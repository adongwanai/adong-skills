#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from common import (
    RENDERER_VERSION,
    SKILL_DIR,
    VIEW_NAMES,
    active_view_names,
    bullets_by_id,
    claims_by_id,
    latex_escape,
    profile_digest,
    require_valid_profile,
    workspace_path,
)


SECTION_ORDER = (
    ("科研经历", {"research", "publication"}),
    ("实习经历", {"experience"}),
    ("项目经历", {"project", "open_source", "leadership"}),
    ("个人荣誉", {"award"}),
)
LATEX_ASSETS = (SKILL_DIR / "assets" / "latex" / "resume-photo.cls",)
LEADING_LABELS = {
    "问题背景",
    "研究内容",
    "相关成果",
    "负责部分",
    "实习内容1",
    "实习内容2",
    "实习内容3",
    "项目背景",
    "核心痛点",
    "技术方案",
    "实验验证",
    "最终效果",
    "设计灵感",
    "架构设计",
    "关键技术",
    "实验结果",
    "应用场景",
    "技术栈",
}


def latex_join(values: list[str], separator: str = r" \textbullet{} ") -> str:
    return separator.join(latex_escape(value) for value in values if value)


def render_contacts(candidate: dict[str, Any]) -> str:
    contacts: list[str] = []
    for key in ("phone", "email", "university", "degree", "birthday", "location"):
        value = candidate.get(key, "").strip()
        if not value:
            continue
        if key == "email":
            escaped = latex_escape(value)
            contacts.append(rf"\ResumeUrl{{mailto:{escaped}}}{{{escaped}}}")
        else:
            contacts.append(rf"\textnormal{{{latex_escape(value)}}}")
    for link in candidate.get("links", []):
        label = latex_escape(link["label"])
        url = latex_escape(link["url"])
        contacts.append(rf"\ResumeUrl{{{url}}}{{{label}}}")
    return ",%\n  ".join(contacts)


def render_skills(skills: list[dict[str, Any]]) -> str:
    if not skills:
        return ""
    lines = [r"\section{专业技能}", r"\begin{itemize}"]
    for skill_group in skills:
        if skill_group.get("text", "").strip():
            lines.append(rf"  \item {latex_escape(skill_group['text'])}")
        else:
            group = latex_escape(skill_group["group"])
            items = latex_join(skill_group.get("items", []), ", ")
            lines.append(rf"  \item \textbf{{{group}}}: {items}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def format_date(value: str) -> str:
    if value == "Present":
        return "至今"
    return value.replace("-", ".")


def render_date_range(start: str, end: str) -> str:
    values = [format_date(value) for value in (start, end) if value]
    if not values:
        return ""
    if len(values) == 1:
        return latex_escape(values[0])
    return rf"{latex_escape(values[0])}—{latex_escape(values[1])}"


def render_itemize(bullets: list[str]) -> str:
    lines = [r"\begin{itemize}"]
    for text in bullets:
        match = re.match(r"^([^:：]{2,12})([:：])\s*(.*)$", text)
        if match and match.group(1) in LEADING_LABELS:
            label, punctuation, rest = match.groups()
            lines.append(rf"  \item \textbf{{{latex_escape(label)}}}{latex_escape(punctuation)} {latex_escape(rest)}")
        else:
            lines.append(rf"  \item {latex_escape(text)}")
    lines.append(r"\end{itemize}")
    return "\n".join(lines)


def render_resume_item(title: str, subtitle: str, date_range: str) -> str:
    subtitle_arg = rf"[\textnormal{{{latex_escape(subtitle)}}}]" if subtitle else "[]"
    date_arg = rf"[{date_range}]" if date_range else "[]"
    return rf"\ResumeItem{{{latex_escape(title)}}}{subtitle_arg}{date_arg}"


def render_detailed_claim(claim: dict[str, Any], selected_bullet_ids: list[str]) -> str:
    claim_bullets = bullets_by_id(claim)
    bullets = [claim_bullets[bullet_id]["text"] for bullet_id in selected_bullet_ids]
    date_range = render_date_range(claim.get("start", ""), claim.get("end", ""))
    lines = [render_resume_item(claim["name"], claim.get("role", ""), date_range)]
    lines.append(render_itemize(bullets))
    return "\n".join(lines)


def render_claim_sections(profile: dict[str, Any], view: dict[str, Any]) -> str:
    all_claims = claims_by_id(profile)
    selected = [all_claims[claim_id] for claim_id in view["claim_ids"]]
    sections: list[str] = []
    ordered_groups: list[tuple[str, set[str]]] = []
    for claim in selected:
        group = next(group for group in SECTION_ORDER if claim["category"] in group[1])
        if group not in ordered_groups:
            ordered_groups.append(group)
    for title, categories in ordered_groups:
        section_claims = [claim for claim in selected if claim["category"] in categories]
        if not section_claims:
            continue
        sections.append(rf"\section{{{title}}}")
        if categories == {"award"}:
            sections.append(r"\begin{itemize}")
            for claim in section_claims:
                claim_bullets = bullets_by_id(claim)
                for bullet_id in view["bullet_ids_by_claim"][claim["id"]]:
                    sections.append(rf"  \item {latex_escape(claim_bullets[bullet_id]['text'])}")
            sections.append(r"\end{itemize}")
        else:
            sections.extend(
                render_detailed_claim(claim, view["bullet_ids_by_claim"][claim["id"]])
                for claim in section_claims
            )
    return "\n".join(sections)


def render_education(education: list[dict[str, Any]]) -> str:
    selected = [
        item
        for item in education
        if item.get("status") in {"provided", "confirmed"}
    ]
    if not selected:
        return ""
    lines = [r"\section{教育背景}"]
    for item in selected:
        date_range = render_date_range(item.get("start", ""), item.get("end", ""))
        detail = item.get("detail", "") or item.get("degree", "")
        lines.append(render_resume_item(item["school"], detail, date_range))
    return "\n".join(lines)


def render_photo_setup(candidate: dict[str, Any]) -> str:
    photo = candidate.get("photo", "").strip()
    if not photo:
        return ""
    return rf"\ResumePhoto{{{latex_escape(Path(photo).name)}}}"


def render_document(profile: dict[str, Any], view_name: str) -> str:
    candidate = profile["candidate"]
    view = profile["resume_views"][view_name]
    display_name = latex_escape(candidate.get("display_name") or f"{candidate['name']}{candidate.get('name_prefix', '')}")
    fixture_notice = profile.get("fixture_notice", "").strip()
    summary_text = view.get("summary") or candidate.get("summary", "")
    summary = latex_escape(" ".join(value for value in (fixture_notice, summary_text) if value))
    contacts = render_contacts(candidate)
    contact_command = rf"\ResumeContacts{{{contacts}}}" if contacts else r"\ResumeContacts{}"
    skills = render_skills(view.get("skills", []))
    education = render_education(profile.get("education", []))
    claims = render_claim_sections(profile, view)
    digest = profile_digest(profile)
    photo = render_photo_setup(candidate)
    visible_headline = latex_escape(view["headline"])
    return rf"""% Generated by Agent Career Kit from one source-linked profile.
% renderer-version: {RENDERER_VERSION}
% profile-sha256: {digest}
% view: {view_name}
% view-headline: {latex_escape(view["headline"])}
% expected-pages: {view["expected_pages"]}
% Layout based on adongwanai/LLM-Resume-Template resume-photo.tex.
% !TeX TS-program = xelatex
\documentclass{{resume-photo}}
\setCJKmainfont{{FandolSong-Regular.otf}}[BoldFont=FandolSong-Bold.otf]
\renewcommand{{\heiti}}{{\bfseries}}
\hypersetup{{pdfsubject={{profile-sha256:{digest}}}}}
\ResumeName{{{display_name}}}
{photo}
\begin{{document}}
{contact_command}
\ResumeTitle

\begin{{center}}
  \zihao{{5}}\bfseries {visible_headline}
\end{{center}}

\noindent
{summary}

{education}
{skills}
{claims}
\end{{document}}
"""


def selected_views(profile: dict[str, Any], requested: list[str] | None = None) -> list[str]:
    active = active_view_names(profile)
    if requested is None:
        if not active:
            raise ValueError("当前没有启用简历方向；请先完成方向判断并设置 resume_views.<方向>.active=true")
        return active
    inactive = [view_name for view_name in requested if view_name not in active]
    if inactive:
        raise ValueError(f"不能渲染未启用的简历方向: {', '.join(inactive)}")
    return requested


def render_resumes(workspace: Path, view_names: list[str] | None = None) -> list[Path]:
    profile = require_valid_profile(workspace)
    view_names = selected_views(profile, view_names)
    rendered = {view_name: render_document(profile, view_name) for view_name in view_names}
    outputs: list[Path] = []
    for view_name in view_names:
        output_dir = workspace / "outputs" / "resumes" / view_name
        output_dir.mkdir(parents=True, exist_ok=True)
        for asset in LATEX_ASSETS:
            shutil.copy2(asset, output_dir / asset.name)
        photo = profile["candidate"].get("photo", "").strip()
        if photo:
            shutil.copy2(workspace / photo, output_dir / Path(photo).name)
        output = output_dir / "main.tex"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output_dir, delete=False) as handle:
            handle.write(rendered[view_name])
            temporary = Path(handle.name)
        os.replace(temporary, output)
        outputs.append(output)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="按需渲染已启用的 Agent 简历方向。")
    parser.add_argument("workspace")
    parser.add_argument("--view", action="append", choices=VIEW_NAMES, dest="views")
    args = parser.parse_args()
    try:
        outputs = render_resumes(workspace_path(args.workspace), args.views)
    except ValueError as error:
        raise SystemExit(f"简历生成失败：\n{error}") from None
    print("\n".join(str(path) for path in outputs))


if __name__ == "__main__":
    main()
