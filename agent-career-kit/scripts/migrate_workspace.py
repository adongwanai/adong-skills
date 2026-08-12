#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import date
from pathlib import Path

from career_state import empty_state, event_id, load_state, save_state, write_markdown
from common import CAREER_STAGES, SKILL_DIR, workspace_path
from render_career_dashboard import render_dashboard


def migrate(workspace: Path, career_stage: str | None = None) -> list[Path]:
    workspace = workspace.resolve()
    changed: list[Path] = []
    template = SKILL_DIR / "assets" / "workspace-template"
    for filename in ("intake.md",):
        target = workspace / filename
        if not target.exists():
            shutil.copy2(template / filename, target)
            changed.append(target)

    state_path = workspace / "career-state.json"
    if state_path.is_file():
        state = load_state(workspace)
    else:
        state = empty_state()
    application_dir = workspace / "outputs" / "application"
    known_jobs = {item["id"] for item in state["opportunities"]}
    known_interviews = {item["id"] for item in state["interviews"]}
    known_offers = {item["id"] for item in state["offers"]}
    job_keys = {(item["company"], item["role"]): item["id"] for item in state["opportunities"]}
    status_map = {
        "researching": "researching",
        "preparing": "preparing",
        "referred": "referred",
        "applied": "applied",
        "screening": "screening",
        "interviewing": "interviewing",
        "offer": "offer",
        "rejected": "rejected",
        "paused": "paused",
        "withdrawn": "withdrawn",
    }

    def ensure_job(company: str, role: str, day: str, preferred_id: str) -> str:
        key = (company or "未命名公司", role or "未命名岗位")
        if key in job_keys:
            return job_keys[key]
        job_id = preferred_id
        suffix = 1
        while job_id in known_jobs:
            suffix += 1
            job_id = f"{preferred_id}-{suffix}"
        state["opportunities"].append(
            {
                "id": job_id,
                "company": key[0],
                "role": key[1],
                "source": "旧版记录",
                "url": "",
                "location": "",
                "priority": "medium",
                "fit": "unknown",
                "fit_reasons": [],
                "gaps": [],
                "status": "researching",
                "created_at": day,
                "updated_at": day,
                "next_action": "",
                "next_action_date": "",
                "application_request": "",
            }
        )
        known_jobs.add(job_id)
        job_keys[key] = job_id
        return job_id

    tracker = application_dir / "application-tracker.csv"
    if tracker.is_file():
        with tracker.open(encoding="utf-8", newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle), start=1):
                day = row.get("date") or date.today().isoformat()
                preferred = row.get("application_id") or f"legacy-job-{index:03d}"
                job_id = ensure_job(row.get("company", ""), row.get("role", ""), day, preferred)
                job = next(item for item in state["opportunities"] if item["id"] == job_id)
                job.update(
                    {
                        "source": row.get("source", "") or job["source"],
                        "status": status_map.get(row.get("status", ""), job["status"]),
                        "updated_at": day,
                        "next_action": row.get("next_action", ""),
                    }
                )
                note = row.get("notes") or "旧版投递记录迁移"
                if not any(item["opportunity_id"] == job_id and item.get("note") == note for item in state["events"]):
                    state["events"].append(
                        {"id": event_id(state, day), "opportunity_id": job_id, "type": "note", "date": day, "note": note}
                    )

    interviews = application_dir / "interview-schedule.csv"
    if interviews.is_file():
        with interviews.open(encoding="utf-8", newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle), start=1):
                interview_id = row.get("interview_id") or f"legacy-interview-{index:03d}"
                if interview_id in known_interviews:
                    continue
                day = row.get("date") or date.today().isoformat()
                job_id = ensure_job(row.get("company", ""), row.get("role", ""), day, f"legacy-job-interview-{index:03d}")
                result = row.get("result", "")
                status = "passed" if result.lower() in {"pass", "passed", "通过"} else "failed" if result.lower() in {"fail", "failed", "未通过"} else "completed" if result else "scheduled"
                state["interviews"].append(
                    {"id": interview_id, "opportunity_id": job_id, "round": row.get("round", "面试"), "date": day, "status": status, "focus": row.get("focus", ""), "result": result, "review_path": row.get("review_path", "")}
                )
                known_interviews.add(interview_id)

    offers = application_dir / "offer-comparison.csv"
    if offers.is_file():
        with offers.open(encoding="utf-8", newline="") as handle:
            for index, row in enumerate(csv.DictReader(handle), start=1):
                offer_id = row.get("offer_id") or f"legacy-offer-{index:03d}"
                if offer_id in known_offers:
                    continue
                day = date.today().isoformat()
                job_id = ensure_job(row.get("company", ""), row.get("role", ""), day, f"legacy-job-offer-{index:03d}")
                state["offers"].append(
                    {"id": offer_id, "opportunity_id": job_id, "level": row.get("level", ""), "cash": row.get("cash", ""), "equity": row.get("equity", ""), "bonus": row.get("bonus", ""), "conditions": row.get("conditions", ""), "deadline": row.get("deadline", ""), "status": "evaluating", "risks": [row["risk_notes"]] if row.get("risk_notes") else []}
                )
                job = next(item for item in state["opportunities"] if item["id"] == job_id)
                job["status"] = "offer"
                known_offers.add(offer_id)

    previous_state = state_path.read_text(encoding="utf-8") if state_path.is_file() else ""
    save_state(workspace, state)
    if state_path.read_text(encoding="utf-8") != previous_state:
        changed.append(state_path.resolve())

    dashboard = write_markdown(workspace, state)
    dashboard_html = render_dashboard(workspace, state)
    changed.extend(path.resolve() for path in (dashboard, dashboard_html))

    profile_path = workspace / "candidate-profile.json"
    if career_stage and profile_path.is_file():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        if profile.get("candidate", {}).get("career_stage") != career_stage:
            profile.setdefault("candidate", {})["career_stage"] = career_stage
            profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed.append(profile_path)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="将旧版工作区升级到中文冷启动和 Markdown 求职看板。")
    parser.add_argument("workspace")
    parser.add_argument("--career-stage", choices=sorted(CAREER_STAGES))
    args = parser.parse_args()
    try:
        changed = migrate(workspace_path(args.workspace), args.career_stage)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"工作区迁移失败：\n{error}") from None
    if changed:
        print("已更新：")
        print("\n".join(f"- {path}" for path in changed))
    else:
        print("工作区已经是当前版本，无需迁移。")
    if not args.career_stage:
        print("下一步：确认候选阶段，并用 --career-stage campus|experienced|senior 再运行一次。")


if __name__ == "__main__":
    main()
