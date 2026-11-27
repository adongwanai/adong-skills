from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from _common import BEIJING_TZ, read_json, skill_root


def date_with_offset(days: int) -> str:
    return (datetime.now(BEIJING_TZ).date() + timedelta(days=days)).isoformat()


def run_step(args: list[str], cwd: Path, env: dict[str, str]) -> None:
    print("[run]", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HF daily paper fetch -> summarize -> Markdown & static site build.")
    parser.add_argument(
        "--workspace",
        default=os.getenv("HF_PAPER_WORKSPACE") or os.getcwd(),
        help="Target workspace or hf-daily-papers repo directory (defaults to current working directory).",
    )
    parser.add_argument("--date", default=None, help="Explicit YYYY-MM-DD date.")
    parser.add_argument("--date-offset-days", type=int, default=-1, help="Offset from Beijing today when --date is omitted (default -1 = yesterday).")
    parser.add_argument("--auto-fallback-days", type=int, default=2, help="Step back if target date has 0 papers.")
    parser.add_argument("--model", default=None)
    parser.add_argument("--provider", choices=["auto", "openai", "anthropic"], default="auto")
    parser.add_argument("--max-papers", type=int, default=None)
    parser.add_argument("--skip-cache", action="store_true")
    parser.add_argument("--send-email", action="store_true")
    args = parser.parse_args()

    sroot = skill_root()
    scripts = sroot / "scripts"
    ws = Path(args.workspace).expanduser().resolve()
    ws.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["HF_PAPER_WORKSPACE"] = str(ws)

    target_date = args.date or date_with_offset(args.date_offset_days)
    work_dir = ws / "out" / target_date
    work_dir.mkdir(parents=True, exist_ok=True)
    papers_path = work_dir / "papers.json"
    summaries_path = work_dir / "summaries.json"

    fetch_cmd = [
        sys.executable,
        str(scripts / "fetch_papers.py"),
        "--date",
        target_date,
        "--auto-fallback-days",
        "0" if args.date else str(args.auto_fallback_days),
        "--out",
        str(papers_path),
    ]
    if args.max_papers:
        fetch_cmd.extend(["--max-papers", str(args.max_papers)])
    if args.skip_cache:
        fetch_cmd.append("--skip-cache")
    run_step(fetch_cmd, cwd=ws, env=env)

    fetched = read_json(papers_path)
    actual_date = fetched.get("date") or target_date
    if fetched.get("count", 0) == 0:
        print(f"[done] {actual_date} has 0 papers on HuggingFace; workspace unchanged.")
        return 0

    existing_daily = ws / "data" / "daily" / f"{actual_date}.json"
    sum_cmd = [
        sys.executable,
        str(scripts / "summarize.py"),
        "--in",
        str(papers_path),
        "--out",
        str(summaries_path),
        "--provider",
        args.provider,
    ]
    if existing_daily.exists():
        sum_cmd.extend(["--existing", str(existing_daily)])
    if args.model:
        sum_cmd.extend(["--model", args.model])
    run_step(sum_cmd, cwd=ws, env=env)

    run_step(
        [
            sys.executable,
            str(scripts / "build_site.py"),
            "--data-dir",
            str(ws / "data"),
            "--site-dir",
            str(ws / "site"),
            "--ingest-papers",
            str(papers_path),
            "--ingest-summaries",
            str(summaries_path),
        ],
        cwd=ws,
        env=env,
    )

    daily_json = ws / "data" / "daily" / f"{actual_date}.json"
    if daily_json.exists():
        daily_md_archive = ws / "daily" / f"{actual_date}.md"
        work_md = work_dir / "report.md"
        run_step(
            [sys.executable, str(scripts / "render_md.py"), "--in-json", str(daily_json), "--out-md", str(daily_md_archive)],
            cwd=ws,
            env=env,
        )
        run_step(
            [sys.executable, str(scripts / "render_md.py"), "--in-json", str(daily_json), "--out-md", str(work_md)],
            cwd=ws,
            env=env,
        )
    if args.send_email and daily_json.exists():
        run_step([sys.executable, str(scripts / "send_email.py"), "--daily-json", str(daily_json)], cwd=ws, env=env)

    print(f"[done] workspace={ws}: updated daily/{actual_date}.md and site/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
