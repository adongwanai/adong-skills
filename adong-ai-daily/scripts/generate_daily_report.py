#!/usr/bin/env python3
"""
adong-ai-daily · 兼容旧版命令行入口（修复旧版空分类标题错位、硬编码套话与路径权限问题）
实际委托给 render_report.py 生成交互式 HTML 日报页与社群一键转发纯文本版。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python3 generate_daily_report.py <candidates_json> [--curated <curated_json>] [--out-dir <dir>]")
        sys.exit(1)

    candidates_file = sys.argv[1]
    extra_args = sys.argv[2:]
    if "--curated" not in extra_args and "--auto" not in extra_args:
        extra_args.append("--auto")

    cmd = [sys.executable, str(SCRIPT_DIR / "render_report.py"), "--candidates", candidates_file, *extra_args]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
