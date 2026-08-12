#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from common import (
    PLACEHOLDER_RE,
    RENDERER_VERSION,
    VIEW_NAMES,
    active_view_names,
    load_profile,
    profile_digest,
    validate_profile,
    workspace_path,
)
from career_state import load_state, render_markdown, state_digest, validate_state
from render_resumes import LATEX_ASSETS, render_document


REQUIRED_FILES = (
    "candidate-profile.json",
    "career-state.json",
    "intake.md",
    "evidence-ledger.md",
    "capability-map.md",
    "weaknesses.md",
    "progress.md",
    "application-dashboard.md",
)


def _validate_generated_dashboard(workspace: Path, state: dict) -> list[str]:
    errors: list[str] = []
    dashboard_dir = workspace / "outputs" / "career-dashboard"
    for filename in ("index.html", "style.css", "app.js"):
        path = dashboard_dir / filename
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty generated artifact: {path.relative_to(workspace)}")
    index = dashboard_dir / "index.html"
    if index.is_file() and f"<!-- career-state-sha256: {state_digest(state)} -->" not in index.read_text(encoding="utf-8"):
        errors.append("Offer 驾驶舱与当前 career-state.json 不一致")
    markdown = workspace / "application-dashboard.md"
    if markdown.is_file() and markdown.read_text(encoding="utf-8") != render_markdown(state):
        errors.append("Markdown 求职看板与当前 career-state.json 不一致")
    return errors


def _validate_pdf(path: Path, profile: dict, view_name: str, tex_path: Path) -> list[str]:
    errors: list[str] = []
    if path.stat().st_mtime_ns < tex_path.stat().st_mtime_ns:
        errors.append(f"stale PDF: {path.relative_to(path.parents[4])}")
    if path.read_bytes()[:5] != b"%PDF-":
        return [f"invalid PDF header: {path}"]
    try:
        import pdfplumber
    except ImportError:
        return ["pdfplumber is required for --require-artifacts PDF validation"]
    with pdfplumber.open(path) as pdf:
        expected_pages = profile["resume_views"][view_name]["expected_pages"]
        if len(pdf.pages) != expected_pages:
            errors.append(f"{view_name} PDF expected {expected_pages} pages, got {len(pdf.pages)}")
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        expected_text = (
            profile["candidate"]["name"],
            profile["resume_views"][view_name]["headline"],
            profile["candidate"].get("university", ""),
            next(claim["name"] for claim in profile["claims"] if claim["id"] == profile["resume_views"][view_name]["claim_ids"][0]),
        )
        for value in (*expected_text, profile.get("fixture_notice", "").strip()):
            if not value:
                continue
            if value not in text:
                errors.append(f"{view_name} PDF text extraction is missing: {value}")
        for page in pdf.pages:
            if abs(float(page.width) - 595.28) > 2 or abs(float(page.height) - 841.89) > 2:
                errors.append(f"{view_name} PDF page is not A4")
        subject = str(pdf.metadata.get("Subject", ""))
        if profile_digest(profile) not in subject:
            errors.append(f"{view_name} PDF metadata does not match the current profile")
    return errors


def _validate_generated_resumes(
    workspace: Path, profile: dict, view_names: list[str] | None = None
) -> list[str]:
    errors: list[str] = []
    digest = profile_digest(profile)
    active = active_view_names(profile)
    selected = active if view_names is None else view_names
    for view_name in selected:
        if view_name not in active:
            errors.append(f"不能验证未启用的简历方向: {view_name}")
            continue
        resume_dir = workspace / "outputs" / "resumes" / view_name
        tex_path = resume_dir / "main.tex"
        class_path = resume_dir / LATEX_ASSETS[0].name
        pdf_path = resume_dir / "main.pdf"
        zip_path = resume_dir / "overleaf.zip"
        generated_paths = [tex_path, class_path, pdf_path, zip_path]
        photo = profile["candidate"].get("photo", "").strip()
        if photo:
            generated_paths.append(resume_dir / Path(photo).name)
        for path in generated_paths:
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"missing or empty generated artifact: {path.relative_to(workspace)}")
        if not tex_path.is_file() or tex_path.stat().st_size == 0:
            continue
        tex = tex_path.read_text(encoding="utf-8")
        if tex != render_document(profile, view_name):
            errors.append(f"stale TeX: {tex_path.relative_to(workspace)}")
        if PLACEHOLDER_RE.search(tex):
            errors.append(f"generated artifact contains placeholder: {tex_path.relative_to(workspace)}")
        if class_path.is_file() and class_path.stat().st_size:
            if class_path.read_text(encoding="utf-8") != LATEX_ASSETS[0].read_text(encoding="utf-8"):
                errors.append(f"stale resume class: {class_path.relative_to(workspace)}")
        if pdf_path.is_file() and pdf_path.stat().st_size:
            errors.extend(_validate_pdf(pdf_path, profile, view_name, tex_path))
        if zip_path.is_file() and zip_path.stat().st_size:
            try:
                with zipfile.ZipFile(zip_path) as archive:
                    expected_names = ["NOTICE.txt", "main.tex", "manifest.json", LATEX_ASSETS[0].name]
                    if photo:
                        expected_names.append(Path(photo).name)
                    if sorted(archive.namelist()) != sorted(expected_names):
                        errors.append(f"invalid Overleaf contents: {zip_path.relative_to(workspace)}")
                    elif archive.read("main.tex").decode("utf-8") != tex:
                        errors.append(f"stale Overleaf TeX: {zip_path.relative_to(workspace)}")
                    elif archive.read(LATEX_ASSETS[0].name).decode("utf-8") != LATEX_ASSETS[0].read_text(encoding="utf-8"):
                        errors.append(f"stale Overleaf class: {zip_path.relative_to(workspace)}")
                    else:
                        notice = archive.read("NOTICE.txt").decode("utf-8")
                        for value in ("@adongwanai", "https://creativecommons.org/licenses/by/4.0/", "Feng Kaiyu"):
                            if value not in notice:
                                errors.append(f"incomplete Overleaf provenance: {zip_path.relative_to(workspace)}")
                        manifest = json.loads(archive.read("manifest.json"))
                        if manifest != {
                            "profile_sha256": digest,
                            "renderer_version": RENDERER_VERSION,
                            "view": view_name,
                        }:
                            errors.append(f"stale Overleaf manifest: {zip_path.relative_to(workspace)}")
            except (zipfile.BadZipFile, KeyError, UnicodeDecodeError, json.JSONDecodeError):
                errors.append(f"invalid Overleaf ZIP: {zip_path.relative_to(workspace)}")

    return errors


def _validate_generated_portfolio(workspace: Path, profile: dict) -> list[str]:
    errors: list[str] = []
    digest = profile_digest(profile)
    portfolio_dir = workspace / "outputs" / "portfolio"
    for filename in ("index.html", "style.css", "app.js"):
        path = portfolio_dir / filename
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty generated artifact: {path.relative_to(workspace)}")
    index = portfolio_dir / "index.html"
    if index.is_file() and index.stat().st_size:
        text = index.read_text(encoding="utf-8")
        if f"<!-- profile-sha256: {digest} -->" not in text:
            errors.append("portfolio is stale")
        if PLACEHOLDER_RE.search(text):
            errors.append("generated portfolio contains a placeholder")
        fixture_notice = profile.get("fixture_notice", "").strip()
        if fixture_notice and fixture_notice not in text:
            errors.append("portfolio is missing fixture disclosure")

    return errors


def validate_workspace(
    workspace: Path,
    require_artifacts: bool = False,
    *,
    stage: str = "profile",
    require_resumes: bool = False,
    require_portfolio: bool = False,
    require_dashboard: bool = False,
    view_names: list[str] | None = None,
) -> list[str]:
    errors: list[str] = []
    required_files = ("candidate-profile.json", "career-state.json", "intake.md") if stage == "intake" else REQUIRED_FILES
    for relative in required_files:
        path = workspace / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty required file: {relative}")

    state_path = workspace / "career-state.json"
    state = load_state(workspace) if state_path.is_file() else None
    if state is not None:
        errors.extend(validate_state(state, workspace))
    if stage == "intake":
        if require_dashboard and state is not None:
            errors.extend(_validate_generated_dashboard(workspace, state))
        return errors

    profile_path = workspace / "candidate-profile.json"
    profile = None
    if profile_path.is_file():
        profile = load_profile(workspace)
        errors.extend(validate_profile(profile, workspace))

    profile_valid = profile is not None and not validate_profile(profile, workspace)
    if profile_valid and (require_artifacts or require_resumes):
        errors.extend(_validate_generated_resumes(workspace, profile, view_names))
    if profile_valid and (require_artifacts or require_portfolio):
        errors.extend(_validate_generated_portfolio(workspace, profile))
    if state is not None and require_dashboard:
        errors.extend(_validate_generated_dashboard(workspace, state))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="分阶段验证 Agent 求职工作区。")
    parser.add_argument("workspace")
    parser.add_argument("--stage", choices=("intake", "profile"), default="profile")
    parser.add_argument("--require-resumes", action="store_true")
    parser.add_argument("--view", action="append", choices=VIEW_NAMES, dest="views")
    parser.add_argument("--require-portfolio", action="store_true")
    parser.add_argument("--require-dashboard", action="store_true")
    parser.add_argument("--require-artifacts", action="store_true", help="维护者兼容参数：验证简历和作品集。")
    args = parser.parse_args()
    workspace = workspace_path(args.workspace)
    errors = validate_workspace(
        workspace,
        args.require_artifacts,
        stage=args.stage,
        require_resumes=args.require_resumes,
        require_portfolio=args.require_portfolio,
        require_dashboard=args.require_dashboard,
        view_names=args.views,
    )
    if errors:
        raise SystemExit("工作区验证失败：\n- " + "\n- ".join(errors))
    print(f"验证通过：{workspace}（阶段：{args.stage}）")


if __name__ == "__main__":
    main()
