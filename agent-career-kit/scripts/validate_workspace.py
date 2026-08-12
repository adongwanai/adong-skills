#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from pathlib import Path

from common import PLACEHOLDER_RE, RENDERER_VERSION, load_profile, profile_digest, validate_profile, workspace_path
from render_resumes import LATEX_ASSETS, render_document


REQUIRED_FILES = (
    "candidate-profile.json",
    "evidence-ledger.md",
    "capability-map.md",
    "weaknesses.md",
    "progress.md",
    "outputs/application/application-tracker.csv",
    "outputs/application/interview-schedule.csv",
    "outputs/application/offer-comparison.csv",
)

TRACKER_HEADERS = {
    "application-tracker.csv": [
        "application_id", "company", "role", "source", "route", "status", "date", "next_action", "notes"
    ],
    "interview-schedule.csv": [
        "interview_id", "company", "role", "round", "date", "focus", "result", "review_path"
    ],
    "offer-comparison.csv": [
        "offer_id", "company", "role", "level", "cash", "equity", "bonus", "benefits", "conditions", "deadline", "risk_notes"
    ],
}
APPLICATION_STATUSES = {
    "researching", "ready", "referred", "applied", "screen", "interviewing", "offer", "rejected", "paused", "withdrawn"
}
INTERVIEW_RESULTS = {"pending", "pass", "fail", "withdrawn"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_tracker(path: Path, expected_header: list[str], workspace: Path) -> list[str]:
    errors: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        actual_header = handle.seek(0) or next(csv.reader(handle), [])
    if actual_header != expected_header:
        return [f"invalid tracker header: {path.name}"]
    id_field = expected_header[0]
    ids = [row[id_field] for row in rows]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        errors.append(f"{path.name} requires unique non-empty {id_field} values")
    for row_number, row in enumerate(rows, start=2):
        if path.name == "application-tracker.csv":
            if row["status"] not in APPLICATION_STATUSES:
                errors.append(f"{path.name}:{row_number} has invalid status")
            if row["status"] not in {"rejected", "withdrawn"} and not row["next_action"].strip():
                errors.append(f"{path.name}:{row_number} requires next_action")
            date = row["date"]
        elif path.name == "interview-schedule.csv":
            if row["result"] not in INTERVIEW_RESULTS:
                errors.append(f"{path.name}:{row_number} has invalid result")
            if row["review_path"]:
                review = workspace / row["review_path"]
                if not review.is_file() or workspace not in review.resolve().parents:
                    errors.append(f"{path.name}:{row_number} has invalid review_path")
            date = row["date"]
        else:
            date = row["deadline"]
        if date and not DATE_RE.match(date):
            errors.append(f"{path.name}:{row_number} date must use YYYY-MM-DD")
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
            profile["candidate"]["university"],
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


def _validate_generated_artifacts(workspace: Path, profile: dict) -> list[str]:
    errors: list[str] = []
    digest = profile_digest(profile)
    for view_name in ("development", "algorithm"):
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

    tracker = workspace / "outputs" / "application" / "career-tracker.xlsx"
    if not tracker.is_file() or tracker.stat().st_size == 0:
        errors.append("missing or empty generated artifact: outputs/application/career-tracker.xlsx")
    else:
        try:
            with zipfile.ZipFile(tracker) as archive:
                names = archive.namelist()
                if "xl/workbook.xml" not in names:
                    errors.append("career-tracker.xlsx is not a valid workbook")
                else:
                    workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
                    for sheet in ("Applications", "Interviews", "Offers", "Summary"):
                        if f'name="{sheet}"' not in workbook_xml:
                            errors.append(f"career-tracker.xlsx is missing sheet: {sheet}")
                    xml_text = "\n".join(
                        archive.read(name).decode("utf-8")
                        for name in names
                        if name.startswith("xl/") and name.endswith(".xml")
                    )
                    for marker in ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A"):
                        if marker in xml_text:
                            errors.append(f"career-tracker.xlsx contains formula error: {marker}")
        except zipfile.BadZipFile:
            errors.append("career-tracker.xlsx is not a valid workbook")
    return errors


def validate_workspace(workspace: Path, require_artifacts: bool) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        path = workspace / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty required file: {relative}")

    profile_path = workspace / "candidate-profile.json"
    profile = None
    if profile_path.is_file():
        profile = load_profile(workspace)
        errors.extend(validate_profile(profile, workspace))

    tracker_dir = workspace / "outputs" / "application"
    for filename, expected_header in TRACKER_HEADERS.items():
        path = tracker_dir / filename
        if path.is_file():
            errors.extend(_validate_tracker(path, expected_header, workspace))

    if require_artifacts and profile is not None and not validate_profile(profile, workspace):
        errors.extend(_validate_generated_artifacts(workspace, profile))
    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate an Agent Career Kit workspace.")
    parser.add_argument("workspace")
    parser.add_argument("--require-artifacts", action="store_true")
    args = parser.parse_args()
    workspace = workspace_path(args.workspace)
    errors = validate_workspace(workspace, args.require_artifacts)
    if errors:
        raise SystemExit("workspace validation failed:\n- " + "\n- ".join(errors))
    print(f"OK: {workspace}")


if __name__ == "__main__":
    main()
