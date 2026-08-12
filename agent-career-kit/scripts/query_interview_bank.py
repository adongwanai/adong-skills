#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import workspace_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Query an indexed interview bank in a candidate workspace.")
    parser.add_argument("workspace")
    parser.add_argument("--domain")
    parser.add_argument("--category")
    parser.add_argument("--level", action="append", choices=[f"L{value}" for value in range(6)])
    parser.add_argument("--contains")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.limit < 1:
        raise ValueError("limit must be positive")

    workspace = workspace_path(args.workspace)
    index_path = workspace / "interview-bank" / "question-index.json"
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    levels = set(args.level or ["L1", "L2", "L3", "L4", "L5"])
    contains = args.contains.casefold() if args.contains else None
    matches = []
    for question in payload["questions"]:
        if question["level"] not in levels:
            continue
        if args.domain and question["domain"] != args.domain:
            continue
        if args.category and question["category"] != args.category:
            continue
        if contains and contains not in question["question"].casefold():
            continue
        matches.append(question)
        if len(matches) == args.limit:
            break
    print(json.dumps(matches, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
