from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from _common import make_session, normalize_space, now_iso, project_root, read_json, today_beijing, write_json

HF_BASE = "https://huggingface.co"
ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")
PAPER_HREF_RE = re.compile(r"^/papers/(\d{4}\.\d{4,5})/?$")


def _tag_text(tag: Tag | None) -> str:
    return normalize_space(tag.get_text(" ", strip=True) if tag else "")


def _normalize_org_value(value: Any) -> str | None:
    if isinstance(value, dict):
        return normalize_space(str(value.get("fullname") or value.get("name") or "")) or None
    if isinstance(value, list):
        for item in value:
            normalized = _normalize_org_value(item)
            if normalized:
                return normalized
        return None
    if value:
        return normalize_space(str(value)) or None
    return None


def _normalize_api_card(item: dict[str, Any]) -> dict[str, Any] | None:
    paper = item.get("paper") if isinstance(item.get("paper"), dict) else item
    raw_id = (
        paper.get("id")
        or paper.get("arxivId")
        or paper.get("arxiv_id")
        or item.get("id")
        or item.get("arxivId")
        or ""
    )
    match = ARXIV_ID_RE.search(str(raw_id))
    if not match:
        url = paper.get("url") or paper.get("hfUrl") or item.get("url") or ""
        match = ARXIV_ID_RE.search(str(url))
    if not match:
        return None
    arxiv_id = match.group(1)

    submitter_obj = item.get("submittedBy") or paper.get("submittedBy") or item.get("submitter") or {}
    submitter = (
        submitter_obj.get("fullname") or submitter_obj.get("name") or submitter_obj.get("username")
        if isinstance(submitter_obj, dict)
        else submitter_obj
    )
    authors = paper.get("authors") if isinstance(paper.get("authors"), list) else []
    org_value = paper.get("organization") or paper.get("org") or item.get("organization") or item.get("org")
    summary_text = normalize_space(str(paper.get("summary") or item.get("summary") or ""))
    ai_summary = normalize_space(str(paper.get("ai_summary") or item.get("ai_summary") or ""))
    raw_keywords = paper.get("ai_keywords") if isinstance(paper.get("ai_keywords"), list) else []

    github_url = paper.get("githubRepo") or item.get("githubRepo") or None
    github_stars = paper.get("githubStars") or item.get("githubStars")
    project_url = paper.get("projectPage") or item.get("projectPage") or None
    thumbnail = item.get("thumbnail") or paper.get("thumbnail") or None
    num_comments = int(item.get("numComments") or paper.get("numComments") or 0)

    return {
        "arxiv_id": arxiv_id,
        "title": normalize_space(str(paper.get("title") or item.get("title") or "Untitled")),
        "hf_url": urljoin(HF_BASE, f"/papers/{arxiv_id}"),
        "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
        "github_url": str(github_url).strip() if github_url else None,
        "github_stars": int(github_stars) if isinstance(github_stars, (int, float)) else None,
        "project_url": str(project_url).strip() if project_url else None,
        "thumbnail": str(thumbnail).strip() if thumbnail else None,
        "ai_keywords": [normalize_space(str(k)) for k in raw_keywords[:6] if normalize_space(str(k))],
        "ai_summary": ai_summary or None,
        "num_comments": num_comments,
        "submitter": normalize_space(str(submitter)) if submitter else None,
        "org": _normalize_org_value(org_value),
        "upvotes": int(item.get("upvotes") or paper.get("upvotes") or paper.get("numLikes") or 0),
        "n_authors": len(authors) if authors else None,
        "authors_preview": [
            normalize_space(str((a.get("user", {}) or {}).get("fullname") or a.get("name") if isinstance(a, dict) else a))
            for a in authors[:6]
            if normalize_space(str(a.get("name") if isinstance(a, dict) else a))
        ],
        "published_at": paper.get("publishedAt") or paper.get("published_at"),
        "hf_brief": ai_summary or summary_text[:280],
        "abstract": summary_text,
        "parse_failed": not bool(summary_text),
        "parse_errors": [] if summary_text else ["missing summary in API"],
    }


def _fetch_list_from_api(date: str, session=None) -> list[dict[str, Any]] | None:
    session = session or make_session()
    url = f"{HF_BASE}/api/daily_papers?date={date}"
    response = session.get(url, timeout=30)
    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400 or "json" not in content_type.lower():
        return None
    data = response.json()
    raw_items = data.get("papers") if isinstance(data, dict) else data
    if not isinstance(raw_items, list):
        return None
    cards = []
    seen: set[str] = set()
    for item in raw_items:
        if isinstance(item, dict):
            card = _normalize_api_card(item)
            if card and card["arxiv_id"] not in seen:
                seen.add(card["arxiv_id"])
                cards.append(card)
    return cards


def parse_list_page_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    seen: set[str] = set()
    cards: list[dict[str, Any]] = []
    for link in soup.find_all("a", href=PAPER_HREF_RE):
        href = str(link.get("href", ""))
        match = PAPER_HREF_RE.match(href)
        if not match:
            continue
        arxiv_id = match.group(1)
        if arxiv_id in seen:
            continue
        seen.add(arxiv_id)
        card = link.find_parent(["article", "li", "div"]) or link
        heading = card.find(["h3", "h2", "h1"])
        title = _tag_text(heading) or _tag_text(link) or "Untitled"
        cards.append(
            {
                "arxiv_id": arxiv_id,
                "title": title,
                "hf_url": urljoin(HF_BASE, f"/papers/{arxiv_id}"),
                "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}",
                "github_url": None,
                "github_stars": None,
                "project_url": None,
                "thumbnail": None,
                "ai_keywords": [],
                "ai_summary": None,
                "num_comments": 0,
                "submitter": None,
                "org": None,
                "upvotes": 0,
                "n_authors": None,
                "authors_preview": [],
                "published_at": None,
                "hf_brief": "",
                "abstract": "",
                "parse_failed": True,
                "parse_errors": ["html list fallback"],
            }
        )
    return cards


def fetch_detail_fallback(arxiv_id: str, session=None) -> dict[str, Any]:
    session = session or make_session()
    time.sleep(0.15)
    url = f"{HF_BASE}/papers/{arxiv_id}"
    response = session.get(url, timeout=30)
    if response.status_code >= 400:
        return {"abstract": "", "github_url": None}
    soup = BeautifulSoup(response.text, "lxml")
    abstract = ""
    header = soup.find(lambda t: isinstance(t, Tag) and t.name in {"h1", "h2", "h3"} and "Abstract" in t.get_text())
    if header:
        paras = []
        for sib in header.next_siblings:
            if isinstance(sib, Tag) and sib.name in {"h1", "h2", "h3"}:
                break
            if isinstance(sib, Tag):
                for p in sib.find_all("p", recursive=True) or [sib]:
                    txt = _tag_text(p)
                    if len(txt) > 40 and txt.lower() != "abstract":
                        paras.append(txt)
        if paras:
            abstract = max(paras, key=len)
    if not abstract:
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta and meta.get("content"):
            abstract = normalize_space(str(meta["content"]))
    github_url = None
    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        if "github.com/" in href and "huggingface" not in href.lower():
            github_url = href
            break
    return {"abstract": abstract, "github_url": github_url}


def build_papers_payload(date: str, max_papers: int | None = None, concurrency: int = 4) -> dict[str, Any]:
    session = make_session()
    cards: list[dict[str, Any]] | None = None
    try:
        cards = _fetch_list_from_api(date, session=session)
    except Exception as exc:
        print(f"[fetch] HF API error, falling back to HTML: {exc}", file=sys.stderr)

    if cards is None:
        resp = session.get(f"{HF_BASE}/papers/date/{date}", timeout=30)
        resp.raise_for_status()
        cards = parse_list_page_html(resp.text)

    if max_papers:
        cards = cards[:max_papers]

    if not cards:
        return {"date": date, "fetched_at": now_iso(), "count": 0, "papers": []}

    # Only hit detail HTML for cards missing abstract
    missing_indices = [idx for idx, c in enumerate(cards) if not c.get("abstract")]
    if missing_indices:
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            fut_map = {
                executor.submit(fetch_detail_fallback, cards[i]["arxiv_id"], session): i for i in missing_indices
            }
            for fut in as_completed(fut_map):
                idx = fut_map[fut]
                try:
                    detail = fut.result()
                    if detail.get("abstract"):
                        cards[idx]["abstract"] = detail["abstract"]
                        cards[idx]["hf_brief"] = cards[idx]["hf_brief"] or detail["abstract"][:280]
                        cards[idx]["parse_failed"] = False
                        cards[idx]["parse_errors"] = []
                    if detail.get("github_url") and not cards[idx].get("github_url"):
                        cards[idx]["github_url"] = detail["github_url"]
                except Exception as exc:
                    cards[idx]["parse_errors"].append(str(exc))

    cards.sort(key=lambda c: int(c.get("upvotes") or 0), reverse=True)
    return {"date": date, "fetched_at": now_iso(), "count": len(cards), "papers": cards}


def _cache_path(date: str) -> Path:
    return project_root() / ".cache" / "hf-daily-paper" / f"{date}.json"


def _is_cache_fresh(cache_file: Path, target_date: str) -> bool:
    if not cache_file.exists():
        return False
    try:
        payload = read_json(cache_file)
    except Exception:
        return False
    if payload.get("count", 0) <= 0:
        return False
    # For today or yesterday, expire cache after 2 hours because upvotes & new papers keep arriving
    today = today_beijing()
    yesterday = (datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    if target_date in {today, yesterday}:
        age_sec = time.time() - cache_file.stat().st_mtime
        if age_sec > 7200:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch HuggingFace daily papers into papers.json.")
    parser.add_argument("--date", default=None, help="Target date in YYYY-MM-DD.")
    parser.add_argument("--auto-fallback-days", type=int, default=0, help="Step back up to N days if target date has 0 papers.")
    parser.add_argument("--out", required=True, help="Output papers.json path.")
    parser.add_argument("--max-papers", type=int, default=None, help="Optional cap for debugging (skips writing shared cache).")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--skip-cache", action="store_true")
    args = parser.parse_args()

    target_date = args.date or today_beijing()
    out_path = Path(args.out)

    for offset in range(max(0, args.auto_fallback_days) + 1):
        dt = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=offset)).strftime("%Y-%m-%d")
        cache_file = _cache_path(dt)
        if not args.skip_cache and not args.max_papers and _is_cache_fresh(cache_file, dt):
            payload = read_json(cache_file)
            write_json(payload, out_path)
            print(f"[fetch] reused valid cache for {dt} ({payload['count']} papers)")
            return 0

        payload = build_papers_payload(date=dt, max_papers=args.max_papers, concurrency=args.concurrency)
        if payload["count"] > 0 or offset == max(0, args.auto_fallback_days):
            write_json(payload, out_path)
            if payload["count"] > 0 and not args.max_papers:
                write_json(payload, cache_file)
            failed = sum(1 for p in payload["papers"] if p.get("parse_failed"))
            print(f"[fetch] wrote {out_path} for {dt} ({payload['count']} papers, {failed} missing abstracts)")
            return 0
        print(f"[fetch] {dt} has 0 papers on HF, stepping back 1 day...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
