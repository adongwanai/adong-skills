#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from career_state import (
    EVENT_TYPES,
    FIT_LEVELS,
    INTERVIEW_STATUSES,
    OFFER_STATUSES,
    OPPORTUNITY_STATUSES,
    PRIORITIES,
    apply_event_status,
    event_id,
    load_state,
    opportunity_map,
    save_state,
    write_markdown,
)
from common import workspace_path


def _csv_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _today(value: str | None = None) -> str:
    return value or date.today().isoformat()


def _job(state: dict, job_id: str) -> dict:
    job = opportunity_map(state).get(job_id)
    if not job:
        raise ValueError(f"岗位不存在: {job_id}")
    return job


def add_job(state: dict, args: argparse.Namespace) -> None:
    if args.id in opportunity_map(state):
        raise ValueError(f"岗位 ID 已存在: {args.id}")
    day = _today(args.date)
    state["opportunities"].append(
        {
            "id": args.id,
            "company": args.company,
            "role": args.role,
            "source": args.source,
            "url": args.url,
            "location": args.location,
            "priority": args.priority,
            "fit": args.fit,
            "fit_reasons": _csv_values(args.fit_reasons),
            "gaps": _csv_values(args.gaps),
            "status": args.status,
            "created_at": day,
            "updated_at": day,
            "next_action": args.next_action,
            "next_action_date": args.next_action_date,
            "application_request": args.application_request,
        }
    )
    state["events"].append(
        {"id": event_id(state, day), "opportunity_id": args.id, "type": "sourced", "date": day, "note": args.note}
    )


def update_job(state: dict, args: argparse.Namespace) -> None:
    job = _job(state, args.id)
    for key in (
        "company",
        "role",
        "source",
        "url",
        "location",
        "priority",
        "fit",
        "status",
        "next_action",
        "next_action_date",
        "application_request",
    ):
        value = getattr(args, key)
        if value is not None:
            job[key] = value
    for key in ("fit_reasons", "gaps"):
        value = getattr(args, key)
        if value is not None:
            job[key] = _csv_values(value)
    job["updated_at"] = _today(args.date)


def record_event(state: dict, args: argparse.Namespace) -> None:
    job = _job(state, args.job_id)
    day = _today(args.date)
    state["events"].append(
        {"id": event_id(state, day), "opportunity_id": args.job_id, "type": args.type, "date": day, "note": args.note}
    )
    apply_event_status(job, args.type)
    job["updated_at"] = day
    if args.type in {"applied", "response", "interview_scheduled", "offer", "rejected", "withdrawn"}:
        job["next_action"] = ""
        job["next_action_date"] = ""


def add_interview(state: dict, args: argparse.Namespace) -> None:
    _job(state, args.job_id)
    if any(item["id"] == args.id for item in state["interviews"]):
        raise ValueError(f"面试 ID 已存在: {args.id}")
    state["interviews"].append(
        {
            "id": args.id,
            "opportunity_id": args.job_id,
            "round": args.round,
            "date": args.date,
            "status": args.status,
            "focus": args.focus,
            "result": args.result,
            "review_path": args.review_path,
        }
    )
    event_type = "interview_scheduled"
    if args.status == "passed":
        event_type = "interview_passed"
    elif args.status == "failed":
        event_type = "interview_failed"
    record_event(
        state,
        argparse.Namespace(job_id=args.job_id, date=args.date, type=event_type, note=args.result or args.focus),
    )


def update_interview(state: dict, args: argparse.Namespace) -> None:
    interview = next((item for item in state["interviews"] if item["id"] == args.id), None)
    if not interview:
        raise ValueError(f"面试不存在: {args.id}")
    previous_status = interview["status"]
    for key in ("round", "date", "status", "focus", "result", "review_path"):
        value = getattr(args, key)
        if value is not None:
            interview[key] = value
    if args.status in {"passed", "failed"} and args.status != previous_status:
        event_type = "interview_passed" if args.status == "passed" else "interview_failed"
        record_event(
            state,
            argparse.Namespace(
                job_id=interview["opportunity_id"],
                date=interview["date"],
                type=event_type,
                note=interview.get("result", ""),
            ),
        )


def add_offer(state: dict, args: argparse.Namespace) -> None:
    _job(state, args.job_id)
    if any(item["id"] == args.id for item in state["offers"]):
        raise ValueError(f"Offer ID 已存在: {args.id}")
    state["offers"].append(
        {
            "id": args.id,
            "opportunity_id": args.job_id,
            "level": args.level,
            "cash": args.cash,
            "equity": args.equity,
            "bonus": args.bonus,
            "conditions": args.conditions,
            "deadline": args.deadline,
            "status": args.status,
            "risks": _csv_values(args.risks),
        }
    )
    record_event(
        state,
        argparse.Namespace(job_id=args.job_id, date=_today(args.date), type="offer", note=args.conditions),
    )


def update_offer(state: dict, args: argparse.Namespace) -> None:
    offer = next((item for item in state["offers"] if item["id"] == args.id), None)
    if not offer:
        raise ValueError(f"Offer 不存在: {args.id}")
    for key in ("level", "cash", "equity", "bonus", "conditions", "deadline", "status"):
        value = getattr(args, key)
        if value is not None:
            offer[key] = value
    if args.risks is not None:
        offer["risks"] = _csv_values(args.risks)


def set_target(state: dict, args: argparse.Namespace) -> None:
    target = state["target"]
    for key in ("minimum_offer", "deadline", "notes"):
        value = getattr(args, key)
        if value is not None:
            target[key] = value
    if args.roles is not None:
        target["roles"] = _csv_values(args.roles)
    if args.locations is not None:
        target["locations"] = _csv_values(args.locations)


def _add_common_job_args(parser: argparse.ArgumentParser, *, optional: bool = False) -> None:
    kwargs = {"default": None} if optional else {}
    parser.add_argument("--company", required=not optional, **kwargs)
    parser.add_argument("--role", required=not optional, **kwargs)
    parser.add_argument("--source", default=None if optional else "")
    parser.add_argument("--url", default=None if optional else "")
    parser.add_argument("--location", default=None if optional else "")
    parser.add_argument("--priority", choices=sorted(PRIORITIES), default=None if optional else "medium")
    parser.add_argument("--fit", choices=sorted(FIT_LEVELS), default=None if optional else "unknown")
    parser.add_argument("--fit-reasons", default=None if optional else "")
    parser.add_argument("--gaps", default=None if optional else "")
    parser.add_argument("--status", choices=sorted(OPPORTUNITY_STATUSES), default=None if optional else "researching")
    parser.add_argument("--next-action", default=None if optional else "")
    parser.add_argument("--next-action-date", default=None if optional else "")
    parser.add_argument("--application-request", default=None if optional else "")
    parser.add_argument("--date", default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="更新 Offer 求职漏斗，并同步生成 Markdown 与网页驾驶舱。")
    parser.add_argument("workspace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    target = subparsers.add_parser("set-target", help="设置目标 Offer 边界。")
    target.add_argument("--roles")
    target.add_argument("--locations")
    target.add_argument("--minimum-offer")
    target.add_argument("--deadline")
    target.add_argument("--notes")

    add = subparsers.add_parser("add-job", help="新增目标岗位。")
    add.add_argument("--id", required=True)
    _add_common_job_args(add)
    add.add_argument("--note", default="")

    update = subparsers.add_parser("update-job", help="更新岗位判断或下一步。")
    update.add_argument("--id", required=True)
    _add_common_job_args(update, optional=True)

    event = subparsers.add_parser("record-event", help="记录投递、回复或结果。")
    event.add_argument("--job-id", required=True)
    event.add_argument("--type", required=True, choices=sorted(EVENT_TYPES))
    event.add_argument("--date")
    event.add_argument("--note", default="")

    interview = subparsers.add_parser("add-interview", help="记录面试安排或结果。")
    interview.add_argument("--id", required=True)
    interview.add_argument("--job-id", required=True)
    interview.add_argument("--round", required=True)
    interview.add_argument("--date", required=True)
    interview.add_argument("--status", choices=sorted(INTERVIEW_STATUSES), default="scheduled")
    interview.add_argument("--focus", default="")
    interview.add_argument("--result", default="")
    interview.add_argument("--review-path", default="")

    interview_update = subparsers.add_parser("update-interview", help="更新面试结果和复盘。")
    interview_update.add_argument("--id", required=True)
    interview_update.add_argument("--round")
    interview_update.add_argument("--date")
    interview_update.add_argument("--status", choices=sorted(INTERVIEW_STATUSES))
    interview_update.add_argument("--focus")
    interview_update.add_argument("--result")
    interview_update.add_argument("--review-path")

    offer = subparsers.add_parser("add-offer", help="记录 Offer。")
    offer.add_argument("--id", required=True)
    offer.add_argument("--job-id", required=True)
    offer.add_argument("--level", default="")
    offer.add_argument("--cash", default="")
    offer.add_argument("--equity", default="")
    offer.add_argument("--bonus", default="")
    offer.add_argument("--conditions", default="")
    offer.add_argument("--deadline", default="")
    offer.add_argument("--status", choices=sorted(OFFER_STATUSES), default="evaluating")
    offer.add_argument("--risks", default="")
    offer.add_argument("--date")

    offer_update = subparsers.add_parser("update-offer", help="更新 Offer 条件或决策状态。")
    offer_update.add_argument("--id", required=True)
    offer_update.add_argument("--level")
    offer_update.add_argument("--cash")
    offer_update.add_argument("--equity")
    offer_update.add_argument("--bonus")
    offer_update.add_argument("--conditions")
    offer_update.add_argument("--deadline")
    offer_update.add_argument("--status", choices=sorted(OFFER_STATUSES))
    offer_update.add_argument("--risks")

    subparsers.add_parser("render", help="从当前状态重建 Markdown 与网页。")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        workspace = workspace_path(args.workspace)
        state = load_state(workspace)
        if args.command == "set-target":
            set_target(state, args)
        elif args.command == "add-job":
            add_job(state, args)
        elif args.command == "update-job":
            update_job(state, args)
        elif args.command == "record-event":
            record_event(state, args)
        elif args.command == "add-interview":
            add_interview(state, args)
        elif args.command == "update-interview":
            update_interview(state, args)
        elif args.command == "add-offer":
            add_offer(state, args)
        elif args.command == "update-offer":
            update_offer(state, args)
        if args.command != "render":
            save_state(workspace, state)
        write_markdown(workspace, state)
        from render_career_dashboard import render_dashboard

        dashboard = render_dashboard(workspace, state)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"求职状态更新失败：\n{error}") from None
    print(workspace / "application-dashboard.md")
    print(dashboard)


if __name__ == "__main__":
    main()
