#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from common import REPO_DIR, workspace_path


LEVEL_RE = re.compile(r"^\*\*(L[0-5])\b")
QUESTION_RE = re.compile(r"^(\d+)\.\s+(.+)$")
ATTRIBUTION_RE = re.compile(r"\s*「([^」]+)」\s*$")


def index_bank(bank_path: Path, workspace: Path) -> Path:
    if workspace == REPO_DIR or REPO_DIR in workspace.parents:
        raise ValueError("private interview-bank indexes must stay outside the Agent Career Kit repository")
    text = bank_path.read_text(encoding="utf-8-sig")
    domain = ""
    category = ""
    level = ""
    questions: list[dict[str, object]] = []

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if line.startswith("# "):
            heading = line[2:].strip()
            if not heading.startswith("1000篇"):
                domain = heading
                category = ""
                level = ""
            continue
        if line.startswith("## "):
            category = line[3:].strip()
            level = ""
            continue
        level_match = LEVEL_RE.match(line)
        if level_match:
            level = level_match.group(1)
            continue
        question_match = QUESTION_RE.match(line)
        if not question_match or not domain or not category or not level:
            continue
        question = question_match.group(2).strip()
        attribution_match = ATTRIBUTION_RE.search(question)
        attributions: list[str] = []
        if attribution_match:
            attributions = [item.strip() for item in re.split(r"[、,，]", attribution_match.group(1)) if item.strip()]
            question = question[: attribution_match.start()].rstrip()
        questions.append(
            {
                "id": f"bank-{len(questions) + 1:05d}",
                "domain": domain,
                "category": category,
                "level": level,
                "question": question,
                "reported_attributions": attributions,
                "source_line": line_number,
            }
        )

    if not questions:
        raise ValueError("interview bank contains no indexed questions")

    output = workspace / "interview-bank" / "question-index.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": {
            "name": bank_path.name,
            "sha256": hashlib.sha256(bank_path.read_bytes()).hexdigest(),
            "bytes": bank_path.stat().st_size,
            "lines": len(text.splitlines()),
            "provenance_note": "User-provided Xiaohongshu-platform interview aggregation. Company labels are reported attributions, not independently verified interview history.",
        },
        "question_count": len(questions),
        "questions": questions,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Index a user-provided Markdown interview bank into a private candidate workspace.")
    parser.add_argument("bank", type=Path)
    parser.add_argument("workspace")
    args = parser.parse_args()
    bank = args.bank.expanduser().resolve()
    if not bank.is_file():
        raise ValueError(f"interview bank does not exist: {bank}")
    print(index_bank(bank, workspace_path(args.workspace)))


if __name__ == "__main__":
    main()
