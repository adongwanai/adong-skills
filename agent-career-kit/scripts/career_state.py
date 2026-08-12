#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


STATE_NAME = "career-state.json"
OPPORTUNITY_STATUSES = {
    "researching",
    "preparing",
    "referred",
    "applied",
    "screening",
    "interviewing",
    "offer",
    "rejected",
    "paused",
    "withdrawn",
}
STATUS_LABELS = {
    "researching": "调研中",
    "preparing": "准备中",
    "referred": "已内推",
    "applied": "已投递",
    "screening": "筛选中",
    "interviewing": "面试中",
    "offer": "Offer",
    "rejected": "拒绝",
    "paused": "暂停",
    "withdrawn": "主动结束",
}
EVENT_TYPES = {
    "sourced",
    "materials_ready",
    "referred",
    "applied",
    "response",
    "interview_scheduled",
    "interview_passed",
    "interview_failed",
    "offer",
    "rejected",
    "follow_up",
    "withdrawn",
    "note",
}
EVENT_LABELS = {
    "sourced": "发现岗位",
    "materials_ready": "材料就绪",
    "referred": "完成内推",
    "applied": "完成投递",
    "response": "收到回复",
    "interview_scheduled": "安排面试",
    "interview_passed": "通过面试",
    "interview_failed": "面试未通过",
    "offer": "收到 Offer",
    "rejected": "收到拒绝",
    "follow_up": "完成跟进",
    "withdrawn": "主动结束",
    "note": "补充记录",
}
PRIORITIES = {"high", "medium", "low"}
PRIORITY_LABELS = {"high": "高", "medium": "中", "low": "低"}
FIT_LEVELS = {"strong", "possible", "weak", "unknown"}
FIT_LABELS = {"strong": "强匹配", "possible": "可争取", "weak": "弱匹配", "unknown": "待判断"}
INTERVIEW_STATUSES = {"scheduled", "completed", "passed", "failed", "cancelled"}
INTERVIEW_STATUS_LABELS = {
    "scheduled": "待进行",
    "completed": "待复盘",
    "passed": "已通过",
    "failed": "未通过",
    "cancelled": "已取消",
}
OFFER_STATUSES = {"evaluating", "negotiating", "accepted", "declined", "expired"}
OFFER_STATUS_LABELS = {
    "evaluating": "评估中",
    "negotiating": "谈判中",
    "accepted": "已接受",
    "declined": "已拒绝",
    "expired": "已过期",
}


def empty_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "target": {"roles": [], "locations": [], "minimum_offer": "", "deadline": "", "notes": ""},
        "opportunities": [],
        "events": [],
        "interviews": [],
        "offers": [],
    }


def canonical_state(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def state_digest(state: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_state(state).encode("utf-8")).hexdigest()


def load_state(workspace: Path) -> dict[str, Any]:
    return json.loads((workspace / STATE_NAME).read_text(encoding="utf-8"))


def _valid_iso_date(value: str) -> bool:
    if not value:
        return True
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _valid_web_url(value: str) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _validate_unique_ids(errors: list[str], items: Any, name: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"{name} 必须是列表")
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{name}[{index}] 必须是对象")
            continue
        item_id = item.get("id", "")
        if not isinstance(item_id, str) or not item_id.strip():
            errors.append(f"{name}[{index}].id 不能为空")
        elif item_id in mapped:
            errors.append(f"{name} 存在重复 ID: {item_id}")
        else:
            mapped[item_id] = item
    return mapped


def validate_state(state: dict[str, Any], workspace: Path) -> list[str]:
    errors: list[str] = []
    if state.get("schema_version") != 1:
        errors.append("career-state.json 的 schema_version 必须为 1")
    target = state.get("target", {})
    if not isinstance(target, dict):
        errors.append("target 必须是对象")
        target = {}
    for key in ("roles", "locations"):
        values = target.get(key, [])
        if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
            errors.append(f"target.{key} 必须是非空字符串列表")
    if not _valid_iso_date(target.get("deadline", "")):
        errors.append("target.deadline 必须使用 YYYY-MM-DD")

    opportunities = _validate_unique_ids(errors, state.get("opportunities", []), "opportunities")
    for opportunity_id, item in opportunities.items():
        prefix = f"opportunities.{opportunity_id}"
        if not item.get("company", "").strip() or not item.get("role", "").strip():
            errors.append(f"{prefix} 必须包含公司和岗位")
        if item.get("status") not in OPPORTUNITY_STATUSES:
            errors.append(f"{prefix}.status 无效")
        if item.get("priority") not in PRIORITIES:
            errors.append(f"{prefix}.priority 无效")
        if item.get("fit") not in FIT_LEVELS:
            errors.append(f"{prefix}.fit 无效")
        if not _valid_web_url(item.get("url", "")):
            errors.append(f"{prefix}.url 必须是 HTTP(S) 地址")
        for key in ("created_at", "updated_at"):
            if not item.get(key) or not _valid_iso_date(item[key]):
                errors.append(f"{prefix}.{key} 必须使用 YYYY-MM-DD")
        if not _valid_iso_date(item.get("next_action_date", "")):
            errors.append(f"{prefix}.next_action_date 必须使用 YYYY-MM-DD")
        request_path = item.get("application_request", "")
        if request_path:
            relative = Path(request_path)
            if relative.is_absolute() or ".." in relative.parts or not (workspace / relative).is_file():
                errors.append(f"{prefix}.application_request 必须指向工作区内已有文件")

    events = _validate_unique_ids(errors, state.get("events", []), "events")
    for event_id, item in events.items():
        prefix = f"events.{event_id}"
        if item.get("opportunity_id") not in opportunities:
            errors.append(f"{prefix} 引用了不存在的岗位")
        if item.get("type") not in EVENT_TYPES:
            errors.append(f"{prefix}.type 无效")
        if not _valid_iso_date(item.get("date", "")) or not item.get("date"):
            errors.append(f"{prefix}.date 必须使用 YYYY-MM-DD")

    interviews = _validate_unique_ids(errors, state.get("interviews", []), "interviews")
    for interview_id, item in interviews.items():
        prefix = f"interviews.{interview_id}"
        if item.get("opportunity_id") not in opportunities:
            errors.append(f"{prefix} 引用了不存在的岗位")
        if item.get("status") not in INTERVIEW_STATUSES:
            errors.append(f"{prefix}.status 无效")
        if not item.get("round", "").strip():
            errors.append(f"{prefix}.round 不能为空")
        if not _valid_iso_date(item.get("date", "")) or not item.get("date"):
            errors.append(f"{prefix}.date 必须使用 YYYY-MM-DD")

    offers = _validate_unique_ids(errors, state.get("offers", []), "offers")
    for offer_id, item in offers.items():
        prefix = f"offers.{offer_id}"
        if item.get("opportunity_id") not in opportunities:
            errors.append(f"{prefix} 引用了不存在的岗位")
        if item.get("status") not in OFFER_STATUSES:
            errors.append(f"{prefix}.status 无效")
        if not _valid_iso_date(item.get("deadline", "")):
            errors.append(f"{prefix}.deadline 必须使用 YYYY-MM-DD")
    return errors


def save_state(workspace: Path, state: dict[str, Any]) -> Path:
    errors = validate_state(state, workspace)
    if errors:
        raise ValueError("求职状态无效：\n- " + "\n- ".join(errors))
    target = workspace / STATE_NAME
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=workspace, delete=False) as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, target)
    return target


def opportunity_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in state["opportunities"]}


def event_id(state: dict[str, Any], event_date: str) -> str:
    prefix = f"evt-{event_date.replace('-', '')}-"
    used = {item["id"] for item in state["events"]}
    index = 1
    while f"{prefix}{index:02d}" in used:
        index += 1
    return f"{prefix}{index:02d}"


def apply_event_status(opportunity: dict[str, Any], event_type: str) -> None:
    transitions = {
        "sourced": "researching",
        "materials_ready": "preparing",
        "referred": "referred",
        "applied": "applied",
        "response": "screening",
        "interview_scheduled": "interviewing",
        "interview_passed": "interviewing",
        "interview_failed": "rejected",
        "offer": "offer",
        "rejected": "rejected",
        "withdrawn": "withdrawn",
    }
    if event_type in transitions:
        opportunity["status"] = transitions[event_type]


def calculate_funnel(state: dict[str, Any]) -> list[dict[str, Any]]:
    events_by_job: dict[str, set[str]] = {}
    for event in state["events"]:
        events_by_job.setdefault(event["opportunity_id"], set()).add(event["type"])
    interviews_by_job = {item["opportunity_id"] for item in state["interviews"]}
    offers_by_job = {item["opportunity_id"] for item in state["offers"]}
    reached = {"opportunities": set(), "applied": set(), "responses": set(), "interviews": set(), "offers": set()}
    applied_statuses = {"applied", "screening", "interviewing", "offer"}
    response_statuses = {"screening", "interviewing", "offer"}
    for item in state["opportunities"]:
        job_id = item["id"]
        if item["status"] != "withdrawn":
            reached["opportunities"].add(job_id)
        types = events_by_job.get(job_id, set())
        if item["status"] in applied_statuses or "applied" in types:
            reached["applied"].add(job_id)
        if item["status"] in response_statuses or types & {"response", "interview_scheduled", "interview_passed", "offer"}:
            reached["responses"].add(job_id)
        if job_id in interviews_by_job or item["status"] in {"interviewing", "offer"} or types & {"interview_scheduled", "interview_passed", "interview_failed"}:
            reached["interviews"].add(job_id)
        if job_id in offers_by_job or item["status"] == "offer" or "offer" in types:
            reached["offers"].add(job_id)
    stages = (
        ("opportunities", "目标岗位"),
        ("applied", "已投递"),
        ("responses", "有回复"),
        ("interviews", "进面试"),
        ("offers", "Offer"),
    )
    result: list[dict[str, Any]] = []
    previous = 0
    for index, (key, label) in enumerate(stages):
        count = len(reached[key])
        conversion = None if index == 0 or previous == 0 else round(count * 100 / previous)
        result.append({"key": key, "label": label, "count": count, "conversion": conversion})
        previous = count
    return result


def _parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


def next_actions(state: dict[str, Any], today: date | None = None) -> list[dict[str, str]]:
    today = today or date.today()
    jobs = opportunity_map(state)
    actions: list[tuple[int, int, date, dict[str, str]]] = []
    priority_rank = {"high": 0, "medium": 1, "low": 2}

    def add(rank: int, job: dict[str, Any], action: str, due: date | None, reason: str) -> None:
        actions.append(
            (
                rank,
                priority_rank[job["priority"]],
                due or date.max,
                {
                    "opportunity_id": job["id"],
                    "company": job["company"],
                    "role": job["role"],
                    "action": action,
                    "due": due.isoformat() if due else "",
                    "reason": reason,
                },
            )
        )

    for offer in state["offers"]:
        if offer["status"] not in {"evaluating", "negotiating"}:
            continue
        job = jobs[offer["opportunity_id"]]
        due = _parse_date(offer.get("deadline", ""))
        add(0, job, "完成 Offer 比较与谈判决策", due, "Offer 已进入决策窗口")

    for interview in state["interviews"]:
        job = jobs[interview["opportunity_id"]]
        interview_date = _parse_date(interview["date"])
        if interview["status"] == "scheduled" and interview_date and interview_date >= today:
            add(1, job, f"准备{interview['round']}面试", interview_date, interview.get("focus") or "面试时间已确定")
        elif interview["status"] in {"scheduled", "completed"} and interview_date and interview_date < today:
            add(1, job, f"记录{interview['round']}结果并完成复盘", today, "面试已结束但结果或复盘未闭环")

    interviewed = {item["opportunity_id"] for item in state["interviews"] if item["status"] == "scheduled"}
    for job in state["opportunities"]:
        status = job["status"]
        explicit_due = _parse_date(job.get("next_action_date", ""))
        if job.get("next_action", "").strip():
            add(2, job, job["next_action"], explicit_due, "岗位已设置下一步")
        elif status == "researching":
            add(3, job, "完成 JD 适配判断并决定是否投入", today, "岗位尚未进入准备")
        elif status == "preparing":
            add(2, job, "完成定向材料并投递", today, "材料准备中")
        elif status == "referred":
            add(3, job, "确认内推进度", today + timedelta(days=2), "已内推但尚未记录投递")
        elif status == "applied":
            applied_dates = [
                _parse_date(event["date"])
                for event in state["events"]
                if event["opportunity_id"] == job["id"] and event["type"] == "applied"
            ]
            last_applied = max((value for value in applied_dates if value), default=_parse_date(job["updated_at"]))
            follow_up = (last_applied or today) + timedelta(days=3)
            add(4, job, "发送一次招聘跟进", follow_up, "投递后尚未收到回复")
        elif status == "screening":
            add(2, job, "准备招聘筛选沟通", today, "已收到回复")
        elif status == "interviewing" and job["id"] not in interviewed:
            add(2, job, "确认下一轮安排或回写面试结果", today, "岗位处于面试阶段但没有待进行场次")

    if not state["opportunities"]:
        return [{"opportunity_id": "", "company": "", "role": "", "action": "添加 3-5 个目标岗位", "due": "", "reason": "当前还没有可推进的岗位"}]
    actions.sort(key=lambda item: (item[0], item[2] > today, item[2], item[1]))
    deduplicated: list[dict[str, str]] = []
    seen: set[str] = set()
    for _, _, _, action in actions:
        key = action["opportunity_id"] or action["action"]
        if key not in seen:
            deduplicated.append(action)
            seen.add(key)
    return deduplicated[:7]


def markdown_cell(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", "<br>")


def render_markdown(state: dict[str, Any], today: date | None = None) -> str:
    jobs = opportunity_map(state)
    funnel = calculate_funnel(state)
    actions = next_actions(state, today)
    target = state["target"]
    lines = [
        "# Offer 求职看板",
        "",
        "> 本文件由 `career-state.json` 自动生成。请让 Agent 使用 `career_ops.py` 更新，不要手工维护两份状态。",
        "",
        "## 目标 Offer",
        "",
        f"- 目标岗位：{markdown_cell('、'.join(target['roles']) or '待确定')}",
        f"- 目标城市：{markdown_cell('、'.join(target['locations']) or '不限/待确定')}",
        f"- Offer 底线：{markdown_cell(target['minimum_offer'] or '待确定')}",
        f"- 目标日期：{markdown_cell(target['deadline'] or '待确定')}",
        f"- 备注：{markdown_cell(target['notes'] or '无')}",
        "",
        "## 下一最佳动作",
        "",
        "| 公司 | 岗位 | 动作 | 截止 | 原因 |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines.extend(
        f"| {markdown_cell(item['company'])} | {markdown_cell(item['role'])} | {markdown_cell(item['action'])} | {markdown_cell(item['due'])} | {markdown_cell(item['reason'])} |"
        for item in actions
    )
    lines.extend(("", "## 转化漏斗", "", "| 阶段 | 数量 | 上一阶段转化 |", "| --- | ---: | ---: |"))
    lines.extend(
        f"| {item['label']} | {item['count']} | {'-' if item['conversion'] is None else str(item['conversion']) + '%'} |"
        for item in funnel
    )
    lines.extend(
        (
            "",
            "## 岗位",
            "",
            "| ID | 公司 | 岗位 | 优先级 | 匹配 | 状态 | 下一步 | 日期 | 渠道 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        )
    )
    lines.extend(
        f"| {markdown_cell(item['id'])} | {markdown_cell(item['company'])} | {markdown_cell(item['role'])} | {PRIORITY_LABELS[item['priority']]} | {FIT_LABELS[item['fit']]} | {STATUS_LABELS[item['status']]} | {markdown_cell(item.get('next_action'))} | {markdown_cell(item.get('next_action_date'))} | {markdown_cell(item.get('source'))} |"
        for item in state["opportunities"]
    )
    lines.extend(
        (
            "",
            "## 面试",
            "",
            "| ID | 公司 | 岗位 | 轮次 | 日期 | 状态 | 重点 | 结果 | 复盘 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        )
    )
    lines.extend(
        f"| {markdown_cell(item['id'])} | {markdown_cell(jobs[item['opportunity_id']]['company'])} | {markdown_cell(jobs[item['opportunity_id']]['role'])} | {markdown_cell(item['round'])} | {item['date']} | {INTERVIEW_STATUS_LABELS[item['status']]} | {markdown_cell(item.get('focus'))} | {markdown_cell(item.get('result'))} | {markdown_cell(item.get('review_path'))} |"
        for item in state["interviews"]
    )
    lines.extend(
        (
            "",
            "## Offer",
            "",
            "| ID | 公司 | 岗位/职级 | 现金 | 股权 | 奖金 | 状态 | 截止日期 | 条件与风险 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        )
    )
    lines.extend(
        f"| {markdown_cell(item['id'])} | {markdown_cell(jobs[item['opportunity_id']]['company'])} | {markdown_cell(jobs[item['opportunity_id']]['role'] + (' / ' + item['level'] if item.get('level') else ''))} | {markdown_cell(item.get('cash'))} | {markdown_cell(item.get('equity'))} | {markdown_cell(item.get('bonus'))} | {OFFER_STATUS_LABELS[item['status']]} | {markdown_cell(item.get('deadline'))} | {markdown_cell('；'.join([item.get('conditions', ''), *item.get('risks', [])]).strip('；'))} |"
        for item in state["offers"]
    )
    lines.extend(
        (
            "",
            "## 时间线",
            "",
            "| 日期 | 公司 | 岗位 | 事件 | 记录 |",
            "| --- | --- | --- | --- | --- |",
        )
    )
    for item in sorted(state["events"], key=lambda value: (value["date"], value["id"]), reverse=True):
        job = jobs[item["opportunity_id"]]
        lines.append(
            f"| {item['date']} | {markdown_cell(job['company'])} | {markdown_cell(job['role'])} | {EVENT_LABELS[item['type']]} | {markdown_cell(item.get('note'))} |"
        )
    return "\n".join(lines) + "\n"


def write_markdown(workspace: Path, state: dict[str, Any], today: date | None = None) -> Path:
    path = workspace / "application-dashboard.md"
    path.write_text(render_markdown(state, today), encoding="utf-8")
    return path
