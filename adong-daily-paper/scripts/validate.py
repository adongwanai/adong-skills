from __future__ import annotations

import sys
from pathlib import Path

from _common import TOPIC_ORDER, project_root, read_json


def main() -> int:
    root = project_root()
    site = root / "site"
    manifest_path = site / "data" / "manifest.json"
    search_path = site / "data" / "search.json"
    atom_path = site / "feed" / "atom.xml"

    for req in (site / "index.html", site / "style.css", site / "app.js", manifest_path, search_path, atom_path):
        if not req.exists():
            print(f"[validate] FAIL: missing required artifact {req}", file=sys.stderr)
            return 1

    manifest = read_json(manifest_path)
    days = manifest.get("days", [])
    surveys = manifest.get("surveys", [])
    if not days:
        print("[validate] FAIL: manifest.days is empty", file=sys.stderr)
        return 1

    for d in days:
        dt = d["date"]
        day_file = site / "data" / "daily" / f"{dt}.json"
        if not day_file.exists():
            print(f"[validate] FAIL: missing daily file {day_file}", file=sys.stderr)
            return 1
        payload = read_json(day_file)
        for p in payload.get("papers", []):
            if not p.get("arxiv_id"):
                print(f"[validate] FAIL: empty arxiv_id in {dt}", file=sys.stderr)
                return 1
            if p.get("topic") not in TOPIC_ORDER:
                print(f"[validate] FAIL: invalid topic {p.get('topic')} in {dt}", file=sys.stderr)
                return 1

    for s in surveys:
        sf = site / "data" / "surveys" / f"{s['slug']}.json"
        if not sf.exists():
            print(f"[validate] FAIL: missing survey file {sf}", file=sys.stderr)
            return 1

    search = read_json(search_path)
    print(
        f"[validate] OK: {len(days)} issues, {len(search.get('rows', []))} indexed papers, {len(surveys)} surveys verified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
