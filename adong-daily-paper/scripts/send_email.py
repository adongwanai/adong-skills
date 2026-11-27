from __future__ import annotations

import argparse
import html
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from _common import load_dotenv, load_site_config, read_json


def _split_addresses(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def send_slim_digest(daily_json_path: str | Path, subject: str | None = None) -> None:
    load_dotenv()
    cfg = load_site_config()
    base_url = str(cfg.get("base_url") or "https://adongwanai.github.io/hf-daily-papers").rstrip("/")
    payload = read_json(daily_json_path)
    dt = payload["date"]
    count = payload.get("count", 0)
    if count == 0:
        print(f"[email] {dt} has 0 papers; skipping email.")
        return

    host = os.environ["SMTP_HOST"]
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASS"]
    sender = os.getenv("SMTP_FROM") or user
    recipients = _split_addresses(os.environ.get("EMAIL_TO"))
    bcc = _split_addresses(os.environ.get("EMAIL_BCC"))
    if not recipients:
        raise RuntimeError("EMAIL_TO is required")

    issue_url = f"{base_url}/#daily/{dt}"
    papers = sorted(payload.get("papers", []), key=lambda x: int(x.get("upvotes") or 0), reverse=True)
    top5 = papers[:5]
    brief = payload.get("daily_brief") or ""

    plain_lines = [
        f"HF Papers · {dt}（共 {count} 篇 · 开源代码 {payload.get('code_count', 0)} 篇）",
        "",
        brief,
        "",
        "代表论文：",
    ]
    for idx, p in enumerate(top5, 1):
        plain_lines.append(f"{idx}. {p['title_zh']} (▲{p.get('upvotes', 0)}) — {p.get('tldr', '')}")
    plain_lines.extend(["", f"在线完整交互账本：{issue_url}"])
    plain_body = "\n".join(plain_lines)

    rows_html = "".join(
        f"""<li style="margin:0 0 10px 0;">
          <strong>{html.escape(p['title_zh'])}</strong>
          <span style="font-family:monospace;font-size:12px;color:#585D69;"> · ▲{p.get('upvotes', 0)} · {html.escape(p['arxiv_id'])}</span><br>
          <span style="color:#444954;font-size:14px;">{html.escape(p.get('tldr', ''))}</span>
        </li>"""
        for p in top5
    )

    html_body = f"""<!doctype html>
<html lang="zh-CN">
<body style="margin:0;padding:24px 16px;background:#F6F5F1;color:#111318;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC',sans-serif;line-height:1.6;">
  <div style="max-width:620px;margin:0 auto;background:#FFFFFF;border:1px solid #DFDDD6;padding:24px 26px;">
    <div style="font-family:monospace;font-size:12px;color:#585D69;letter-spacing:0.06em;text-transform:uppercase;">HF PAPERS · DAILY LEDGER</div>
    <h1 style="margin:6px 0 10px;font-size:22px;font-family:Georgia,serif;">{dt} · 收录 {count} 篇论文</h1>
    <p style="margin:0 0 16px;color:#444954;font-size:14px;">{html.escape(brief)}</p>
    <ol style="margin:0 0 20px 18px;padding:0;">{rows_html}</ol>
    <a href="{issue_url}" style="display:inline-block;background:#111318;color:#FFFFFF;text-decoration:none;padding:9px 16px;font-size:13px;font-weight:500;">打开完整在线论文账本 →</a>
  </div>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject or f"HF Papers · {dt} ({count} 篇)"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.sendmail(sender, recipients + bcc, msg.as_string())
    print(f"[email] sent slim digest for {dt}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Send slim daily digest email linking to GitHub Pages.")
    parser.add_argument("--daily-json", required=True)
    parser.add_argument("--subject", default=None)
    args = parser.parse_args()
    send_slim_digest(args.daily_json, args.subject)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
