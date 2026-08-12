#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import os
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

from career_state import (
    FIT_LABELS,
    INTERVIEW_STATUS_LABELS,
    OFFER_STATUS_LABELS,
    PRIORITY_LABELS,
    STATUS_LABELS,
    calculate_funnel,
    load_state,
    next_actions,
    opportunity_map,
    state_digest,
    validate_state,
)
from common import active_view_names, load_profile, workspace_path


CLOSED_STATUSES = {"rejected", "withdrawn", "paused"}
WAITING_STATUSES = {"applied", "referred", "screening"}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def relative_link(path: str) -> str:
    return "../../" + quote(path, safe="/.-_")


def render_metrics(state: dict) -> str:
    funnel = {item["key"]: item for item in calculate_funnel(state)}
    active = sum(item["status"] not in CLOSED_STATUSES | {"offer"} for item in state["opportunities"])
    interviews = sum(item["status"] == "scheduled" for item in state["interviews"])
    values = (
        (active, "活跃岗位"),
        (funnel["applied"]["count"], "累计投递"),
        (funnel["responses"]["count"], "获得回复"),
        (interviews, "待进行面试"),
        (funnel["offers"]["count"], "Offer"),
    )
    return "".join(f'<div class="metric"><strong>{value}</strong><span>{label}</span></div>' for value, label in values)


def render_actions(state: dict) -> str:
    actions = next_actions(state)
    return "".join(
        f"""<article class="action-item">
  <span class="action-rank">{index:02d}</span>
  <div class="action-copy"><strong>{esc(item['action'])}</strong><p>{esc(item['company'])}{' / ' if item['company'] and item['role'] else ''}{esc(item['role'])}<br>{esc(item['reason'])}</p></div>
  <time class="action-due">{esc(item['due'] or '尽快')}</time>
</article>"""
        for index, item in enumerate(actions, start=1)
    )


def render_funnel(state: dict) -> str:
    return "".join(
        f'<div class="funnel-row"><div>{item["label"]}</div><strong>{item["count"]}</strong><span>{"起点" if item["conversion"] is None else str(item["conversion"]) + "%"}</span></div>'
        for item in calculate_funnel(state)
    )


def render_artifacts(workspace: Path, profile: dict, state: dict) -> str:
    artifacts: list[tuple[str, str, str]] = []
    for view_name in active_view_names(profile):
        label = "Agent 开发简历" if view_name == "development" else "Agent 算法简历"
        pdf = workspace / "outputs" / "resumes" / view_name / "main.pdf"
        if pdf.is_file():
            artifacts.append((label, f"outputs/resumes/{view_name}/main.pdf", "PDF"))
    portfolio = workspace / "outputs" / "portfolio" / "index.html"
    if portfolio.is_file():
        artifacts.append(("候选人作品集", "outputs/portfolio/index.html", "网页"))
    for job in state["opportunities"]:
        request = job.get("application_request", "")
        if request and (workspace / request).is_file():
            packet = str(Path(request).with_name("application-packet.md"))
            artifacts.append((f"{job['company']}投递包", packet, "Markdown"))
    if not artifacts:
        return '<div class="empty-state">还没有生成简历或投递包。先完成候选人档案，再为最高优先岗位准备材料。</div>'
    return "".join(
        f'<a class="artifact" href="{relative_link(path)}"><strong>{esc(label)}</strong><span>{kind}</span></a>'
        for label, path, kind in artifacts
    )


def status_class(status: str) -> str:
    if status in CLOSED_STATUSES:
        return "closed"
    if status in WAITING_STATUSES:
        return "waiting"
    return "active"


def render_filters(state: dict) -> str:
    statuses = {item["status"] for item in state["opportunities"]}
    buttons = ['<button type="button" data-status-filter="all" aria-pressed="true">全部</button>']
    buttons.extend(
        f'<button type="button" data-status-filter="{status}" aria-pressed="false">{STATUS_LABELS[status]}</button>'
        for status in STATUS_LABELS
        if status in statuses
    )
    return "".join(buttons)


def render_jobs(state: dict) -> str:
    if not state["opportunities"]:
        return '<div class="empty-state">岗位池还是空的。先添加 3-5 个真实 JD，系统会给出优先级和下一步。</div>'
    actions = {item["opportunity_id"]: item for item in next_actions(state) if item["opportunity_id"]}
    priority_rank = {"high": 0, "medium": 1, "low": 2}
    jobs = sorted(state["opportunities"], key=lambda item: (item["status"] in CLOSED_STATUSES, priority_rank[item["priority"]], item["company"]))
    rows: list[str] = []
    for item in jobs:
        action = actions.get(item["id"], {})
        links: list[str] = []
        if item.get("url"):
            links.append(f'<a href="{esc(item["url"])}">JD</a>')
        if item.get("application_request"):
            packet = str(Path(item["application_request"]).with_name("application-packet.md"))
            links.append(f'<a href="{relative_link(packet)}">投递包</a>')
        reasons = item.get("fit_reasons") or item.get("gaps") or ["尚未完成适配判断"]
        rows.append(
            f"""<article class="job" data-job-status="{item['status']}">
  <div><h3>{esc(item['company'])}</h3><p class="role">{esc(item['role'])} / {PRIORITY_LABELS[item['priority']]}优先级 / {FIT_LABELS[item['fit']]}</p></div>
  <p class="job-reason">{esc('；'.join(reasons[:2]))}</p>
  <div class="job-action"><span class="status {status_class(item['status'])}">{STATUS_LABELS[item['status']]}</span><strong>{esc(action.get('action') or item.get('next_action') or '等待下一状态')}</strong><span>{esc(action.get('due') or item.get('next_action_date'))}</span></div>
  <div class="job-links">{''.join(links)}</div>
</article>"""
        )
    return "".join(rows)


def render_interviews(state: dict) -> str:
    if not state["interviews"]:
        return '<div class="empty-state">还没有面试记录。收到面试安排后，记录时间、轮次和准备重点。</div>'
    jobs = opportunity_map(state)
    rows = "".join(
        f"<tr><td><strong>{esc(jobs[item['opportunity_id']]['company'])}</strong><span>{esc(jobs[item['opportunity_id']]['role'])}</span></td><td>{esc(item['round'])}</td><td>{esc(item['date'])}</td><td>{INTERVIEW_STATUS_LABELS[item['status']]}</td><td>{esc(item.get('focus'))}</td><td>{esc(item.get('result') or '待记录')}</td></tr>"
        for item in sorted(state["interviews"], key=lambda value: value["date"])
    )
    return f"<table><thead><tr><th>岗位</th><th>轮次</th><th>日期</th><th>状态</th><th>准备重点</th><th>结果</th></tr></thead><tbody>{rows}</tbody></table>"


def render_offers(state: dict) -> str:
    if not state["offers"]:
        return '<div class="empty-state">Offer 到达后会在这里集中比较薪酬、职级、条件、截止日期与风险。</div>'
    jobs = opportunity_map(state)
    cards: list[str] = []
    for item in state["offers"]:
        job = jobs[item["opportunity_id"]]
        risks = "；".join(item.get("risks", [])) or item.get("conditions") or "暂无补充风险"
        cards.append(
            f"""<article class="offer">
  <header><div><h3>{esc(job['company'])}</h3><p>{esc(job['role'])}{' / ' + esc(item['level']) if item.get('level') else ''}</p></div><span class="status active">{OFFER_STATUS_LABELS[item['status']]}</span></header>
  <dl><div><dt>现金</dt><dd>{esc(item.get('cash') or '待确认')}</dd></div><div><dt>股权</dt><dd>{esc(item.get('equity') or '待确认')}</dd></div><div><dt>截止日期</dt><dd>{esc(item.get('deadline') or '待确认')}</dd></div></dl>
  <p class="risk">{esc(risks)}</p>
</article>"""
        )
    return "".join(cards)


def render_dashboard(workspace: Path, state: dict | None = None) -> Path:
    workspace = workspace.resolve()
    state = state or load_state(workspace)
    errors = validate_state(state, workspace)
    if errors:
        raise ValueError("求职状态无效：\n- " + "\n- ".join(errors))
    profile = load_profile(workspace)
    candidate = profile.get("candidate", {})
    target = state["target"]
    target_title = "拿到满足底线的目标 Offer"
    if target["roles"]:
        target_title = " / ".join(target["roles"])
    target_detail = target["notes"] or "围绕真实岗位持续推进投递、面试与 Offer，不用准备动作替代结果。"
    target_meta = "".join(
        f"<div><span>{label}</span><strong>{esc(value or '待确定')}</strong></div>"
        for label, value in (
            ("目标城市", "、".join(target["locations"])),
            ("Offer 底线", target["minimum_offer"]),
            ("目标日期", target["deadline"]),
        )
    )
    data = {
        "candidate_name": esc(candidate.get("name") or "候选人"),
        "candidate_headline": esc(candidate.get("headline") or "Agent 求职"),
        "target_title": esc(target_title),
        "target_detail": esc(target_detail),
        "target_meta": target_meta,
        "metrics": render_metrics(state),
        "actions": render_actions(state),
        "funnel": render_funnel(state),
        "artifacts": render_artifacts(workspace, profile, state),
        "filters": render_filters(state),
        "jobs": render_jobs(state),
        "interviews": render_interviews(state),
        "offers": render_offers(state),
    }
    output_parent = workspace / "outputs"
    output_parent.mkdir(exist_ok=True)
    output_dir = output_parent / "career-dashboard"
    staging = Path(tempfile.mkdtemp(prefix=".career-dashboard-", dir=output_parent))
    assets = Path(__file__).resolve().parents[1] / "assets" / "career-dashboard"
    template = (assets / "index.html.template").read_text(encoding="utf-8")
    for key, value in data.items():
        template = template.replace("{{" + key + "}}", value)
    template = f"<!-- career-state-sha256: {state_digest(state)} -->\n" + template
    (staging / "index.html").write_text(template, encoding="utf-8")
    shutil.copy2(assets / "style.css", staging / "style.css")
    shutil.copy2(assets / "app.js", staging / "app.js")
    backup = output_parent / ".career-dashboard-backup"
    if backup.exists():
        shutil.rmtree(backup)
    if output_dir.exists():
        os.replace(output_dir, backup)
    os.replace(staging, output_dir)
    if backup.exists():
        shutil.rmtree(backup)
    return output_dir / "index.html"


def main() -> None:
    parser = argparse.ArgumentParser(description="从求职状态生成中文 Offer 驾驶舱。")
    parser.add_argument("workspace")
    args = parser.parse_args()
    try:
        print(render_dashboard(workspace_path(args.workspace)))
    except (OSError, ValueError) as error:
        raise SystemExit(f"驾驶舱生成失败：\n{error}") from None


if __name__ == "__main__":
    main()
