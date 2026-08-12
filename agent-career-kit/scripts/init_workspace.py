#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from common import SKILL_DIR, workspace_path
from index_interview_bank import BUNDLED_BANK, index_bank


def initialize(raw_destination: str) -> Path:
    destination = workspace_path(raw_destination)
    if destination.exists():
        raise ValueError(f"destination already exists: {destination}")

    template = SKILL_DIR / "assets" / "workspace-template"
    shutil.copytree(template, destination)
    (destination / ".gitignore").write_text(
        "# Candidate workspaces are private by default. Remove entries only after an explicit data review.\n"
        "*\n"
        "!.gitignore\n",
        encoding="utf-8",
    )
    for relative in (
        "source-materials",
        "public-assets",
        "jd-bank",
        "outputs/resumes/development",
        "outputs/resumes/algorithm",
        "outputs/portfolio",
        "outputs/interview/companies",
        "outputs/application",
    ):
        (destination / relative).mkdir(parents=True, exist_ok=True)

    for filename in ("application-tracker.csv", "interview-schedule.csv", "offer-comparison.csv"):
        shutil.move(destination / filename, destination / "outputs" / "application" / filename)
    index_bank(BUNDLED_BANK, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an external Agent Career Kit workspace.")
    parser.add_argument("destination", help="New workspace directory. It must not already exist.")
    args = parser.parse_args()
    print(initialize(args.destination))


if __name__ == "__main__":
    main()
