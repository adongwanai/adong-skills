from __future__ import annotations

import argparse
import html
import re
import shutil
from pathlib import Path
from typing import Any

import markdown

from _common import (
    TOPIC_META,
    TOPIC_ORDER,
    load_site_config,
    normalize_space,
    normalize_topic,
    now_iso,
    project_root,
    read_json,
    safe_slug,
    skill_root,
    write_json,
)


def merge_fresh_run(papers_path: Path, summaries_path: Path, out_daily_dir: Path) -> Path | None:
    papers_payload = read_json(papers_path)
    summaries_payload = read_json(summaries_path)
    raw_items = summaries_payload.get("items") if isinstance(summaries_payload, dict) else summaries_payload
    if not isinstance(raw_items, list):
        raise ValueError("summaries.json must contain an 'items' list")

    summary_map = {str(item.get("arxiv_id")): item for item in raw_items if item.get("arxiv_id")}
    date_str = papers_payload.get("date") or summaries_payload.get("date")
    papers_list = papers_payload.get("papers", [])
    if not papers_list:
        print(f"[build] {date_str} has 0 papers; skipping daily archive write.")
        return None

    merged: list[dict[str, Any]] = []
    for p in papers_list:
        aid = str(p.get("arxiv_id") or "")
        s = summary_map.get(aid, {})
        topic = normalize_topic(s.get("topic"))
        item = {
            "arxiv_id": aid,
            "title": p.get("title") or s.get("title_zh") or "Untitled",
            "title_zh": s.get("title_zh") or p.get("title") or "未命名论文",
            "topic": topic,
            "tags": s.get("tags") or p.get("ai_keywords", [])[:3],
            "hf_url": p.get("hf_url") or f"https://huggingface.co/papers/{aid}",
            "arxiv_url": p.get("arxiv_url") or f"https://arxiv.org/abs/{aid}",
            "pdf_url": p.get("pdf_url") or f"https://arxiv.org/pdf/{aid}",
            "github_url": p.get("github_url"),
            "github_stars": p.get("github_stars"),
            "project_url": p.get("project_url"),
            "thumbnail": p.get("thumbnail"),
            "submitter": p.get("submitter"),
            "org": p.get("org"),
            "upvotes": int(p.get("upvotes") or 0),
            "n_authors": p.get("n_authors"),
            "authors_preview": p.get("authors_preview") or [],
            "tldr": s.get("tldr") or p.get("hf_brief") or "",
            "problem": s.get("problem") or "",
            "method": s.get("method") or "",
            "contribution": s.get("contribution") or "",
            "result": s.get("result"),
            "insight_score": int(s.get("insight_score") or 3),
            "focus_match": bool(s.get("focus_match")),
            "extra_commentary": s.get("extra_commentary"),
            "plain_explanation": s.get("plain_explanation") or "",
            "ideas_and_insights": s.get("ideas_and_insights") or [],
            "new_paper_directions": s.get("new_paper_directions") or [],
            "summarize_failed": bool(s.get("summarize_failed", not bool(s))),
        }
        merged.append(item)

    merged.sort(key=lambda x: (TOPIC_ORDER.index(x["topic"]), -int(x.get("upvotes") or 0)))
    daily_brief = summaries_payload.get("daily_brief") if isinstance(summaries_payload, dict) else ""
    if not daily_brief:
        by_t: dict[str, int] = {}
        for m in merged:
            by_t[m["topic"]] = by_t.get(m["topic"], 0) + 1
        top_t = sorted(by_t.items(), key=lambda kv: kv[1], reverse=True)[:3]
        desc = "、".join(f"{TOPIC_META[k]['label_zh']}（{v} 篇）" for k, v in top_t)
        top_p = sorted(merged, key=lambda x: int(x.get("upvotes") or 0), reverse=True)[:2]
        daily_brief = f"当日收录集中于{desc}。代表工作包括：{'；'.join(x['title_zh'] for x in top_p)}。"

    payload = {
        "date": date_str,
        "generated_at": now_iso(),
        "model": summaries_payload.get("model") if isinstance(summaries_payload, dict) else None,
        "count": len(merged),
        "total_upvotes": sum(int(x.get("upvotes") or 0) for x in merged),
        "code_count": sum(1 for x in merged if x.get("github_url")),
        "high_signal_count": sum(1 for x in merged if int(x.get("insight_score") or 0) >= 4),
        "daily_brief": daily_brief,
        "list_url": f"https://huggingface.co/papers/date/{date_str}",
        "papers": merged,
    }
    out_daily_dir.mkdir(parents=True, exist_ok=True)
    target = out_daily_dir / f"{date_str}.json"
    write_json(payload, target)
    return target


def render_survey_json(md_path: Path, meta_path: Path) -> dict[str, Any]:
    meta = read_json(meta_path) if meta_path.exists() else {"slug": md_path.stem, "order": 99, "title_zh": md_path.stem}
    md_text = md_path.read_text(encoding="utf-8")
    lines = md_text.splitlines()
    # Extract summary paragraph (first non-heading, non-table paragraph)
    summary_lines: list[str] = []
    for ln in lines[1:20]:
        s = ln.strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith("<"):
            continue
        if s.startswith("时间范围"):
            continue
        summary_lines.append(re.sub(r"[*_`]", "", s))
        if len(summary_lines) >= 2:
            break
    summary = normalize_space(" ".join(summary_lines))[:180]

    body_md = "\n".join(lines[1:]) if lines and lines[0].startswith("# ") else md_text
    raw_html = markdown.markdown(body_md, extensions=["extra", "tables", "sane_lists"], output_format="html5")

    # Inject deterministic IDs into h2/h3 and extract outline TOC
    toc: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    def _add_heading_id(match: re.Match[str]) -> str:
        level = int(match.group(1))
        inner = match.group(2)
        plain = normalize_space(re.sub(r"<[^>]+>", "", html.unescape(inner)))
        hid = f"sec-{len(toc) + 1}-{safe_slug(plain)[:24]}"
        while hid in used_ids:
            hid += "-x"
        used_ids.add(hid)
        if level in (2, 3):
            toc.append({"id": hid, "level": level, "text": plain})
        return f"<h{level} id=\"{hid}\">{inner}</h{level}>"

    enriched_html = re.sub(r"<h([23])>(.*?)</h\1>", _add_heading_id, raw_html, flags=re.S)
    # Wrap tables in horizontal scroll container & open external links in new tab
    enriched_html = enriched_html.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    enriched_html = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" target="_blank" rel="noopener"', enriched_html)

    return {
        **meta,
        "summary": summary,
        "toc": toc,
        "html": enriched_html,
    }


def build_atom_feed(cfg: dict[str, Any], recent_days: list[dict[str, Any]], daily_dir: Path) -> str:
    base_url = str(cfg.get("base_url") or "https://adongwanai.github.io/hf-daily-papers").rstrip("/")
    feed_url = str(cfg.get("feed_url") or f"{base_url}/feed/atom.xml")
    title = html.escape(str(cfg.get("title") or "HF Papers"))
    updated = now_iso()
    entries: list[str] = []
    for day_meta in recent_days[:15]:
        dt = day_meta["date"]
        day_data = read_json(daily_dir / f"{dt}.json")
        top_items = sorted(day_data.get("papers", []), key=lambda x: int(x.get("upvotes") or 0), reverse=True)[:8]
        li_html = "".join(
            f"<li><strong>{html.escape(p['title_zh'])}</strong> (▲{p.get('upvotes', 0)} · {html.escape(p['arxiv_id'])}) — {html.escape(p.get('tldr', ''))}</li>"
            for p in top_items
        )
        summary_html = f"<p>{html.escape(day_data.get('daily_brief') or '')}</p><ul>{li_html}</ul>"
        link = f"{base_url}/#daily/{dt}"
        entries.append(
            f"""  <entry>
    <title>HF Papers · {dt} ({day_meta['count']} 篇)</title>
    <link href="{link}" />
    <id>{base_url}/daily/{dt}</id>
    <updated>{day_data.get('generated_at') or updated}</updated>
    <content type="html">{html.escape(summary_html)}</content>
  </entry>"""
        )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{title} · 每日论文账本</title>
  <link href="{base_url}/" />
  <link href="{feed_url}" rel="self" />
  <updated>{updated}</updated>
  <id>{base_url}/</id>
  <author>
    <name>{html.escape(str(cfg.get('author_name') or 'Adong'))}</name>
  </author>
{chr(10).join(entries)}
</feed>
"""


def ensure_site_shell(site_dir: Path) -> None:
    site_dir.mkdir(parents=True, exist_ok=True)
    tpl_dir = skill_root() / "templates" / "site"
    if not tpl_dir.exists():
        return
    for asset in ("index.html", "style.css", "app.js"):
        dest = site_dir / asset
        src = tpl_dir / asset
        if src.exists() and not dest.exists():
            shutil.copyfile(src, dest)


def build_all(data_dir: Path, site_dir: Path) -> None:
    ensure_site_shell(site_dir)
    cfg = load_site_config()
    daily_src = data_dir / "daily"
    surveys_src = data_dir / "surveys"

    site_data = site_dir / "data"
    site_daily = site_data / "daily"
    site_surveys = site_data / "surveys"
    if site_data.exists():
        shutil.rmtree(site_data)
    site_daily.mkdir(parents=True, exist_ok=True)
    site_surveys.mkdir(parents=True, exist_ok=True)

    days_index: list[dict[str, Any]] = []
    search_rows: list[list[Any]] = []
    total_papers = 0

    for day_file in sorted(daily_src.glob("*.json"), reverse=True):
        payload = read_json(day_file)
        papers = payload.get("papers", [])
        if not papers:
            continue
        dt = payload["date"]
        topic_counts: dict[str, int] = {}
        for p in papers:
            t = normalize_topic(p.get("topic"))
            p["topic"] = t
            topic_counts[t] = topic_counts.get(t, 0) + 1
            # Compact tuple for instant search:
            # [0:date, 1:arxiv_id, 2:topic, 3:upvotes, 4:score, 5:has_code(0/1), 6:title_zh, 7:title_en_if_diff, 8:org, 9:tldr]
            t_zh = p.get("title_zh") or p.get("title") or ""
            t_en = p.get("title") if (p.get("title") and p.get("title") != t_zh) else ""
            search_rows.append(
                [
                    dt,
                    p.get("arxiv_id") or "",
                    t,
                    int(p.get("upvotes") or 0),
                    int(p.get("insight_score") or 3),
                    1 if p.get("github_url") else 0,
                    t_zh,
                    t_en,
                    p.get("org") or "",
                    p.get("tldr") or "",
                ]
            )

        top_paper = max(papers, key=lambda x: int(x.get("upvotes") or 0))
        days_index.append(
            {
                "date": dt,
                "count": len(papers),
                "total_upvotes": sum(int(x.get("upvotes") or 0) for x in papers),
                "code_count": sum(1 for x in papers if x.get("github_url")),
                "high_signal_count": sum(1 for x in papers if int(x.get("insight_score") or 0) >= 4),
                "topic_counts": topic_counts,
                "top_paper": {
                    "arxiv_id": top_paper.get("arxiv_id"),
                    "title_zh": top_paper.get("title_zh"),
                    "upvotes": int(top_paper.get("upvotes") or 0),
                },
                "daily_brief": payload.get("daily_brief") or "",
            }
        )
        total_papers += len(papers)
        write_json(payload, site_daily / f"{dt}.json", compact=True)

    surveys_index: list[dict[str, Any]] = []
    if surveys_src.exists():
        for md_path in sorted(surveys_src.glob("*.md")):
            meta_path = surveys_src / f"{md_path.stem}.meta.json"
            survey_obj = render_survey_json(md_path, meta_path)
            slug = survey_obj["slug"]
            write_json(survey_obj, site_surveys / f"{slug}.json", compact=True)
            surveys_index.append(
                {
                    "slug": slug,
                    "order": survey_obj.get("order", 99),
                    "title_zh": survey_obj.get("title_zh"),
                    "title_en": survey_obj.get("title_en"),
                    "full_title": survey_obj.get("full_title"),
                    "period": survey_obj.get("period"),
                    "paper_count": survey_obj.get("paper_count", 0),
                    "summary": survey_obj.get("summary", ""),
                    "section_count": len([x for x in survey_obj.get("toc", []) if x["level"] == 2]),
                }
            )
    surveys_index.sort(key=lambda s: s["order"])

    manifest = {
        "site": cfg,
        "generated_at": now_iso(),
        "topics": [{"key": k, **TOPIC_META[k]} for k in TOPIC_ORDER],
        "stats": {
            "issue_count": len(days_index),
            "paper_count": total_papers,
            "survey_count": len(surveys_index),
            "earliest_date": days_index[-1]["date"] if days_index else None,
            "latest_date": days_index[0]["date"] if days_index else None,
        },
        "days": days_index,
        "surveys": surveys_index,
    }
    write_json(manifest, site_data / "manifest.json", compact=True)
    write_json({"fields": ["date", "arxiv_id", "topic", "upvotes", "score", "code", "title_zh", "title_en", "org", "tldr"], "rows": search_rows}, site_data / "search.json", compact=True)

    feed_dir = site_dir / "feed"
    feed_dir.mkdir(parents=True, exist_ok=True)
    (feed_dir / "atom.xml").write_text(build_atom_feed(cfg, days_index, daily_src), encoding="utf-8")
    (site_dir / ".nojekyll").write_text("", encoding="utf-8")

    print(
        f"[build] compiled {len(days_index)} issues ({total_papers} papers), {len(surveys_index)} surveys, search.json ({len(search_rows)} rows), and feed/atom.xml"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build static site data & RSS feed.")
    parser.add_argument("--data-dir", default=str(project_root() / "data"))
    parser.add_argument("--site-dir", default=str(project_root() / "site"))
    parser.add_argument("--ingest-papers", default=None)
    parser.add_argument("--ingest-summaries", default=None)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    site_dir = Path(args.site_dir)

    if args.ingest_papers and args.ingest_summaries:
        merge_fresh_run(Path(args.ingest_papers), Path(args.ingest_summaries), data_dir / "daily")

    build_all(data_dir, site_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
