#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from career_state import load_state, write_markdown
from common import SKILL_DIR, workspace_path
from render_career_dashboard import render_dashboard


def initialize(raw_destination: str) -> Path:
    destination = workspace_path(raw_destination)
    if destination.exists():
        raise ValueError(f"destination already exists: {destination}")

    template = SKILL_DIR / "assets" / "workspace-template"
    shutil.copytree(template, destination)
    (destination / ".gitignore").write_text(
        "# Candidate workspaces contain generated and source files; opt in files when version control is needed.\n"
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
        "outputs/career-dashboard",
        "outputs/interview/companies",
        "outputs/application",
    ):
        (destination / relative).mkdir(parents=True, exist_ok=True)

    state = load_state(destination)
    write_markdown(destination, state)
    render_dashboard(destination, state)

    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description="创建轻量的 Agent 求职工作区。")
    parser.add_argument("destination", help="新的工作区目录，必须尚不存在。")
    args = parser.parse_args()
    try:
        destination = initialize(args.destination)
    except ValueError as error:
        raise SystemExit(f"初始化失败：{error}") from None
    print(destination)
    print("下一步：提供简历、JD、项目材料或一段背景介绍中的任意一种；Agent 会负责导入与整理。")


if __name__ == "__main__":
    main()
