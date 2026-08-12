#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from common import workspace_path
from validate_workspace import validate_workspace


FLOW_FILES = (
    "candidate-profile.json",
    "evidence-ledger.md",
    "capability-map.md",
    "projects/memory-benchmark.md",
    "story-bank/incident-gate.md",
    "jd-bank/representative-jd.md",
    "outputs/resumes/resume-audit.md",
    "outputs/interview/coding/async_tool_executor.py",
    "outputs/interview/coding/test_async_tool_executor.py",
    "outputs/interview/coding/review.md",
    "outputs/interview/system-design/harness-platform.md",
    "outputs/interview/agent-question-pack.md",
    "outputs/interview/mock-review.md",
    "outputs/interview/companies/representative-top-ai-company/prep.md",
    "outputs/demo/project-readme.md",
    "outputs/demo/demo-script.md",
    "weaknesses.md",
    "progress.md",
)

CONTENT_CONTRACTS = {
    "outputs/interview/agent-question-pack.md": ("## Candidate Risk Profile", "## Interview Framework", "考察领域 | 相关技术点 | 考察优先级", "## Full-Loop Run Sheet", "| Total | 45 min | 60 min |", "## Interview Questions & Scoring Points"),
    "outputs/interview/mock-review.md": ("## Candidate Answer Evidence", "## Anchored Rubric", "## Review"),
    "outputs/interview/companies/representative-top-ai-company/prep.md": ("## Source And Facts", "## Hypotheses To Verify", "## Candidate Questions", "## Logistics And Open Research"),
    "outputs/interview/system-design/harness-platform.md": ("## Workload And SLO", "## Capacity And Failure Domains", "## Tradeoff"),
    "outputs/demo/project-readme.md": ("## Problem", "## Architecture", "## Evaluation", "## Demo"),
    "outputs/demo/demo-script.md": ("## 30-Second Opening", "## 2-Minute Walkthrough", "## Deep Defense"),
    "outputs/resumes/resume-audit.md": (
        "## Audit Scope",
        "## Thirty-Second Impression",
        "## Holistic Audit",
        "## Language And Terminology",
        "## Summary Audit",
        "## Experience And Project Audit",
        "## Bullet-Level Audit",
        "## Strategic Revision Blueprint",
        "### Before / After",
        "## Unresolved Evidence",
    ),
}


def validate_e2e(workspace: Path) -> list[str]:
    errors = validate_workspace(workspace, require_artifacts=True)
    for relative in FLOW_FILES:
        path = workspace / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing full-flow artifact: {relative}")
    for relative, anchors in CONTENT_CONTRACTS.items():
        path = workspace / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for anchor in anchors:
            if anchor not in text:
                errors.append(f"{relative} is missing section: {anchor}")
    profile = json.loads((workspace / "candidate-profile.json").read_text(encoding="utf-8"))
    selected_bullets = {
        bullet_id
        for view in profile["resume_views"].values()
        for bullet_ids in view["bullet_ids_by_claim"].values()
        for bullet_id in bullet_ids
    }
    audit = (workspace / "outputs" / "resumes" / "resume-audit.md").read_text(encoding="utf-8")
    for bullet_id in sorted(selected_bullets):
        marker = f"| `{bullet_id}` |"
        count = audit.count(marker)
        if count != 1:
            errors.append(f"resume audit must cover selected bullet exactly once: {bullet_id} (found {count})")
    question_pack = (workspace / "outputs" / "interview" / "agent-question-pack.md").read_text(encoding="utf-8")
    run_sheet_rows = re.findall(
        r"^\| (Self-introduction|Project deep dive|Agent fundamentals|External coding / hand-written algorithm|Candidate questions|Transitions) \| (\d+) min \| (\d+) min \|$",
        question_pack,
        flags=re.MULTILINE,
    )
    if len(run_sheet_rows) != 6:
        errors.append(f"full-loop run sheet must contain exactly 6 timed stages (found {len(run_sheet_rows)})")
    elif sum(int(row[1]) for row in run_sheet_rows) != 45 or sum(int(row[2]) for row in run_sheet_rows) != 60:
        errors.append("full-loop run sheet stage budgets must total exactly 45 and 60 minutes")
    suspicion_count = len(re.findall(r"^\d+\. \*\*疑点：", question_pack, flags=re.MULTILINE))
    if suspicion_count != 3:
        errors.append(f"interview reconnaissance must contain exactly 3 core suspicions (found {suspicion_count})")
    questions = re.split(r"(?m)(?=^\d+\. \*\*\[主问题\])", question_pack)
    questions = [block for block in questions if re.match(r"^\d+\. \*\*\[主问题\]", block)]
    if not 15 <= len(questions) <= 20:
        errors.append(f"interview reconnaissance must contain 15-20 main questions (found {len(questions)})")
    breadth_count = 0
    for index, question in enumerate(questions, start=1):
        follow_ups = len(re.findall(r"^- 追问[1-3]：", question, flags=re.MULTILINE))
        if not 2 <= follow_ups <= 3:
            errors.append(f"interview question {index} must contain 2-3 follow-ups (found {follow_ups})")
        for marker in ("- 评分要点：", "- 验证依据：", "- 评估作用："):
            if marker not in question:
                errors.append(f"interview question {index} is missing {marker}")
        if "[广度/诚实度]" in question.splitlines()[0]:
            breadth_count += 1
    if not 2 <= breadth_count <= 4:
        errors.append(f"interview reconnaissance must contain 2-4 breadth/honesty questions (found {breadth_count})")
    mock_review = (workspace / "outputs" / "interview" / "mock-review.md").read_text(encoding="utf-8")
    if "- Session format: full-loop" in mock_review:
        sections = ("## Timing Record", "## Self-Introduction", "## Project Deep Dive", "## Agent Fundamentals", "## External Coding Or Hand-Written Algorithm", "## Candidate Questions")
        for section in sections:
            if section not in mock_review:
                errors.append(f"full-loop mock review is missing section: {section}")
        if all(section in mock_review for section in sections) and [mock_review.index(section) for section in sections] != sorted(mock_review.index(section) for section in sections):
            errors.append("full-loop mock review sections are out of order")
        if mock_review.count("## External Coding Or Hand-Written Algorithm") != 1:
            errors.append("full-loop mock review must contain exactly one coding or algorithm section")
        if "- Planned duration: 45 minutes" not in mock_review and "- Planned duration: 60 minutes" not in mock_review:
            errors.append("full-loop mock review must declare a 45 or 60 minute duration")
    elif "- Session format: focus" in mock_review:
        for section in ("- Focus target:", "## Focus Depth"):
            if section not in mock_review:
                errors.append(f"focus mock review is missing section: {section}")
    else:
        errors.append("mock review must declare focus or full-loop session format")
    coding_dir = workspace / "outputs" / "interview" / "coding"
    if (coding_dir / "test_async_tool_executor.py").is_file():
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "-v", "test_async_tool_executor.py"],
            cwd=coding_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            errors.append("coding interview artifact test failed")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate a full-flow Agent Career Kit workspace.")
    parser.add_argument("workspace")
    args = parser.parse_args()
    workspace = workspace_path(args.workspace)
    errors = validate_e2e(workspace)
    if errors:
        raise SystemExit("end-to-end validation failed:\n- " + "\n- ".join(errors))
    print(f"E2E OK: {workspace}")


if __name__ == "__main__":
    main()
