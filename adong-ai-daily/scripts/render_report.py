#!/usr/bin/env python3
"""
adong-ai-daily · 账本校验、ID精确回填与双端渲染引擎

核心职责：
1. 读取候选池 JSON（collect_sources.py 生成）与 Agent 策展 JSON（curated.json），
   或启用 --auto 确定性无套话兜底模式。
2. 按候选短 ID（如 N001）从候选池精确回填真实 URL、多源共振列表、点赞/Star 热度，
   彻底杜绝大模型漏链或编造链接；同时对文案执行“去 AI 套话”扫描提醒。
3. 仅输出用户指定的 2 份干净交付物：
   - {date}_ai_daily_report.html（自包含交互式 HTML 日报账本 + 内置自媒体分享卡片高清 Canvas 导出台）
   - {date}_community_brief.txt（社群一键转发纯文本精简版）
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = SKILL_ROOT / "config.json"

CATEGORY_ORDER = [
    "科研进展",
    "技术突破",
    "产品发布",
    "融资并购",
    "开源工具",
    "重磅观点",
    "行业动态",
    "政策监管",
    "产业观察",
]

BANNED_CLICHES = [
    "意义重大", "里程碑式", "颠覆性", "铺平了道路", "随着大模型的发展",
    "生态建设加速", "资本市场看好相关领域", "值得关注的重要动态", "引爆全网",
]


def resolve_output_dir(requested_dir: str, config: dict[str, Any]) -> Path:
    candidates_dirs = []
    if requested_dir:
        candidates_dirs.append(Path(requested_dir).expanduser())
    if os.environ.get("AI_DAILY_OUT_DIR"):
        candidates_dirs.append(Path(os.environ["AI_DAILY_OUT_DIR"]).expanduser())
    if config.get("default_output_dir"):
        candidates_dirs.append(Path(config["default_output_dir"]).expanduser())
    candidates_dirs.append(Path(config.get("fallback_output_dir", str(SKILL_ROOT / "output"))).expanduser())

    for d in candidates_dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".write_probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return d
        except PermissionError:
            print(f"⚠️ 目录 {d} 受 macOS 隐私权限限制，尝试回退目录...", file=sys.stderr)
            continue
        except OSError:
            continue

    fallback = SKILL_ROOT / "output"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def weekday_zh(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][dt.weekday()]
    except ValueError:
        return ""


def lint_cliches(curated: dict[str, Any]) -> list[str]:
    blob = json.dumps(curated, ensure_ascii=False)
    return [phrase for phrase in BANNED_CLICHES if phrase in blob]


def build_auto_curated(candidates_data: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """当未传入 Agent 策展文件时的确定性提取器：严守事实，绝不生成空洞套话。"""
    candidates = candidates_data.get("candidates") or []
    limits = config.get("limits") or {}
    per_cat_max = int(limits.get("per_category_max", 6))
    total_target = int(limits.get("selected_total_target", 38))

    # 若传入的是旧版格式（无 candidates，仅有 sources[].articles），即时兼容转换
    if not candidates and candidates_data.get("sources"):
        idx = 1
        for src in candidates_data["sources"]:
            sname = src.get("source_name", "资讯")
            for art in src.get("articles") or []:
                candidates.append({
                    "id": f"N{idx:03d}",
                    "title": art.get("title", ""),
                    "summary": (art.get("description") or "").strip(),
                    "primary_url": art.get("link", ""),
                    "primary_source": sname,
                    "tier": "media",
                    "suggested_category": "行业动态",
                    "resonance_count": 1,
                    "sources": [{"name": sname, "url": art.get("link", ""), "heat": None, "heat_unit": ""}],
                    "focus_hits": [],
                    "score": 0.5,
                })
                idx += 1

    by_cat: dict[str, list[dict[str, Any]]] = {c: [] for c in CATEGORY_ORDER}
    selected: list[dict[str, Any]] = []

    for c in candidates:
        if len(selected) >= total_target:
            break
        cat = c.get("suggested_category", "行业动态")
        if cat not in by_cat:
            cat = "行业动态"
        if len(by_cat[cat]) >= per_cat_max:
            continue
        raw_sum = (c.get("summary") or "").strip()
        if not raw_sum:
            src_names = "、".join(s["name"] for s in (c.get("sources") or [])[:3])
            raw_sum = f"来源：{src_names}（原文未附摘要，点击直达查看完整细节）"
        entry = {
            "id": c["id"],
            "category": cat,
            "headline": c["title"],
            "one_liner": raw_sum[:110],
            "adong_note": "",
        }
        by_cat[cat].append(entry)
        selected.append(entry)

    top_picks_ids = [s["id"] for s in selected[:4]]

    # 生成基于真实统计与具体事件的客观汇总
    active_cats = sorted(((k, v) for k, v in by_cat.items() if v), key=lambda kv: len(kv[1]), reverse=True)
    top_cat_summary = "、".join(f"{k}（{len(v)}条）" for k, v in active_cats[:3])
    multi_cnt = (candidates_data.get("stats") or {}).get("multi_source_clusters", 0)
    daily_take = (
        f"今日共从多源动态中去重提炼出 {len(selected)} 条核心进展，主要集中在 {top_cat_summary}。"
        f"其中有 {multi_cnt} 起事件出现跨媒体/跨榜单同题共振，建议重点优先扫读前 4 条高热度与一手建设者条目。"
    )

    insights = []
    for k, items_in_cat in active_cats[:5]:
        cited = [it["id"] for it in items_in_cat[:3]]
        titles_preview = "；".join(it["headline"][:32] for it in items_in_cat[:3])
        insights.append({
            "title": f"{k}方向密集动态速览",
            "body": f"本分类今日收录 {len(items_in_cat)} 条代表性进展，核心事件包括：{titles_preview}。可结合原文指标与开源仓库进一步评估工程可用性。",
            "evidence_ids": cited,
        })

    return {
        "date": candidates_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "daily_take": daily_take,
        "top_picks": top_picks_ids,
        "insights": insights,
        "items": selected,
    }


def merge_and_validate(
    candidates_data: dict[str, Any],
    curated: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    cand_map: dict[str, dict[str, Any]] = {
        c["id"]: c for c in (candidates_data.get("candidates") or [])
    }

    cliche_hits = lint_cliches(curated)
    if cliche_hits:
        print(f"⚠️ 文风提示：检测到套话词汇 {cliche_hits}，建议后续保持平实克制。", file=sys.stderr)

    enriched_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw_item in curated.get("items") or []:
        cid = str(raw_item.get("id") or "").strip()
        if not cid or cid in seen_ids:
            continue
        base = cand_map.get(cid)
        if not base:
            print(f"⚠️ 忽略未知候选 ID: {cid}（防止未验证链接混入）", file=sys.stderr)
            continue
        seen_ids.add(cid)

        cat = raw_item.get("category") or base.get("suggested_category") or "行业动态"
        if cat not in CATEGORY_ORDER:
            cat = "行业动态"

        headline = (raw_item.get("headline") or base["title"]).strip()
        one_liner = (raw_item.get("one_liner") or base.get("summary") or "").strip()
        adong_note = (raw_item.get("adong_note") or "").strip()

        # 计算最佳热度徽章
        heat_badge = ""
        for s in base.get("sources") or []:
            if s.get("heat"):
                h = s["heat"]
                h_str = f"{h/1000:.1f}k" if h >= 1000 else str(h)
                unit = s.get("heat_unit") or ""
                heat_badge = f"{h_str} {unit}".strip()
                break

        enriched_items.append({
            "id": cid,
            "category": cat,
            "headline": headline,
            "original_title": base["title"],
            "one_liner": one_liner,
            "adong_note": adong_note,
            "primary_url": base["primary_url"],
            "primary_source": base["primary_source"],
            "tier": base.get("tier", "media"),
            "author": base.get("author", ""),
            "role": base.get("role", ""),
            "resonance_count": base.get("resonance_count", 1),
            "heat_badge": heat_badge,
            "focus_hits": base.get("focus_hits") or [],
            "sources": base.get("sources") or [],
        })

    item_by_id = {it["id"]: it for it in enriched_items}

    # 处理 Top Picks（4条）
    top_ids = [tid for tid in (curated.get("top_picks") or []) if tid in item_by_id]
    if len(top_ids) < 4:
        for it in enriched_items:
            if it["id"] not in top_ids:
                top_ids.append(it["id"])
            if len(top_ids) >= 4:
                break
    top_picks = [item_by_id[tid] for tid in top_ids[:4]]

    # 处理 Insights 并校验 evidence_ids
    insights = []
    for ins in curated.get("insights") or []:
        ev_ids = [eid for eid in (ins.get("evidence_ids") or []) if eid in item_by_id]
        insights.append({
            "title": (ins.get("title") or "").strip(),
            "body": (ins.get("body") or "").strip(),
            "evidence_ids": ev_ids,
        })

    date_str = curated.get("date") or candidates_data.get("date") or datetime.now().strftime("%Y-%m-%d")

    return {
        "date": date_str,
        "weekday": weekday_zh(date_str),
        "update_time": candidates_data.get("update_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report_title": config.get("report_title", "阿东 AI 日报"),
        "author_name": config.get("author_name", "@阿东玩 AI"),
        "author_tagline": config.get("author_tagline", "一线 Agent 工程师 · 每日 AI 前沿账本"),
        "daily_take": (curated.get("daily_take") or "").strip(),
        "stats": {
            **(candidates_data.get("stats") or {}),
            "selected_count": len(enriched_items),
        },
        "top_picks": top_picks,
        "insights": insights,
        "categories": CATEGORY_ORDER,
        "items": enriched_items,
        "sources_telemetry": candidates_data.get("sources") or [],
    }


def clean_display_url(url: str) -> str:
    return re.sub(r"[?&]scm=[^&]+", "", url or "").rstrip("?&")


def render_community_brief(ledger: dict[str, Any], max_items: int = 16) -> str:
    """生成干净利落、无 Markdown 乱码符号、可直接发微信群/飞书群的纯文本早报。"""
    lines: list[str] = []
    header_date = ledger["date"].replace("-", "年", 1).replace("-", "月", 1) + "日"
    lines.append(f"【{ledger['report_title']}】{header_date} {ledger['weekday']}")
    lines.append("")

    if ledger.get("daily_take"):
        lines.append("⚡ 今日核心主线")
        lines.append(ledger["daily_take"])
        lines.append("")

    # Top Picks
    top_picks = ledger.get("top_picks") or []
    if top_picks:
        lines.append("🔥 今日必看重磅")
        num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for i, it in enumerate(top_picks[:4]):
            badge = f"（🔥{it['resonance_count']}源共振）" if it["resonance_count"] >= 2 else f"（{it['primary_source']}）"
            lines.append(f"{num_emojis[i]} {it['headline']}{badge}")
            if it.get("one_liner"):
                lines.append(f"   ↳ {it['one_liner']}")
            if it.get("adong_note"):
                lines.append(f"   💬 阿东注：{it['adong_note']}")
            lines.append(f"   🔗 {clean_display_url(it['primary_url'])}")
        lines.append("")

    # 其余精选：按分类轮询抽取，保证社群版覆盖全领域重点而非挤在单一分类
    top_id_set = {it["id"] for it in top_picks[:4]}
    pools_by_cat: dict[str, list[dict[str, Any]]] = {}
    for it in ledger["items"]:
        if it["id"] not in top_id_set:
            pools_by_cat.setdefault(it["category"], []).append(it)

    quota = max(0, max_items - len(top_picks[:4]))
    chosen_by_cat: dict[str, list[dict[str, Any]]] = {c: [] for c in CATEGORY_ORDER}
    picked = 0
    round_idx = 0
    while picked < quota:
        added_in_round = False
        for cat in CATEGORY_ORDER:
            pool = pools_by_cat.get(cat) or []
            if round_idx < len(pool) and picked < quota:
                chosen_by_cat[cat].append(pool[round_idx])
                picked += 1
                added_in_round = True
        if not added_in_round:
            break
        round_idx += 1

    if picked > 0:
        lines.append("━━━━━━━━━━━━━━━")
        lines.append("🗂️ 分领域精选速览")
        for cat in CATEGORY_ORDER:
            cat_items = chosen_by_cat.get(cat)
            if not cat_items:
                continue
            lines.append(f"\n▸ [{cat}]")
            for it in cat_items:
                lines.append(f"• {it['headline']}")
                if it.get("one_liner"):
                    lines.append(f"  {it['one_liner']}")
                lines.append(f"  {clean_display_url(it['primary_url'])}")
        lines.append("")

    # 深度判断浓缩版
    insights = ledger.get("insights") or []
    if insights:
        lines.append("━━━━━━━━━━━━━━━")
        lines.append("💡 阿东今日趋势判断")
        for idx, ins in enumerate(insights[:5], 1):
            short_body = ins["body"].strip()
            if len(short_body) > 135:
                cut = short_body[:135]
                dot = max(cut.rfind("。"), cut.rfind("；"))
                short_body = (cut[:dot] + "。") if dot >= 60 else (cut.rstrip("，、； ") + "…")
            lines.append(f"{idx}. 【{ins['title']}】{short_body}")
        lines.append("")

    st = ledger.get("stats") or {}
    raw_cnt = st.get("raw_articles") or ledger["stats"].get("selected_count", 0)
    lines.append("━━━━━━━━━━━━━━━")
    lines.append(
        f"📊 统计：从 {raw_cnt} 篇一手动态与科技源去重提炼 · 全量精选 {st.get('selected_count', 0)} 条"
    )
    lines.append(f"✍️ 整理：{ledger['author_name']}（完整交互账本见配套 HTML 页）")
    return "\n".join(lines) + "\n"


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>__PAGE_TITLE__</title>
  <style>
    :root, [data-theme="light"] {
      --bg: #f6f7f9;
      --surface: #ffffff;
      --surface-alt: #f0f2f6;
      --border: #e2e6ee;
      --border-strong: #cbd2df;
      --text: #111827;
      --text-secondary: #4b5563;
      --text-muted: #6b7280;
      --accent: #1d4ed8;
      --accent-soft: #dbeafe;
      --accent-text: #1e40af;
      --hot-bg: #fff7ed;
      --hot-border: #fed7aa;
      --hot-text: #c2410c;
      --note-bg: #f0fdf4;
      --note-border: #bbf7d0;
      --note-text: #166534;
      --shadow: 0 1px 3px rgba(15, 23, 42, 0.05), 0 4px 14px rgba(15, 23, 42, 0.03);
    }
    [data-theme="dark"] {
      --bg: #0b0f17;
      --surface: #131a26;
      --surface-alt: #1c2536;
      --border: #263248;
      --border-strong: #374766;
      --text: #f1f5f9;
      --text-secondary: #cbd5e1;
      --text-muted: #94a3b8;
      --accent: #60a5fa;
      --accent-soft: rgba(59, 130, 246, 0.18);
      --accent-text: #93c5fd;
      --hot-bg: rgba(249, 115, 22, 0.14);
      --hot-border: rgba(251, 146, 60, 0.35);
      --hot-text: #fdba74;
      --note-bg: rgba(34, 197, 94, 0.12);
      --note-border: rgba(74, 222, 128, 0.3);
      --note-text: #86efac;
      --shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
    }
    [data-theme="paper"] {
      --bg: #f5f0e6;
      --surface: #fcfaf4;
      --surface-alt: #ede6d8;
      --border: #ded5c3;
      --border-strong: #c7bba4;
      --text: #26221c;
      --text-secondary: #524a3e;
      --text-muted: #7a7060;
      --accent: #9a3412;
      --accent-soft: #ffedd5;
      --accent-text: #9a3412;
      --hot-bg: #fef3c7;
      --hot-border: #fde68a;
      --hot-text: #b45309;
      --note-bg: #ecfccb;
      --note-border: #d9f99d;
      --note-text: #3f6212;
      --shadow: 0 2px 10px rgba(60, 45, 20, 0.06);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
      line-height: 1.6;
      -webkit-font-smoothing: antialiased;
      padding-bottom: 64px;
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }

    .container { max-width: 1120px; margin: 0 auto; padding: 0 20px; }

    /* Top Sticky Navbar */
    .topbar {
      position: sticky;
      top: 0;
      z-index: 40;
      backdrop-filter: blur(14px);
      -webkit-backdrop-filter: blur(14px);
      background: color-mix(in srgb, var(--bg) 86%, transparent);
      border-bottom: 1px solid var(--border);
      padding: 12px 0;
    }
    .topbar-inner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }
    .brand { display: flex; align-items: center; gap: 10px; }
    .brand-badge {
      background: var(--text);
      color: var(--surface);
      font-weight: 700;
      font-size: 13px;
      padding: 4px 10px;
      border-radius: 6px;
      letter-spacing: 0.5px;
    }
    .brand-date { font-size: 14px; font-weight: 600; color: var(--text-secondary); }

    .actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 7px 13px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      transition: all 0.16s ease;
    }
    .btn:hover { border-color: var(--border-strong); transform: translateY(-1px); }
    .btn-primary {
      background: var(--accent);
      color: #ffffff;
      border-color: var(--accent);
    }
    .btn-primary:hover { opacity: 0.92; border-color: var(--accent); }

    .theme-group {
      display: inline-flex;
      background: var(--surface-alt);
      padding: 3px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }
    .theme-btn {
      border: none;
      background: transparent;
      color: var(--text-muted);
      font-size: 12px;
      padding: 4px 9px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 500;
    }
    .theme-btn.active {
      background: var(--surface);
      color: var(--text);
      box-shadow: 0 1px 2px rgba(0,0,0,0.08);
    }

    /* Hero & Executive Take */
    .hero { padding: 28px 0 18px; }
    .hero-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 18px;
    }
    .hero-title { font-size: 28px; font-weight: 800; letter-spacing: -0.02em; }
    .hero-sub { font-size: 13px; color: var(--text-muted); margin-top: 4px; }
    .telemetry-pills { display: flex; gap: 8px; flex-wrap: wrap; }
    .stat-pill {
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--surface);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      font-variant-numeric: tabular-nums;
    }

    .take-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 4px solid var(--accent);
      border-radius: 12px;
      padding: 18px 20px;
      box-shadow: var(--shadow);
    }
    .take-label {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--accent);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .take-text { font-size: 15.5px; font-weight: 500; line-height: 1.7; color: var(--text); }

    /* Section Headings */
    .section { margin-top: 28px; }
    .section-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
      gap: 12px;
      flex-wrap: wrap;
    }
    .section-title { font-size: 18px; font-weight: 800; display: flex; align-items: center; gap: 8px; }
    .section-hint { font-size: 12.5px; color: var(--text-muted); }

    /* Bento Top Picks */
    .bento-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    @media (max-width: 760px) { .bento-grid { grid-template-columns: 1fr; } }

    .pick-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 12px;
      transition: border-color 0.18s ease, transform 0.18s ease;
    }
    .pick-card:hover { border-color: var(--accent); transform: translateY(-2px); }

    .badges-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
    .badge {
      font-size: 11.5px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 6px;
      background: var(--surface-alt);
      color: var(--text-secondary);
    }
    .badge-cat { background: var(--accent-soft); color: var(--accent-text); }
    .badge-hot { background: var(--hot-bg); border: 1px solid var(--hot-border); color: var(--hot-text); }
    .badge-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; color: var(--text-muted); }

    .card-title { font-size: 16px; font-weight: 700; line-height: 1.45; color: var(--text); }
    .card-summary { font-size: 13.5px; color: var(--text-secondary); line-height: 1.62; }
    .adong-note {
      font-size: 12.5px;
      padding: 8px 11px;
      border-radius: 8px;
      background: var(--note-bg);
      border: 1px solid var(--note-border);
      color: var(--note-text);
      line-height: 1.55;
    }
    .card-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding-top: 10px;
      border-top: 1px dashed var(--border);
      flex-wrap: wrap;
    }
    .source-links { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12.5px; }
    .src-link {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      font-weight: 500;
      color: var(--accent);
    }
    .mini-btn {
      border: 1px solid var(--border);
      background: var(--surface-alt);
      color: var(--text-secondary);
      font-size: 11.5px;
      padding: 3px 8px;
      border-radius: 6px;
      cursor: pointer;
    }
    .mini-btn:hover { color: var(--text); border-color: var(--border-strong); }

    /* Deep Insights Grid */
    .insights-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    @media (max-width: 760px) { .insights-grid { grid-template-columns: 1fr; } }

    .insight-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .insight-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
    .insight-num {
      font-family: ui-monospace, SFMono-Regular, monospace;
      font-size: 12px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 6px;
      background: var(--accent-soft);
      color: var(--accent-text);
      flex-shrink: 0;
    }
    .insight-title { font-size: 15.5px; font-weight: 700; line-height: 1.45; flex: 1; }
    .insight-body { font-size: 13.5px; color: var(--text-secondary); line-height: 1.68; }
    .evidence-bar { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: auto; padding-top: 6px; }
    .ev-pill {
      font-family: ui-monospace, SFMono-Regular, monospace;
      font-size: 11.5px;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--surface-alt);
      border: 1px solid var(--border);
      color: var(--accent);
      cursor: pointer;
      font-weight: 600;
    }
    .ev-pill:hover { background: var(--accent-soft); border-color: var(--accent); }

    /* Filter Toolbar */
    .filter-panel {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 16px;
      margin-bottom: 16px;
      display: flex;
      flex-direction: column;
      gap: 11px;
      box-shadow: var(--shadow);
    }
    .filter-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .pill-btn {
      border: 1px solid var(--border);
      background: var(--surface-alt);
      color: var(--text-secondary);
      font-size: 12.5px;
      font-weight: 500;
      padding: 5px 11px;
      border-radius: 999px;
      cursor: pointer;
      transition: all 0.14s;
    }
    .pill-btn:hover { color: var(--text); border-color: var(--border-strong); }
    .pill-btn.active {
      background: var(--text);
      color: var(--surface);
      border-color: var(--text);
      font-weight: 600;
    }
    .search-wrap {
      display: flex;
      align-items: center;
      gap: 10px;
      justify-content: space-between;
      flex-wrap: wrap;
    }
    .search-input {
      flex: 1;
      min-width: 220px;
      padding: 7px 12px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--bg);
      color: var(--text);
      font-size: 13px;
      outline: none;
    }
    .search-input:focus { border-color: var(--accent); }

    /* Ledger Feed */
    .cat-block { margin-bottom: 24px; }
    .cat-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;
      padding-bottom: 6px;
      border-bottom: 2px solid var(--border);
    }
    .cat-name { font-size: 16px; font-weight: 800; }
    .cat-count { font-size: 12px; color: var(--text-muted); font-weight: 600; }

    .feed-list { display: flex; flex-direction: column; gap: 10px; }
    .feed-item {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 11px;
      padding: 14px 16px;
      transition: all 0.2s ease;
    }
    .feed-item:hover { border-color: var(--border-strong); }
    .feed-item.flash-highlight {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-soft);
    }
    .feed-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }
    .feed-headline { font-size: 15px; font-weight: 700; color: var(--text); line-height: 1.45; }
    .feed-desc { font-size: 13.5px; color: var(--text-secondary); margin-top: 5px; line-height: 1.6; }
    .feed-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      margin-top: 9px;
      flex-wrap: wrap;
    }

    /* Telemetry Footer */
    details.telemetry-box {
      margin-top: 36px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 18px;
    }
    details.telemetry-box summary {
      cursor: pointer;
      font-size: 13.5px;
      font-weight: 700;
      color: var(--text-secondary);
    }
    .source-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
      gap: 8px;
      margin-top: 12px;
    }
    .source-chip {
      font-size: 12px;
      padding: 7px 10px;
      border-radius: 8px;
      background: var(--surface-alt);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }
    .dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; margin-right: 5px; }
    .dot-ok { background: #10b981; }
    .dot-cache { background: #f59e0b; }
    .dot-err { background: #ef4444; }

    /* Modal: Social Card Studio */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      z-index: 90;
      background: rgba(10, 15, 25, 0.68);
      backdrop-filter: blur(5px);
      display: none;
      align-items: center;
      justify-content: center;
      padding: 18px;
    }
    .modal-backdrop.open { display: flex; }
    .modal-dialog {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      max-width: 960px;
      width: 100%;
      max-height: 92vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      box-shadow: 0 24px 48px rgba(0,0,0,0.4);
    }
    .modal-head {
      padding: 14px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .modal-body {
      display: grid;
      grid-template-columns: 300px 1fr;
      gap: 0;
      overflow-y: auto;
    }
    @media (max-width: 800px) { .modal-body { grid-template-columns: 1fr; } }
    .studio-controls {
      padding: 18px;
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 14px;
      background: var(--surface-alt);
    }
    .ctrl-group { display: flex; flex-direction: column; gap: 6px; }
    .ctrl-label { font-size: 12px; font-weight: 700; color: var(--text-secondary); }
    .ctrl-select, .ctrl-input {
      padding: 8px 10px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--text);
      font-size: 13px;
    }
    .studio-preview {
      padding: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0d1117;
      min-height: 440px;
    }
    #card-canvas {
      max-width: 100%;
      max-height: 68vh;
      height: auto;
      border-radius: 10px;
      box-shadow: 0 12px 36px rgba(0,0,0,0.5);
    }

    /* Toast */
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 120;
      background: var(--text);
      color: var(--surface);
      padding: 10px 16px;
      border-radius: 10px;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
      opacity: 0;
      transform: translateY(10px);
      pointer-events: none;
      transition: all 0.22s ease;
    }
    .toast.show { opacity: 1; transform: translateY(0); }
  </style>
</head>
<body>
  <!-- Sticky Header -->
  <header class="topbar">
    <div class="container topbar-inner">
      <div class="brand">
        <span class="brand-badge" id="nav-brand">ADONG AI DAILY</span>
        <span class="brand-date" id="nav-date"></span>
      </div>
      <div class="actions">
        <div class="theme-group" role="group" aria-label="主题切换">
          <button class="theme-btn active" data-set-theme="light" onclick="setTheme('light')">白宣</button>
          <button class="theme-btn" data-set-theme="paper" onclick="setTheme('paper')">暖纸</button>
          <button class="theme-btn" data-set-theme="dark" onclick="setTheme('dark')">黑曜</button>
        </div>
        <button class="btn" onclick="copyCommunityBrief()">📋 一键复制社群早报</button>
        <button class="btn btn-primary" onclick="openCardStudio(0)">🎨 导出自媒体卡片</button>
      </div>
    </div>
  </header>

  <main class="container">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-header">
        <div>
          <h1 class="hero-title" id="hero-title"></h1>
          <p class="hero-sub" id="hero-sub"></p>
        </div>
        <div class="telemetry-pills" id="hero-stats"></div>
      </div>

      <div class="take-box">
        <div class="take-label">⚡ 今日 30 秒主线判断</div>
        <p class="take-text" id="daily-take"></p>
      </div>
    </section>

    <!-- Top Picks Bento -->
    <section class="section" id="sec-picks">
      <div class="section-head">
        <h2 class="section-title">🏆 今日必读 Top Picks</h2>
        <span class="section-hint">综合跨源共振热度与一线工程相关性精选</span>
      </div>
      <div class="bento-grid" id="bento-picks"></div>
    </section>

    <!-- Deep Insights -->
    <section class="section" id="sec-insights">
      <div class="section-head">
        <h2 class="section-title">🔭 阿东今日趋势判断</h2>
        <span class="section-hint">点击角标 [N001] 可直接跳转高亮对应事实源；点右上角可单张转小红书金句卡</span>
      </div>
      <div class="insights-grid" id="insights-grid"></div>
    </section>

    <!-- Full Interactive Ledger -->
    <section class="section" id="sec-ledger">
      <div class="section-head">
        <h2 class="section-title">🗂️ 全量分类情报账本</h2>
        <span class="section-hint" id="filter-count-label"></span>
      </div>

      <div class="filter-panel">
        <div class="filter-row" id="cat-pills"></div>
        <div class="search-wrap">
          <div class="filter-row" id="tier-pills">
            <button class="pill-btn active" data-tier="all" onclick="setTier('all')">全部信源</button>
            <button class="pill-btn" data-tier="resonance" onclick="setTier('resonance')">🔥 多源共振</button>
            <button class="pill-btn" data-tier="builders" onclick="setTier('builders')">🧑‍💻 X建设者·播客</button>
            <button class="pill-btn" data-tier="papers" onclick="setTier('papers')">📄 论文·官方</button>
            <button class="pill-btn" data-tier="opensource" onclick="setTier('opensource')">💻 GitHub·HN开源</button>
            <button class="pill-btn" data-tier="media" onclick="setTier('media')">📰 中文科技媒体</button>
          </div>
          <input type="search" id="search-box" class="search-input" placeholder="搜索模型、框架、公司、关键词..." oninput="renderLedger()" />
        </div>
      </div>

      <div id="ledger-container"></div>
    </section>

    <!-- Source Telemetry -->
    <details class="telemetry-box">
      <summary id="telemetry-summary">📡 查看底层多源采集健康度与缓存状态</summary>
      <div class="source-grid" id="telemetry-grid"></div>
    </details>
  </main>

  <!-- Social Media Card Studio Modal -->
  <div class="modal-backdrop" id="card-modal" onclick="if(event.target===this)closeCardStudio()">
    <div class="modal-dialog">
      <div class="modal-head">
        <div style="font-weight:800;font-size:15px;">🎨 自媒体高清分享卡片工作台（纯本地高清渲染 · 零外部依赖）</div>
        <button class="btn" onclick="closeCardStudio()">✕ 关闭</button>
      </div>
      <div class="modal-body">
        <div class="studio-controls">
          <div class="ctrl-group">
            <label class="ctrl-label">卡片规格模板</label>
            <select id="ctrl-tpl" class="ctrl-select" onchange="onStudioChange()">
              <option value="cover">小红书 / 即刻 · 今日必看封面 (3:4)</option>
              <option value="insight">小红书 / 朋友圈 · 深度判断金句卡 (3:4)</option>
              <option value="banner">公众号次条 / X · 横版头图 (16:9)</option>
            </select>
          </div>
          <div class="ctrl-group" id="ctrl-insight-wrap" style="display:none;">
            <label class="ctrl-label">选择哪条深度判断</label>
            <select id="ctrl-insight-idx" class="ctrl-select" onchange="onStudioChange()"></select>
          </div>
          <div class="ctrl-group">
            <label class="ctrl-label">视觉配色主题</label>
            <select id="ctrl-palette" class="ctrl-select" onchange="onStudioChange()">
              <option value="obsidian">极夜黑曜 (Obsidian Geek)</option>
              <option value="editorial">瑞士白宣 (Editorial Paper)</option>
              <option value="cobalt">深海靛蓝 (Cobalt Tech)</option>
            </select>
          </div>
          <div class="ctrl-group">
            <label class="ctrl-label">底部作者署名</label>
            <input id="ctrl-author" class="ctrl-input" value="" oninput="onStudioChange()" />
          </div>
          <div style="margin-top:auto;display:flex;flex-direction:column;gap:8px;padding-top:12px;">
            <button class="btn btn-primary" style="justify-content:center;padding:10px;" onclick="downloadCurrentCard()">⬇ 下载高清 PNG 图片</button>
            <button class="btn" style="justify-content:center;padding:9px;" onclick="copyCurrentCardImage()">📋 复制卡片图片到剪贴板</button>
          </div>
        </div>
        <div class="studio-preview">
          <canvas id="card-canvas" width="1080" height="1440"></canvas>
        </div>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  <script id="ledger-data" type="application/json">__LEDGER_JSON__</script>
  <script id="community-brief-data" type="application/json">__COMMUNITY_BRIEF_JSON__</script>

  <script>
    const LEDGER = JSON.parse(document.getElementById('ledger-data').textContent);
    const COMMUNITY_BRIEF = JSON.parse(document.getElementById('community-brief-data').textContent);

    let activeCat = 'all';
    let activeTier = 'all';

    function esc(s) {
      return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    }

    function showToast(msg) {
      const el = document.getElementById('toast');
      el.textContent = msg;
      el.classList.add('show');
      clearTimeout(window.__toastTimer);
      window.__toastTimer = setTimeout(() => el.classList.remove('show'), 2400);
    }

    function setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      try { localStorage.setItem('adong_daily_theme', theme); } catch(e) {}
      document.querySelectorAll('.theme-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.setTheme === theme);
      });
    }

    async function writeClip(text, okMsg) {
      try {
        await navigator.clipboard.writeText(text);
        showToast(okMsg);
      } catch (e) {
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        ta.remove();
        showToast(okMsg);
      }
    }

    function copyCommunityBrief() {
      writeClip(COMMUNITY_BRIEF, '✅ 已复制社群一键转发版，可直接粘贴到微信群/飞书群');
    }

    function copyTopicMaterial(itemId) {
      const it = LEDGER.items.find(x => x.id === itemId);
      if (!it) return;
      const links = (it.sources || []).map(s => `- ${s.name}: ${s.url}`).join('\n');
      const snippet = [
        `【选题素材 · ${it.category}】${it.headline}`,
        `核心事实：${it.one_liner}`,
        it.adong_note ? `初步判断：${it.adong_note}` : '',
        `关联信源：\n${links}`
      ].filter(Boolean).join('\n');
      writeClip(snippet, `📌 已复制 [${it.id}] 选题素材，可直接丢给写作 Skill`);
    }

    function jumpToItem(itemId) {
      // 确保筛选器未隐藏目标条目
      if (activeCat !== 'all' || activeTier !== 'all' || document.getElementById('search-box').value) {
        activeCat = 'all';
        activeTier = 'all';
        document.getElementById('search-box').value = '';
        syncPills();
        renderLedger();
      }
      const target = document.getElementById('item-' + itemId);
      if (!target) return;
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      target.classList.add('flash-highlight');
      setTimeout(() => target.classList.remove('flash-highlight'), 2200);
    }

    function renderSourceLinks(sources) {
      return (sources || []).slice(0, 4).map(s => {
        const h = s.heat ? ` (${s.heat}${s.heat_unit || ''})` : '';
        return `<a class="src-link" href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.name)}${esc(h)} ↗</a>`;
      }).join('<span style="color:var(--border-strong)">·</span>');
    }

    function initPage() {
      try {
        const saved = localStorage.getItem('adong_daily_theme');
        if (saved) setTheme(saved);
      } catch(e) {}

      document.getElementById('nav-date').textContent = `${LEDGER.date} ${LEDGER.weekday}`;
      document.getElementById('hero-title').textContent = `${LEDGER.report_title} · ${LEDGER.date}`;
      document.getElementById('hero-sub').textContent = `${LEDGER.author_name} ｜ ${LEDGER.author_tagline} ｜ 更新于 ${LEDGER.update_time}`;
      document.getElementById('daily-take').textContent = LEDGER.daily_take || '今日关键 AI 进展已聚合整理如下。';
      document.getElementById('ctrl-author').value = LEDGER.author_name || '@阿东玩 AI';

      const st = LEDGER.stats || {};
      const pills = [
        `📡 连通 ${st.ok_sources || 0}/${st.total_sources || 0} 信源`,
        `📥 原始 ${st.raw_articles || 0} 篇`,
        `🔥 跨源共振 ${st.multi_source_clusters || 0} 起`,
        `✨ 精选 ${st.selected_count || 0} 条`
      ];
      document.getElementById('hero-stats').innerHTML = pills.map(p => `<span class="stat-pill">${esc(p)}</span>`).join('');

      // Render Top Picks
      const picksHtml = (LEDGER.top_picks || []).map(it => {
        const hot = it.resonance_count >= 2 ? `<span class="badge badge-hot">🔥 ${it.resonance_count}源共振</span>` : '';
        const heat = it.heat_badge ? `<span class="badge badge-hot">★ ${esc(it.heat_badge)}</span>` : '';
        const note = it.adong_note ? `<div class="adong-note">💡 <b>一线视角：</b>${esc(it.adong_note)}</div>` : '';
        return `
          <article class="pick-card">
            <div style="display:flex;flex-direction:column;gap:8px;">
              <div class="badges-row">
                <span class="badge badge-cat">${esc(it.category)}</span>
                ${hot}
                ${heat}
                <span class="badge-id">[${esc(it.id)}]</span>
              </div>
              <h3 class="card-title"><a href="${esc(it.primary_url)}" target="_blank" rel="noopener noreferrer" style="color:inherit;">${esc(it.headline)}</a></h3>
              <p class="card-summary">${esc(it.one_liner)}</p>
              ${note}
            </div>
            <div class="card-footer">
              <div class="source-links">${renderSourceLinks(it.sources)}</div>
              <button class="mini-btn" onclick="copyTopicMaterial('${esc(it.id)}')">📌 复制选题</button>
            </div>
          </article>
        `;
      }).join('');
      document.getElementById('bento-picks').innerHTML = picksHtml;

      // Render Insights
      const insights = LEDGER.insights || [];
      if (!insights.length) {
        document.getElementById('sec-insights').style.display = 'none';
      } else {
        document.getElementById('insights-grid').innerHTML = insights.map((ins, idx) => {
          const evs = (ins.evidence_ids || []).map(eid =>
            `<button class="ev-pill" onclick="jumpToItem('${esc(eid)}')">[${esc(eid)}]</button>`
          ).join('');
          return `
            <article class="insight-card">
              <div class="insight-head">
                <span class="insight-num">判断 0${idx + 1}</span>
                <h3 class="insight-title">${esc(ins.title)}</h3>
                <button class="mini-btn" onclick="openCardStudio(${idx}, 'insight')">🖼 转卡片</button>
              </div>
              <p class="insight-body">${esc(ins.body)}</p>
              ${evs ? `<div class="evidence-bar"><span style="font-size:11.5px;color:var(--text-muted);">事实锚点：</span>${evs}</div>` : ''}
            </article>
          `;
        }).join('');

        document.getElementById('ctrl-insight-idx').innerHTML = insights.map((ins, idx) =>
          `<option value="${idx}">判断 0${idx + 1}：${esc(ins.title)}</option>`
        ).join('');
      }

      // Render Category Filter Pills
      const counts = {};
      for (const it of LEDGER.items || []) counts[it.category] = (counts[it.category] || 0) + 1;
      const catButtons = [`<button class="pill-btn active" data-cat="all" onclick="setCat('all')">全部 (${(LEDGER.items || []).length})</button>`];
      for (const cat of LEDGER.categories || []) {
        if (counts[cat]) {
          catButtons.push(`<button class="pill-btn" data-cat="${esc(cat)}" onclick="setCat('${esc(cat)}')">${esc(cat)} (${counts[cat]})</button>`);
        }
      }
      document.getElementById('cat-pills').innerHTML = catButtons.join('');

      // Render Telemetry
      const tele = LEDGER.sources_telemetry || [];
      document.getElementById('telemetry-summary').textContent =
        `📡 底层多源健康度监控（共 ${tele.length} 个公开源 · 免登录直连 · 单源独立缓存）`;
      document.getElementById('telemetry-grid').innerHTML = tele.map(t => {
        const cls = t.status === 'ok' ? 'dot-ok' : (t.status === 'error' ? 'dot-err' : 'dot-cache');
        const label = t.status === 'ok' ? `${t.article_count}篇` : (t.status === 'error' ? '异常' : `${t.article_count}篇(缓存)`);
        return `
          <div class="source-chip" title="${esc(t.note || t.fetched_at || '')}">
            <span><i class="dot ${cls}"></i>${esc(t.source_name)}</span>
            <span style="color:var(--text-muted);font-variant-numeric:tabular-nums;">${esc(label)}</span>
          </div>
        `;
      }).join('');

      renderLedger();
    }

    function syncPills() {
      document.querySelectorAll('#cat-pills .pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.cat === activeCat);
      });
      document.querySelectorAll('#tier-pills .pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.tier === activeTier);
      });
    }

    function setCat(cat) { activeCat = cat; syncPills(); renderLedger(); }
    function setTier(tier) { activeTier = tier; syncPills(); renderLedger(); }

    function matchTier(it, tier) {
      if (tier === 'all') return true;
      if (tier === 'resonance') return (it.resonance_count || 1) >= 2;
      if (tier === 'papers') return it.tier === 'papers' || it.tier === 'official';
      return it.tier === tier;
    }

    function renderLedger() {
      const q = (document.getElementById('search-box').value || '').trim().toLowerCase();
      const filtered = (LEDGER.items || []).filter(it => {
        if (activeCat !== 'all' && it.category !== activeCat) return false;
        if (!matchTier(it, activeTier)) return false;
        if (q) {
          const blob = `${it.headline} ${it.one_liner} ${it.adong_note} ${it.primary_source} ${(it.focus_hits||[]).join(' ')}`.toLowerCase();
          if (!blob.includes(q)) return false;
        }
        return true;
      });

      document.getElementById('filter-count-label').textContent = `当前显示 ${filtered.length} / ${(LEDGER.items || []).length} 条`;

      if (!filtered.length) {
        document.getElementById('ledger-container').innerHTML =
          `<div style="padding:36px;text-align:center;color:var(--text-muted);background:var(--surface);border-radius:12px;border:1px solid var(--border);">没有匹配的条目，试试切换筛选标签或清空搜索词。</div>`;
        return;
      }

      const grouped = {};
      for (const it of filtered) {
        (grouped[it.category] = grouped[it.category] || []).push(it);
      }

      const blocks = [];
      for (const cat of LEDGER.categories || []) {
        const list = grouped[cat];
        if (!list || !list.length) continue;
        const rowsHtml = list.map(it => {
          const hot = it.resonance_count >= 2 ? `<span class="badge badge-hot">🔥 ${it.resonance_count}源</span>` : '';
          const heat = it.heat_badge ? `<span class="badge badge-hot">★ ${esc(it.heat_badge)}</span>` : '';
          const hits = (it.focus_hits || []).slice(0, 3).map(h => `<span class="badge">🎯 ${esc(h)}</span>`).join('');
          const note = it.adong_note ? `<div class="adong-note" style="margin-top:7px;">💡 ${esc(it.adong_note)}</div>` : '';
          return `
            <article class="feed-item" id="item-${esc(it.id)}">
              <div class="feed-top">
                <div class="feed-headline">
                  <span class="badge-id" style="margin-right:6px;">[${esc(it.id)}]</span>
                  <a href="${esc(it.primary_url)}" target="_blank" rel="noopener noreferrer" style="color:inherit;">${esc(it.headline)}</a>
                </div>
                <div class="badges-row" style="flex-shrink:0;">${hot}${heat}${hits}</div>
              </div>
              <p class="feed-desc">${esc(it.one_liner)}</p>
              ${note}
              <div class="feed-meta">
                <div class="source-links">${renderSourceLinks(it.sources)}</div>
                <button class="mini-btn" onclick="copyTopicMaterial('${esc(it.id)}')">📌 复制选题</button>
              </div>
            </article>
          `;
        }).join('');

        blocks.push(`
          <div class="cat-block">
            <div class="cat-header">
              <h3 class="cat-name">${esc(cat)}</h3>
              <span class="cat-count">${list.length} 条</span>
            </div>
            <div class="feed-list">${rowsHtml}</div>
          </div>
        `);
      }
      document.getElementById('ledger-container').innerHTML = blocks.join('');
    }

    /* =====================================================================
       纯原生 HTML5 Canvas 自媒体高清卡片渲染引擎（零外部依赖，离线可用）
       ===================================================================== */
    const PALETTES = {
      obsidian: {
        bg1: '#0b101b', bg2: '#131c2e', card: '#19243a', border: '#2b3b5c',
        text: '#f8fafc', sub: '#cbd5e1', muted: '#94a3b8',
        accent: '#3b82f6', accentSoft: 'rgba(59,130,246,0.2)', hot: '#fb923c'
      },
      editorial: {
        bg1: '#f7f5f0', bg2: '#eeeae0', card: '#ffffff', border: '#dcd5c7',
        text: '#18181b', sub: '#3f3f46', muted: '#71717a',
        accent: '#b91c1c', accentSoft: 'rgba(185,28,28,0.1)', hot: '#c2410c'
      },
      cobalt: {
        bg1: '#0f172a', bg2: '#1e1b4b', card: 'rgba(30,41,59,0.88)', border: '#4338ca',
        text: '#f8fafc', sub: '#e2e8f0', muted: '#a5b4fc',
        accent: '#818cf8', accentSoft: 'rgba(129,140,248,0.22)', hot: '#fbbf24'
      }
    };

    function roundRect(ctx, x, y, w, h, r) {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }

    function wrapLines(ctx, text, maxWidth, maxLines) {
      // 中英混排分词折行：保证英文整词不断裂，中文标点不孤立出现在行首
      const raw = String(text || '');
      const units = raw.match(/[A-Za-z0-9_+#./-]+|[0-9]+(?:\.[0-9]+)?%?|\n|[\u4e00-\u9fff][，。！？：；、）》」”’%]*|./gu) || [];
      const lines = [];
      let line = '';
      for (let i = 0; i < units.length; i++) {
        const tok = units[i];
        if (tok === '\n') {
          lines.push(line.trimEnd());
          line = '';
          if (maxLines && lines.length >= maxLines) break;
          continue;
        }
        if (!line && tok === ' ') continue;
        const test = line + tok;
        if (ctx.measureText(test).width > maxWidth && line.trim()) {
          if (maxLines && lines.length + 1 >= maxLines) {
            let trimmed = line.trimEnd();
            while (trimmed.length > 1 && ctx.measureText(trimmed + '…').width > maxWidth) {
              trimmed = trimmed.slice(0, -1);
            }
            lines.push(trimmed + '…');
            return lines;
          }
          lines.push(line.trimEnd());
          line = tok === ' ' ? '' : tok;
        } else {
          line = test;
        }
      }
      if (line.trim() && (!maxLines || lines.length < maxLines)) {
        lines.push(line.trimEnd());
      }
      return lines;
    }

    window.renderCardToCanvas = function(tpl, paletteName, insightIdx, authorOverride) {
      const canvas = document.getElementById('card-canvas');
      const ctx = canvas.getContext('2d');
      const pal = PALETTES[paletteName] || PALETTES.obsidian;
      const author = authorOverride || LEDGER.author_name || '@阿东玩 AI';
      const fontStack = '-apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", sans-serif';

      if (tpl === 'banner') {
        canvas.width = 1600;
        canvas.height = 900;
      } else {
        canvas.width = 1080;
        canvas.height = 1440;
      }

      const W = canvas.width, H = canvas.height;
      const grad = ctx.createLinearGradient(0, 0, W, H);
      grad.addColorStop(0, pal.bg1);
      grad.addColorStop(1, pal.bg2);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      // Subtle decorative grid dots
      ctx.fillStyle = pal.border;
      ctx.globalAlpha = 0.25;
      for (let gx = 48; gx < W; gx += 48) {
        for (let gy = 48; gy < H; gy += 48) {
          ctx.fillRect(gx, gy, 2, 2);
        }
      }
      ctx.globalAlpha = 1.0;

      if (tpl === 'cover') {
        // Header Pill
        ctx.font = `700 22px ${fontStack}`;
        const pillLabel = `ADONG AI DAILY · ${LEDGER.date}`;
        const pillW = ctx.measureText(pillLabel).width + 48;
        roundRect(ctx, 68, 68, pillW, 48, 24);
        ctx.fillStyle = pal.accentSoft;
        ctx.fill();
        ctx.fillStyle = pal.accent;
        ctx.fillText(pillLabel, 92, 100);

        ctx.font = `600 22px ${fontStack}`;
        ctx.fillStyle = pal.muted;
        const st = LEDGER.stats || {};
        const rightStat = `${LEDGER.weekday} ｜ ${st.raw_articles || 0}篇源动态去重精选`;
        ctx.fillText(rightStat, W - 68 - ctx.measureText(rightStat).width, 100);

        // Main Title
        ctx.font = `800 56px ${fontStack}`;
        ctx.fillStyle = pal.text;
        ctx.fillText(`${LEDGER.report_title} · 今日核心看点`, 68, 192);

        // Executive Take Box
        roundRect(ctx, 68, 226, W - 136, 178, 20);
        ctx.fillStyle = pal.card;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = pal.border;
        ctx.stroke();

        ctx.fillStyle = pal.accent;
        ctx.fillRect(68, 248, 6, 134);

        ctx.font = `600 27px ${fontStack}`;
        ctx.fillStyle = pal.sub;
        const takeLines = wrapLines(ctx, LEDGER.daily_take || '', W - 204, 3);
        takeLines.forEach((ln, idx) => ctx.fillText(ln, 102, 276 + idx * 44));

        // Top 4 Picks Cards
        const picks = (LEDGER.top_picks || LEDGER.items || []).slice(0, 4);
        let yCursor = 436;
        picks.forEach((it, idx) => {
          const cardH = 205;
          roundRect(ctx, 68, yCursor, W - 136, cardH, 20);
          ctx.fillStyle = pal.card;
          ctx.fill();
          ctx.strokeStyle = pal.border;
          ctx.stroke();

          // Category tag
          ctx.font = `700 20px ${fontStack}`;
          const tagText = `0${idx + 1} · ${it.category}`;
          const tagW = ctx.measureText(tagText).width + 28;
          roundRect(ctx, 96, yCursor + 24, tagW, 34, 8);
          ctx.fillStyle = pal.accentSoft;
          ctx.fill();
          ctx.fillStyle = pal.accent;
          ctx.fillText(tagText, 110, yCursor + 48);

          // Resonance / Source
          ctx.font = `600 20px ${fontStack}`;
          ctx.fillStyle = pal.hot;
          const badgeStr = it.resonance_count >= 2 ? `🔥 ${it.resonance_count}源同题共振` : `来源：${it.primary_source}`;
          ctx.fillText(badgeStr, 96 + tagW + 18, yCursor + 48);

          // Headline
          ctx.font = `700 29px ${fontStack}`;
          ctx.fillStyle = pal.text;
          const hLines = wrapLines(ctx, it.headline, W - 196, 2);
          hLines.forEach((ln, li) => ctx.fillText(ln, 96, yCursor + 96 + li * 38));

          // One-liner
          const descY = yCursor + 96 + hLines.length * 38 + 6;
          if (hLines.length === 1) {
            ctx.font = `500 23px ${fontStack}`;
            ctx.fillStyle = pal.muted;
            const dLines = wrapLines(ctx, it.one_liner, W - 196, 2);
            dLines.forEach((ln, li) => ctx.fillText(ln, 96, descY + li * 32));
          } else {
            ctx.font = `500 22px ${fontStack}`;
            ctx.fillStyle = pal.muted;
            const dLines = wrapLines(ctx, it.one_liner, W - 196, 1);
            if (dLines[0]) ctx.fillText(dLines[0], 96, descY + 2);
          }

          yCursor += cardH + 20;
        });

        // Footer Signature
        ctx.font = `700 24px ${fontStack}`;
        ctx.fillStyle = pal.text;
        ctx.fillText(author, 68, H - 52);
        ctx.font = `500 21px ${fontStack}`;
        ctx.fillStyle = pal.muted;
        const footRight = LEDGER.author_tagline || '免登录多源直连 · 去套话工程账本';
        ctx.fillText(footRight, W - 68 - ctx.measureText(footRight).width, H - 52);

      } else if (tpl === 'insight') {
        const ins = (LEDGER.insights || [])[insightIdx || 0] || {
          title: LEDGER.report_title,
          body: LEDGER.daily_take,
          evidence_ids: []
        };

        ctx.font = `700 22px ${fontStack}`;
        const insLabel = `阿东趋势判断 #0${(Number(insightIdx)||0)+1} · ${LEDGER.date}`;
        const insPillW = ctx.measureText(insLabel).width + 52;
        roundRect(ctx, 72, 76, insPillW, 48, 24);
        ctx.fillStyle = pal.accentSoft;
        ctx.fill();
        ctx.fillStyle = pal.accent;
        ctx.fillText(insLabel, 98, 108);

        // Big Quote Accent
        ctx.font = `900 120px Georgia, serif`;
        ctx.fillStyle = pal.accentSoft;
        ctx.fillText('“', 64, 250);

        // Insight Title
        ctx.font = `800 50px ${fontStack}`;
        ctx.fillStyle = pal.text;
        const tLines = wrapLines(ctx, ins.title, W - 144, 3);
        tLines.forEach((ln, idx) => ctx.fillText(ln, 72, 248 + idx * 66));

        // Body Card (dynamic height)
        ctx.font = `500 32px ${fontStack}`;
        const bLines = wrapLines(ctx, ins.body, W - 216, 10);
        const bodyTop = 264 + tLines.length * 66;
        const bodyCardH = Math.max(360, bLines.length * 52 + 84);
        roundRect(ctx, 72, bodyTop, W - 144, bodyCardH, 24);
        ctx.fillStyle = pal.card;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = pal.border;
        ctx.stroke();

        ctx.font = `500 32px ${fontStack}`;
        ctx.fillStyle = pal.sub;
        bLines.forEach((ln, idx) => ctx.fillText(ln, 108, bodyTop + 66 + idx * 52));

        // Cited Evidence Stories
        const evItems = (ins.evidence_ids || [])
          .map(eid => (LEDGER.items || []).find(x => x.id === eid))
          .filter(Boolean)
          .slice(0, 3);

        if (evItems.length) {
          const evTop = bodyTop + bodyCardH + 56;
          ctx.font = `700 23px ${fontStack}`;
          ctx.fillStyle = pal.accent;
          ctx.fillText('🔗 关联事实锚点', 72, evTop);

          evItems.forEach((ev, idx) => {
            ctx.font = `600 24px ${fontStack}`;
            ctx.fillStyle = pal.text;
            const line = `• [${ev.primary_source}] ${ev.headline}`;
            const wrapped = wrapLines(ctx, line, W - 144, 1);
            ctx.fillText(wrapped[0], 72, evTop + 44 + idx * 44);
          });
        }

        ctx.font = `700 25px ${fontStack}`;
        ctx.fillStyle = pal.text;
        ctx.fillText(author, 72, H - 56);
        ctx.font = `500 22px ${fontStack}`;
        ctx.fillStyle = pal.muted;
        const rText = `${LEDGER.report_title} · 讲人话、看数据、给判断`;
        ctx.fillText(rText, W - 72 - ctx.measureText(rText).width, H - 56);

      } else if (tpl === 'banner') {
        // Left Column (44%)
        const leftW = 640;
        roundRect(ctx, 64, 64, 300, 44, 22);
        ctx.fillStyle = pal.accentSoft;
        ctx.fill();
        ctx.font = `700 20px ${fontStack}`;
        ctx.fillStyle = pal.accent;
        ctx.fillText(`${LEDGER.date} · ${LEDGER.weekday}`, 88, 93);

        ctx.font = `800 54px ${fontStack}`;
        ctx.fillStyle = pal.text;
        ctx.fillText(LEDGER.report_title, 64, 184);

        ctx.font = `500 26px ${fontStack}`;
        ctx.fillStyle = pal.sub;
        const tLines = wrapLines(ctx, LEDGER.daily_take || '', leftW - 20, 7);
        tLines.forEach((ln, idx) => ctx.fillText(ln, 64, 252 + idx * 42));

        ctx.font = `700 24px ${fontStack}`;
        ctx.fillStyle = pal.text;
        ctx.fillText(`${author} ｜ ${LEDGER.author_tagline}`, 64, H - 64);

        // Right Column: Top 3 Cards
        const rightX = 748;
        const rightW = W - rightX - 64;
        const picks = (LEDGER.top_picks || LEDGER.items || []).slice(0, 3);
        picks.forEach((it, idx) => {
          const cy = 64 + idx * 264;
          roundRect(ctx, rightX, cy, rightW, 240, 20);
          ctx.fillStyle = pal.card;
          ctx.fill();
          ctx.lineWidth = 2;
          ctx.strokeStyle = pal.border;
          ctx.stroke();

          ctx.font = `700 20px ${fontStack}`;
          ctx.fillStyle = pal.accent;
          const badge = it.resonance_count >= 2 ? `🔥 ${it.resonance_count}源共振` : it.primary_source;
          ctx.fillText(`[${it.category}] · ${badge}`, rightX + 28, cy + 44);

          ctx.font = `700 28px ${fontStack}`;
          ctx.fillStyle = pal.text;
          const hl = wrapLines(ctx, it.headline, rightW - 56, 2);
          hl.forEach((ln, li) => ctx.fillText(ln, rightX + 28, cy + 92 + li * 38));

          ctx.font = `500 21px ${fontStack}`;
          ctx.fillStyle = pal.muted;
          const dl = wrapLines(ctx, it.one_liner, rightW - 56, 1);
          if (dl[0]) ctx.fillText(dl[0], rightX + 28, cy + 206);
        });
      }

      return canvas.toDataURL('image/png');
    };

    function openCardStudio(insightIndex, forceTpl) {
      if (forceTpl) document.getElementById('ctrl-tpl').value = forceTpl;
      if (typeof insightIndex === 'number') {
        document.getElementById('ctrl-insight-idx').value = String(insightIndex);
      }
      document.getElementById('card-modal').classList.add('open');
      onStudioChange();
    }

    function closeCardStudio() {
      document.getElementById('card-modal').classList.remove('open');
    }

    function onStudioChange() {
      const tpl = document.getElementById('ctrl-tpl').value;
      const pal = document.getElementById('ctrl-palette').value;
      const idx = Number(document.getElementById('ctrl-insight-idx').value || 0);
      const author = document.getElementById('ctrl-author').value;
      document.getElementById('ctrl-insight-wrap').style.display = tpl === 'insight' ? 'flex' : 'none';
      window.renderCardToCanvas(tpl, pal, idx, author);
    }

    function downloadCurrentCard() {
      const tpl = document.getElementById('ctrl-tpl').value;
      const canvas = document.getElementById('card-canvas');
      const link = document.createElement('a');
      link.download = `${LEDGER.date}_adong_ai_${tpl}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
      showToast('⬇ 高清 PNG 卡片已开始下载');
    }

    async function copyCurrentCardImage() {
      const canvas = document.getElementById('card-canvas');
      try {
        const blob = await new Promise(res => canvas.toBlob(res, 'image/png'));
        await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
        showToast('✅ 高清卡片图片已复制，可直接粘贴到微信 / 小红书网页版');
      } catch (e) {
        downloadCurrentCard();
      }
    }

    initPage();
  </script>
</body>
</html>
"""


def render_html(ledger: dict[str, Any], community_brief: str) -> str:
    safe_ledger = json.dumps(ledger, ensure_ascii=False).replace("</", "<\\/")
    safe_brief = json.dumps(community_brief, ensure_ascii=False).replace("</", "<\\/")
    page_title = f"{ledger['report_title']} · {ledger['date']} {ledger['weekday']}"
    return (
        HTML_TEMPLATE
        .replace("__PAGE_TITLE__", page_title)
        .replace("__LEDGER_JSON__", safe_ledger)
        .replace("__COMMUNITY_BRIEF_JSON__", safe_brief)
    )


def update_archive_index(ledger: dict[str, Any], html_path: Path, brief_path: Path) -> None:
    idx_path = SKILL_ROOT / "cache" / "ledger_index.json"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        index_data = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {"days": []}
    except Exception:
        index_data = {"days": []}

    days = [d for d in index_data.get("days", []) if d.get("date") != ledger["date"]]
    days.insert(0, {
        "date": ledger["date"],
        "weekday": ledger["weekday"],
        "selected_count": ledger["stats"].get("selected_count", 0),
        "daily_take": ledger.get("daily_take", ""),
        "html_path": str(html_path),
        "community_brief_path": str(brief_path),
        "updated_at": ledger["update_time"],
    })
    index_data["days"] = days[:90]
    idx_path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_merged_config(cfg_path: Path) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if cfg_path.exists():
        config = json.loads(cfg_path.read_text(encoding="utf-8"))
    local_override = cfg_path.with_name("config.local.json")
    if local_override.exists():
        try:
            override_data = json.loads(local_override.read_text(encoding="utf-8"))
            config.update(override_data)
        except Exception:
            pass
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="adong-ai-daily · 渲染自包含交互式 HTML 与社群一键转发版")
    parser.add_argument("--candidates", required=True, help="候选池 JSON 路径（由 collect_sources.py 生成）")
    parser.add_argument("--curated", default="", help="Agent 生成的结构化策展 JSON 路径")
    parser.add_argument("--auto", action="store_true", help="未提供 --curated 时启用确定性无套话提炼模式")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="配置文件路径")
    parser.add_argument("--out-dir", default="", help="交付物输出目录")
    args = parser.parse_args()

    cfg_path = Path(args.config).expanduser()
    config = load_merged_config(cfg_path)

    cand_path = Path(args.candidates).expanduser()
    if not cand_path.exists():
        print(f"❌ 找不到候选池文件: {cand_path}", file=sys.stderr)
        sys.exit(1)

    candidates_data = json.loads(cand_path.read_text(encoding="utf-8"))

    if args.curated:
        cur_path = Path(args.curated).expanduser()
        if not cur_path.exists():
            print(f"❌ 找不到策展文件: {cur_path}", file=sys.stderr)
            sys.exit(1)
        curated = json.loads(cur_path.read_text(encoding="utf-8"))
    elif args.auto:
        curated = build_auto_curated(candidates_data, config)
    else:
        print("❌ 请提供 --curated <curated.json>（推荐由 Agent 按契约生成），或显式指定 --auto", file=sys.stderr)
        sys.exit(1)

    ledger = merge_and_validate(candidates_data, curated, config)
    out_dir = resolve_output_dir(args.out_dir, config)

    brief_max = int((config.get("limits") or {}).get("community_brief_max", 15))
    community_brief = render_community_brief(ledger, max_items=brief_max)
    html_content = render_html(ledger, community_brief)

    html_file = out_dir / f"{ledger['date']}_ai_daily_report.html"
    brief_file = out_dir / f"{ledger['date']}_community_brief.txt"

    html_file.write_text(html_content, encoding="utf-8")
    brief_file.write_text(community_brief, encoding="utf-8")
    update_archive_index(ledger, html_file, brief_file)

    print(f"✅ 交互式 HTML 日报账本: {html_file}")
    print(f"✅ 社群一键转发纯文本版: {brief_file}")


if __name__ == "__main__":
    main()
