#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from career_state import apply_event_status, event_id, load_state, opportunity_map, save_state, write_markdown
from common import VIEW_NAMES, require_valid_profile, validate_application_request, workspace_path


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def render_application_packet(request: dict, profile: dict) -> str:
    status = "已确认，可生成最终投递稿" if request["approval"]["status"] == "approved" else "草稿，等待用户确认"
    requirements = "\n".join(
        "| "
        + " | ".join(
            (
                markdown_cell(item["id"]),
                markdown_cell(item["requirement"]),
                markdown_cell(", ".join(item.get("claim_ids", []))),
                markdown_cell(item.get("evidence_strength", "unknown")),
                markdown_cell(item.get("gap", "")),
            )
        )
        + " |"
        for item in request["requirements"]
    )
    overrides = request.get("bullet_overrides", {})
    rewrite_rows = "\n".join(
        f"| {markdown_cell(bullet_id)} | {markdown_cell(override['source_text'])} | {markdown_cell(override['text'])} |"
        for bullet_id, override in overrides.items()
    )
    if not rewrite_rows:
        rewrite_rows = "| - | 无单次投递改写 | 使用母版原文 |"
    approval = request["approval"]
    approval_text = (
        f"- 确认时间：{approval['approved_at']}\n- 确认记录：{approval['record']}"
        if approval["status"] == "approved"
        else "尚未确认。当前只能生成审阅草稿。"
    )
    risks = "\n".join(f"- {risk}" for risk in request["risks"])
    selected = "\n".join(
        f"- `{claim_id}`：{profile_claim['name']}"
        for claim_id in request["claim_ids"]
        for profile_claim in profile["claims"]
        if profile_claim["id"] == claim_id
    )
    return f"""# {request['company']} · {request['role']} 投递包

## 当前状态

- 状态：{status}
- 母版方向：`{request['source_view']}`
- JD：`{request['jd_path']}`
- JD SHA256：`{request['jd_sha256']}`

## JD 摘要

{request['jd_summary']}

## 要求与证据映射

| 要求 ID | JD 原意 | Claim IDs | 证据强度 | 缺口 |
| --- | --- | --- | --- | --- |
{requirements}

## 本次选材

{selected}

## 选材与排序理由

{request['selection_rationale']}

## 改写提案

| Bullet ID | 母版原文 | 本次投递稿 |
| --- | --- | --- |
{rewrite_rows}

## 投递风险

{risks}

## 用户确认

{approval_text}
"""


def initialize_application(
    workspace: Path,
    jd_path: Path,
    slug: str,
    company: str,
    role: str,
    source_view: str,
    job_id: str = "",
) -> Path:
    workspace = workspace.resolve()
    profile = require_valid_profile(workspace)
    if source_view not in VIEW_NAMES:
        raise ValueError(f"unknown resume view: {source_view}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ValueError("slug 只能使用小写字母、数字和连字符")
    if not company.strip() or not role.strip():
        raise ValueError("公司和岗位不能为空")
    absolute_jd = jd_path.expanduser().resolve()
    try:
        relative_jd = absolute_jd.relative_to(workspace)
    except ValueError:
        raise ValueError("JD 必须放在候选人工作区内") from None
    if not absolute_jd.is_file():
        raise ValueError(f"JD 文件不存在: {absolute_jd}")

    view = profile["resume_views"][source_view]
    output_dir = workspace / "outputs" / "applications" / slug
    if output_dir.exists():
        raise ValueError(f"投递包已存在: {output_dir}")
    state = None
    job = None
    if job_id:
        state = load_state(workspace)
        job = opportunity_map(state).get(job_id)
        if not job:
            raise ValueError(f"岗位不存在: {job_id}")
    request = {
        "schema_version": 1,
        "slug": slug,
        "company": company,
        "role": role,
        "jd_path": relative_jd.as_posix(),
        "jd_sha256": hashlib.sha256(absolute_jd.read_bytes()).hexdigest(),
        "source_view": source_view,
        "headline": role,
        "summary": view.get("summary", ""),
        "summary_claim_ids": view.get("summary_claim_ids", []),
        "claim_ids": view["claim_ids"],
        "bullet_ids_by_claim": view["bullet_ids_by_claim"],
        "bullet_overrides": {},
        "skills": view.get("skills", []),
        "jd_summary": "待填写：从原始 JD 提取职责、硬要求和优先项。",
        "selection_rationale": "待填写：说明本次经历选择与排序理由。",
        "risks": ["待填写：记录未覆盖要求、职级偏差或需面试解释的限制。"],
        "requirements": [
            {"id": "req-01", "requirement": "请从 JD 提取第一项核心要求", "claim_ids": [], "gap": "待映射"}
        ],
        "approval": {"status": "draft", "approved_at": "", "record": ""},
    }
    errors = validate_application_request(request, profile, workspace)
    if errors:
        raise ValueError("\n- ".join(errors))
    output_dir.mkdir(parents=True)
    (output_dir / "application-request.json").write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "application-packet.md").write_text(render_application_packet(request, profile), encoding="utf-8")
    if state is not None and job is not None:
        job["application_request"] = (output_dir / "application-request.json").relative_to(workspace).as_posix()
        job["next_action"] = "确认定向材料并完成投递"
        job["next_action_date"] = ""
        apply_event_status(job, "materials_ready")
        job["updated_at"] = __import__("datetime").date.today().isoformat()
        state["events"].append(
            {
                "id": event_id(state, job["updated_at"]),
                "opportunity_id": job_id,
                "type": "materials_ready",
                "date": job["updated_at"],
                "note": "JD 定向投递包已创建",
            }
        )
        save_state(workspace, state)
        write_markdown(workspace, state)
        from render_career_dashboard import render_dashboard

        render_dashboard(workspace, state)
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="从一个 JD 创建可审计的投递包。")
    parser.add_argument("workspace")
    parser.add_argument("--jd", required=True, type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--view", required=True, choices=VIEW_NAMES)
    parser.add_argument("--job-id", default="", help="可选：关联 career-state.json 中的岗位 ID。")
    args = parser.parse_args()
    try:
        output = initialize_application(
            workspace_path(args.workspace), args.jd, args.slug, args.company, args.role, args.view, args.job_id
        )
    except ValueError as error:
        raise SystemExit(f"投递包初始化失败：\n{error}") from None
    print(output)
    print("下一步：完成 JD 要求映射和改写提案，交给用户一次性确认。")


if __name__ == "__main__":
    main()
