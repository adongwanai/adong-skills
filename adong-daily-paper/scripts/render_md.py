from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from _common import TOPIC_META, TOPIC_ORDER, normalize_topic, project_root, read_json, safe_slug


def render_daily_markdown(payload: dict[str, Any]) -> str:
    date_str = payload.get("date") or ""
    papers = payload.get("papers") or []
    count = len(papers)
    total_upvotes = sum(int(p.get("upvotes") or 0) for p in papers)
    code_count = sum(1 for p in papers if p.get("github_url"))
    list_url = payload.get("list_url") or f"https://huggingface.co/papers/date/{date_str}"
    brief = payload.get("daily_brief") or ""

    lines: list[str] = [
        f"# HuggingFace 论文日报 · {date_str}",
        "",
        f"> 收录 {count} 篇 · 总票数 {total_upvotes} · 开源代码 {code_count} 篇 · 数据源 [HF Daily Papers]({list_url})",
    ]
    if payload.get("generated_at"):
        meta_tail = f"> 生成时间：{payload['generated_at']}"
        if payload.get("model"):
            meta_tail += f" · 模型：{payload['model']}"
        lines.append(meta_tail)
    lines.append("")

    if count == 0:
        lines.append("当日暂无收录论文。")
        return "\n".join(lines) + "\n"

    if brief:
        lines.extend(["## 今日概览", "", brief, ""])

    grouped: dict[str, list[dict[str, Any]]] = {t: [] for t in TOPIC_ORDER}
    for p in papers:
        t = normalize_topic(p.get("topic"))
        grouped[t].append(p)

    lines.extend(["## 目录", ""])
    for t in TOPIC_ORDER:
        group = sorted(grouped[t], key=lambda x: int(x.get("upvotes") or 0), reverse=True)
        if not group:
            continue
        label = TOPIC_META[t]["label_zh"]
        lines.append(f"- **{label}** ({len(group)})")
        for p in group:
            aid = p.get("arxiv_id") or ""
            anchor = f"paper-{safe_slug(aid)}"
            title_zh = p.get("title_zh") or p.get("title") or "未命名论文"
            code_tag = " · `CODE`" if p.get("github_url") else ""
            lines.append(f"  - [▲ {int(p.get('upvotes') or 0)} · {title_zh}](#{anchor}) (`{aid}`{code_tag})")
    lines.extend(["", "---", ""])

    for t in TOPIC_ORDER:
        group = sorted(grouped[t], key=lambda x: int(x.get("upvotes") or 0), reverse=True)
        if not group:
            continue
        label = TOPIC_META[t]["label_zh"]
        code = TOPIC_META[t]["code"]
        lines.extend([f"## {label} ({code})", ""])

        for idx, p in enumerate(group, start=1):
            aid = p.get("arxiv_id") or ""
            anchor = f"paper-{safe_slug(aid)}"
            title_zh = p.get("title_zh") or p.get("title") or "未命名论文"
            title_en = p.get("title") or ""
            lines.append(f"<a id=\"{anchor}\"></a>")
            lines.append(f"### {idx}. {title_zh}")
            if title_en and title_en != title_zh:
                lines.append(f"*{title_en}* (`{aid}`)")
            lines.append("")

            link_parts = []
            if p.get("hf_url"):
                link_parts.append(f"[HF]({p['hf_url']})")
            if p.get("arxiv_url"):
                link_parts.append(f"[arXiv]({p['arxiv_url']})")
            if p.get("pdf_url"):
                link_parts.append(f"[PDF]({p['pdf_url']})")
            if p.get("github_url"):
                stars = f" ({p['github_stars']}★)" if p.get("github_stars") else ""
                link_parts.append(f"[GitHub{stars}]({p['github_url']})")
            if p.get("project_url"):
                link_parts.append(f"[Project]({p['project_url']})")

            meta_parts = [f"票数 ▲ {int(p.get('upvotes') or 0)}"]
            if p.get("insight_score"):
                meta_parts.append(f"信号 {p['insight_score']}/5")
            if p.get("org"):
                meta_parts.append(f"机构：{p['org']}")
            if p.get("submitter"):
                meta_parts.append(f"提交：{p['submitter']}")
            if p.get("n_authors"):
                meta_parts.append(f"{p['n_authors']} 位作者")

            lines.append(f"**链接**：{' · '.join(link_parts)}  ")
            lines.append(f"**元数据**：{' · '.join(meta_parts)}")
            lines.append("")

            if p.get("summarize_failed"):
                lines.append("> 自动总结未完成，请直接查阅上方原文链接。")
                lines.extend(["", "---", ""])
                continue

            if p.get("tldr"):
                lines.append(f"**核心结论**：{p['tldr']}")
                lines.append("")

            if p.get("problem"):
                lines.append(f"- **问题**：{p['problem']}")
            if p.get("method"):
                lines.append(f"- **方法**：{p['method']}")
            if p.get("contribution"):
                lines.append(f"- **贡献**：{p['contribution']}")
            if p.get("result"):
                lines.append(f"- **结果**：{p['result']}")
            lines.append("")

            if p.get("extra_commentary"):
                lines.append(f"> **编者按**：{p['extra_commentary']}")
                lines.append("")

            has_notes = bool(
                p.get("plain_explanation") or p.get("ideas_and_insights") or p.get("new_paper_directions")
            )
            if has_notes:
                lines.append("<details>")
                lines.append("<summary>直白解释与延伸研究设想</summary>")
                lines.append("")
                if p.get("plain_explanation"):
                    lines.extend(["**直白解释**", "", p["plain_explanation"], ""])
                if p.get("ideas_and_insights"):
                    lines.extend(["**可验证实验设想**", ""])
                    for idea in p["ideas_and_insights"]:
                        lines.append(f"- {idea}")
                    lines.append("")
                if p.get("new_paper_directions"):
                    lines.extend(["**后续研究问题**", ""])
                    for d in p["new_paper_directions"]:
                        lines.append(f"- {d}")
                    lines.append("")
                lines.append("</details>")
                lines.append("")

            lines.extend(["---", ""])

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render clean Markdown report from daily JSON.")
    parser.add_argument("--in-json", default=None, help="Single data/daily/YYYY-MM-DD.json file.")
    parser.add_argument("--out-md", default=None, help="Target Markdown path.")
    parser.add_argument("--all", action="store_true", help="Render all data/daily/*.json into daily/*.md.")
    args = parser.parse_args()

    root = project_root()
    if args.all:
        out_dir = root / "daily"
        out_dir.mkdir(parents=True, exist_ok=True)
        cnt = 0
        for jf in sorted((root / "data" / "daily").glob("*.json")):
            payload = read_json(jf)
            md_text = render_daily_markdown(payload)
            (out_dir / f"{payload['date']}.md").write_text(md_text, encoding="utf-8")
            cnt += 1
        print(f"[md] rendered {cnt} Markdown reports into {out_dir}")
        return 0

    if not args.in_json or not args.out_md:
        raise SystemExit("Provide --in-json and --out-md, or pass --all")

    payload = read_json(args.in_json)
    md_text = render_daily_markdown(payload)
    out_path = Path(args.out_md)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md_text, encoding="utf-8")
    print(f"[md] wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
