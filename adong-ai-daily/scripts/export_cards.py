#!/usr/bin/env python3
"""
adong-ai-daily · 自媒体高清分享卡片命令行批量导出器（可选增强）

直接加载已生成的 {date}_ai_daily_report.html，调用其内置的高清 Canvas 渲染函数，
导出小红书 3:4 封面卡、深度判断金句卡与公众号 16:9 头图 PNG。
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path


def export_cards(html_path: Path, out_dir: Path, palette: str = "obsidian") -> list[Path]:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="domcontentloaded")

        jobs = [
            ("cover", 0, f"{html_path.stem.split('_')[0]}_card_cover_3x4.png"),
            ("insight", 0, f"{html_path.stem.split('_')[0]}_card_insight1_3x4.png"),
            ("banner", 0, f"{html_path.stem.split('_')[0]}_card_banner_16x9.png"),
        ]

        for tpl, idx, filename in jobs:
            data_url: str = page.evaluate(
                "([tpl, pal, idx]) => window.renderCardToCanvas(tpl, pal, idx)",
                [tpl, palette, idx],
            )
            _, b64 = data_url.split(",", 1)
            target = out_dir / filename
            target.write_bytes(base64.b64decode(b64))
            saved.append(target)

        browser.close()
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="批量导出日报自媒体分享卡片 PNG")
    parser.add_argument("--html", required=True, help="已生成的日报 HTML 文件路径")
    parser.add_argument("--out-dir", default="", help="卡片保存目录（默认为 HTML 同级目录下的 cards/）")
    parser.add_argument("--palette", default="obsidian", choices=["obsidian", "editorial", "cobalt"], help="卡片配色主题")
    args = parser.parse_args()

    html_path = Path(args.html).expanduser().resolve()
    if not html_path.exists():
        print(f"❌ 找不到 HTML 文件: {html_path}", file=sys.stderr)
        sys.exit(1)

    cards_dir = Path(args.out_dir).expanduser() if args.out_dir else (html_path.parent / "cards")
    saved = export_cards(html_path, cards_dir, palette=args.palette)
    for f in saved:
        print(f"🖼 已导出高清卡片: {f}")


if __name__ == "__main__":
    main()
