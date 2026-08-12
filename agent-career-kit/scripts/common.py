#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SKILL_DIR = Path(__file__).resolve().parents[1]
NESTED_REPO_DIR = SKILL_DIR.parents[1]
REPO_DIR = (
    NESTED_REPO_DIR
    if SKILL_DIR.parent.name == "skills" and (NESTED_REPO_DIR / "examples" / "anonymous-candidate").is_dir()
    else SKILL_DIR.parent
)
PUBLIC_EXAMPLE_DIRS = {
    REPO_DIR / "examples" / "adong-public-case",
    REPO_DIR / "examples" / "anonymous-candidate",
}
PROFILE_NAME = "candidate-profile.json"
RENDERER_VERSION = "4"
FACT_STATUSES = {"provided", "confirmed"}
ALL_STATUSES = FACT_STATUSES | {"planned"}
VISIBILITIES = {"private", "resume", "public"}
SHIP_GATES = {"block", "caution", "pass", "improve"}
CAREER_STAGES = {"campus", "experienced", "senior"}
VIEW_NAMES = ("development", "algorithm")
CLAIM_CATEGORIES = {
    "experience",
    "project",
    "research",
    "open_source",
    "publication",
    "award",
    "leadership",
}
SOURCE_KINDS = {"candidate_statement", "file", "url"}
EVIDENCE_CLASSES = {
    "statement",
    "resume",
    "repository",
    "report",
    "dataset",
    "trace",
    "benchmark",
    "publication",
    "public_profile",
    "jd",
}
STRONG_EVIDENCE_CLASSES = {"repository", "report", "dataset", "trace", "benchmark", "publication"}
PUBLIC_ASSET_SUFFIXES = {".jpg", ".jpeg", ".png", ".svg", ".webp"}
PLACEHOLDER_RE = re.compile(r"(?:TODO|TBD|X{2,}|[xX]{2,}|\[待确认\]|\{\{[^}]+\}\})")


def workspace_path(raw_path: str) -> Path:
    workspace = Path(raw_path).expanduser().resolve()
    if workspace not in PUBLIC_EXAMPLE_DIRS and (workspace == REPO_DIR or REPO_DIR in workspace.parents):
        raise ValueError("candidate workspace must be outside the Agent Career Kit repository")
    return workspace


def load_profile(workspace: Path) -> dict[str, Any]:
    return json.loads((workspace / PROFILE_NAME).read_text(encoding="utf-8"))


def canonical_profile(profile: dict[str, Any]) -> str:
    return json.dumps(profile, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def profile_digest(profile: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_profile(profile).encode("utf-8")).hexdigest()


def is_safe_web_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _validate_source_path(workspace: Path, value: str) -> str | None:
    relative = Path(value)
    if not value or relative.is_absolute() or ".." in relative.parts:
        return "file source must be a relative workspace path"
    source = workspace / relative
    if not source.is_file():
        return f"file source does not exist: {value}"
    if not _inside(source.resolve(), workspace):
        return f"file source escapes the workspace: {value}"
    return None


def _validate_svg(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        return "SVG must not contain a DTD or entity"
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return "SVG is not valid XML"
    if root.tag.rsplit("}", 1)[-1] != "svg":
        return "SVG root element must be svg"
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] in {"script", "foreignObject"}:
            return "SVG must not contain executable or foreign content"
        for name, value in element.attrib.items():
            local_name = name.rsplit("}", 1)[-1].lower()
            if local_name.startswith("on"):
                return "SVG must not contain event handlers"
            if re.search(r"(?:javascript:|https?:|data:)", value.lower()):
                return "SVG must not contain external or executable URLs"
            if local_name in {"href", "src"} and value and not value.startswith("#"):
                return "SVG must not reference external content"
    return None


def validate_public_asset_path(workspace: Path, raw_path: str) -> str | None:
    relative = Path(raw_path)
    if not raw_path or relative.is_absolute() or ".." in relative.parts:
        return "portfolio visual path must be relative"
    if not relative.parts or relative.parts[0] != "public-assets":
        return "portfolio visual must be stored under public-assets/"
    source = workspace / relative
    if not source.is_file():
        return f"portfolio visual does not exist: {raw_path}"
    public_root = (workspace / "public-assets").resolve()
    if source.is_symlink() or not _inside(source.resolve(), public_root):
        return f"portfolio visual must not be a symlink or escape public-assets/: {raw_path}"
    suffix = source.suffix.lower()
    if suffix not in PUBLIC_ASSET_SUFFIXES:
        return f"portfolio visual type is not allowed: {suffix or '<none>'}"
    header = source.read_bytes()[:12]
    if suffix == ".png" and header[:8] != b"\x89PNG\r\n\x1a\n":
        return "portfolio PNG signature is invalid"
    if suffix in {".jpg", ".jpeg"} and header[:3] != b"\xff\xd8\xff":
        return "portfolio JPEG signature is invalid"
    if suffix == ".webp" and not (header[:4] == b"RIFF" and header[8:12] == b"WEBP"):
        return "portfolio WebP signature is invalid"
    if suffix == ".svg":
        return _validate_svg(source)
    return None


def _check_source_refs(
    errors: list[str], prefix: str, refs: Any, source_ids: set[str], required: bool = True
) -> list[str]:
    if not isinstance(refs, list) or (required and not refs):
        errors.append(f"{prefix}.source_refs must contain at least one source id")
        return []
    clean = [ref for ref in refs if isinstance(ref, str) and ref]
    if len(clean) != len(refs):
        errors.append(f"{prefix}.source_refs must contain non-empty strings")
    if len(clean) != len(set(clean)):
        errors.append(f"{prefix}.source_refs contains duplicates")
    for ref in clean:
        if ref not in source_ids:
            errors.append(f"{prefix}.source_refs references unknown source: {ref}")
    return clean


def validate_profile(profile: dict[str, Any], workspace: Path) -> list[str]:
    workspace = workspace.resolve()
    errors: list[str] = []
    if profile.get("schema_version") != 2:
        errors.append("schema_version must be 2")
    if not isinstance(profile.get("fixture_notice", ""), str):
        errors.append("fixture_notice must be a string")

    sources = profile.get("sources", [])
    if not isinstance(sources, list):
        errors.append("sources must be a list")
        sources = []
    source_ids: set[str] = set()
    source_classes: dict[str, str] = {}
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        source_id = source.get("id", "") if isinstance(source, dict) else ""
        if not source_id:
            errors.append(f"{prefix}.id is required")
            continue
        if source_id in source_ids:
            errors.append(f"duplicate source id: {source_id}")
        source_ids.add(source_id)
        kind = source.get("kind")
        value = source.get("value", "")
        evidence_class = source.get("evidence_class", "statement" if kind == "candidate_statement" else "resume")
        if evidence_class not in EVIDENCE_CLASSES:
            errors.append(f"{prefix}.evidence_class is invalid")
        else:
            source_classes[source_id] = evidence_class
        if kind not in SOURCE_KINDS:
            errors.append(f"{prefix}.kind is invalid")
        elif kind == "file":
            path_error = _validate_source_path(workspace, value)
            if path_error:
                errors.append(f"{prefix}: {path_error}")
        elif kind == "url" and not is_safe_web_url(value):
            errors.append(f"{prefix}.value must be an http(s) URL")
        elif kind == "candidate_statement" and not value.strip():
            errors.append(f"{prefix}.value is required")
        if not source.get("accessed_at", "").strip():
            errors.append(f"{prefix}.accessed_at is required")

    candidate = profile.get("candidate", {})
    if not candidate.get("name", "").strip():
        errors.append("candidate.name is required")
    if not candidate.get("headline", "").strip():
        errors.append("candidate.headline is required")
    if candidate.get("career_stage") not in CAREER_STAGES:
        errors.append("candidate.career_stage must be campus, experienced, or senior")
    photo = candidate.get("photo", "").strip()
    if photo:
        path_error = validate_public_asset_path(workspace, photo)
        if path_error:
            errors.append(f"candidate.photo: {path_error}")
    links = candidate.get("links", [])
    link_labels: set[str] = set()
    for index, link in enumerate(links):
        prefix = f"candidate.links[{index}]"
        label = link.get("label", "").strip()
        if not label or label in link_labels:
            errors.append(f"{prefix}.label must be non-empty and unique")
        link_labels.add(label)
        if not is_safe_web_url(link.get("url", "")):
            errors.append(f"{prefix}.url must be an http(s) URL")
    claims = profile.get("claims", [])
    if not isinstance(claims, list) or not claims:
        errors.append("at least one claim is required")
        claims = []
    claim_ids: set[str] = set()
    bullet_ids: set[str] = set()
    claims_by_id: dict[str, dict[str, Any]] = {}
    bullet_owner: dict[str, str] = {}
    for index, claim in enumerate(claims):
        prefix = f"claims[{index}]"
        claim_id = claim.get("id", "").strip()
        if not claim_id:
            errors.append(f"{prefix}.id is required")
        elif claim_id in claim_ids:
            errors.append(f"duplicate claim id: {claim_id}")
        else:
            claim_ids.add(claim_id)
            claims_by_id[claim_id] = claim

        category = claim.get("category")
        status = claim.get("status")
        visibility = claim.get("visibility", "resume")
        if category not in CLAIM_CATEGORIES:
            errors.append(f"{prefix}.category is invalid")
        if status not in ALL_STATUSES:
            errors.append(f"{prefix}.status is invalid")
        if visibility not in VISIBILITIES:
            errors.append(f"{prefix}.visibility is invalid")
        if not claim.get("name", "").strip():
            errors.append(f"{prefix}.name is required")
        _check_source_refs(errors, prefix, claim.get("source_refs"), source_ids, required=status in FACT_STATUSES)

        bullets = claim.get("bullets", [])
        if not isinstance(bullets, list) or not bullets:
            errors.append(f"{prefix}.bullets must contain at least one statement")
            bullets = []
        claim_bullet_ids: set[str] = set()
        for bullet_index, bullet in enumerate(bullets):
            bullet_prefix = f"{prefix}.bullets[{bullet_index}]"
            bullet_id = bullet.get("id", "").strip() if isinstance(bullet, dict) else ""
            if not bullet_id:
                errors.append(f"{bullet_prefix}.id is required")
            elif bullet_id in bullet_ids:
                errors.append(f"duplicate bullet id: {bullet_id}")
            else:
                bullet_ids.add(bullet_id)
                claim_bullet_ids.add(bullet_id)
                bullet_owner[bullet_id] = claim_id
            if not isinstance(bullet, dict) or not bullet.get("text", "").strip():
                errors.append(f"{bullet_prefix}.text is required")
            elif status in FACT_STATUSES:
                _check_source_refs(errors, bullet_prefix, bullet.get("source_refs"), source_ids)
            origin = bullet.get("text_origin", "source") if isinstance(bullet, dict) else "source"
            if origin not in {"source", "agent"}:
                errors.append(f"{bullet_prefix}.text_origin must be source or agent")
            elif origin == "agent":
                approval = bullet.get("approval", {})
                if approval.get("status") != "approved" or not approval.get("record", "").strip():
                    errors.append(f"{bullet_prefix}: Agent 改写必须包含用户确认记录")
                if approval.get("source_ref") not in source_ids:
                    errors.append(f"{bullet_prefix}.approval.source_ref must reference a known source")

        if status == "planned":
            if claim.get("ship_gate") != "block":
                errors.append(f"{prefix}: planned claims must use ship_gate=block")
        elif visibility in {"private", "resume", "public"}:
            if not claim.get("contribution", "").strip():
                errors.append(f"{prefix}.contribution is required for selected outputs")
            if not claim.get("limitation", "").strip():
                errors.append(f"{prefix}.limitation is required for selected outputs")
            if claim.get("ship_gate") not in {"pass", "improve", "caution"}:
                errors.append(f"{prefix}.ship_gate must be pass, improve, or caution for selected outputs")
            if category in {"project", "research"} and claim.get("ship_gate") == "pass":
                proof = claim.get("proof", {})
                proof_refs = claim.get("proof_refs", {})
                proof_notes = claim.get("proof_notes", {})
                proof_source_ids: set[str] = set()
                notes: list[str] = []
                for key in ("task_set", "baseline", "verification", "trace", "failure", "result"):
                    proof_id = proof.get(key, "")
                    if proof_id not in claim_bullet_ids:
                        errors.append(f"{prefix}.proof.{key} must reference one of the claim's bullet ids")
                    proof_source_ids.update(
                        _check_source_refs(errors, f"{prefix}.proof_refs.{key}", proof_refs.get(key), source_ids)
                    )
                    note = proof_notes.get(key, "")
                    if not isinstance(note, str) or not note.strip():
                        errors.append(f"{prefix}.proof_notes.{key} is required for pass")
                    else:
                        notes.append(note.strip())
                if not any(source_classes.get(source_id) in STRONG_EVIDENCE_CLASSES for source_id in proof_source_ids):
                    errors.append(f"{prefix}: pass requires at least one artifact-class evidence source")
                if len(proof_source_ids) < 2:
                    errors.append(f"{prefix}: pass proof must reference at least two distinct sources")
                if len(notes) != len(set(notes)):
                    errors.append(f"{prefix}: pass proof_notes must describe six distinct evidence roles")
        elif claim.get("ship_gate") not in SHIP_GATES:
            errors.append(f"{prefix}.ship_gate is invalid")

    for index, item in enumerate(profile.get("education", [])):
        prefix = f"education[{index}]"
        if item.get("status") not in FACT_STATUSES:
            errors.append(f"{prefix}.status must be provided or confirmed")
        if not item.get("school", "").strip():
            errors.append(f"{prefix}.school is required")
        _check_source_refs(errors, prefix, item.get("source_refs"), source_ids)

    views = profile.get("resume_views", {})
    for view_name in VIEW_NAMES:
        view = views.get(view_name)
        if not isinstance(view, dict):
            errors.append(f"resume_views.{view_name} is required")
            continue
        prefix = f"resume_views.{view_name}"
        active = view.get("active", bool(view.get("claim_ids")))
        if not isinstance(active, bool):
            errors.append(f"{prefix}.active must be true or false")
            active = False
        if not active:
            if view.get("claim_ids"):
                errors.append(f"{prefix}.claim_ids must be empty when the view is inactive")
            continue
        if not view.get("headline", "").strip():
            errors.append(f"{prefix}.headline is required")
        if not isinstance(view.get("expected_pages"), int) or view["expected_pages"] < 1:
            errors.append(f"{prefix}.expected_pages must be a positive integer")
        selected_ids = view.get("claim_ids", [])
        if not selected_ids:
            errors.append(f"{prefix}.claim_ids must not be empty")
        if len(selected_ids) != len(set(selected_ids)):
            errors.append(f"{prefix}.claim_ids contains duplicates")
        for claim_id in selected_ids:
            claim = claims_by_id.get(claim_id)
            if not claim:
                errors.append(f"{prefix} references unknown claim: {claim_id}")
            elif claim.get("status") == "planned":
                errors.append(f"{prefix} references planned claim: {claim_id}")
        summary_refs = view.get("summary_claim_ids", [])
        if view.get("summary", "").strip() and not summary_refs:
            errors.append(f"{prefix}.summary_claim_ids is required when summary is present")
        for claim_id in summary_refs:
            if claim_id not in selected_ids:
                errors.append(f"{prefix}.summary_claim_ids must reference selected claims: {claim_id}")
        bullet_selection = view.get("bullet_ids_by_claim", {})
        if set(bullet_selection) != set(selected_ids):
            errors.append(f"{prefix}.bullet_ids_by_claim must cover exactly the selected claims")
        for claim_id, selected_bullets in bullet_selection.items():
            if not selected_bullets or len(selected_bullets) != len(set(selected_bullets)):
                errors.append(f"{prefix}.bullet_ids_by_claim.{claim_id} must be a non-empty unique list")
            for bullet_id in selected_bullets:
                if bullet_owner.get(bullet_id) != claim_id:
                    errors.append(f"{prefix}.bullet_ids_by_claim.{claim_id} references invalid bullet: {bullet_id}")
        for group_index, group in enumerate(view.get("skills", [])):
            group_prefix = f"{prefix}.skills[{group_index}]"
            if group.get("text", "").strip():
                pass
            elif not group.get("group", "").strip() or not group.get("items"):
                errors.append(f"{group_prefix} requires text or group and items")
            evidence_ids = group.get("evidence_claim_ids", [])
            if not evidence_ids:
                errors.append(f"{group_prefix}.evidence_claim_ids is required")
            for claim_id in evidence_ids:
                if claim_id not in selected_ids:
                    errors.append(f"{group_prefix} references unselected claim: {claim_id}")
    portfolio = profile.get("portfolio", {})
    if not isinstance(portfolio.get("label", ""), str):
        errors.append("portfolio.label must be a string")
    featured_ids = portfolio.get("featured_claim_ids", [])
    if len(featured_ids) != len(set(featured_ids)):
        errors.append("portfolio.featured_claim_ids contains duplicates")
    for claim_id in featured_ids:
        claim = claims_by_id.get(claim_id)
        if not claim:
            errors.append(f"portfolio references unknown claim: {claim_id}")
        elif claim.get("status") == "planned":
            errors.append(f"portfolio references planned claim: {claim_id}")
    if portfolio.get("summary", "").strip() and not portfolio.get("summary_claim_ids"):
        errors.append("portfolio.summary_claim_ids is required when summary is present")
    for claim_id in portfolio.get("summary_claim_ids", []):
        if claim_id not in featured_ids:
            errors.append(f"portfolio.summary_claim_ids must reference a featured claim: {claim_id}")
    for index, metric in enumerate(portfolio.get("metrics", [])):
        prefix = f"portfolio.metrics[{index}]"
        claim_id = metric.get("claim_id", "")
        bullet_id = metric.get("bullet_id", "")
        if not metric.get("value", "").strip() or not metric.get("label", "").strip():
            errors.append(f"{prefix} requires value and label")
        if claim_id not in featured_ids or bullet_owner.get(bullet_id) != claim_id:
            errors.append(f"{prefix} must reference a featured claim and one of its bullets")
    seen_visual_claims: set[str] = set()
    for index, visual in enumerate(portfolio.get("visuals", [])):
        prefix = f"portfolio.visuals[{index}]"
        claim_id = visual.get("claim_id", "")
        if claim_id not in featured_ids:
            errors.append(f"{prefix} must reference a featured public claim")
        if claim_id in seen_visual_claims:
            errors.append(f"{prefix} duplicates a claim visual")
        seen_visual_claims.add(claim_id)
        path_error = validate_public_asset_path(workspace, visual.get("path", ""))
        if path_error:
            errors.append(f"{prefix}: {path_error}")
        if not visual.get("alt", "").strip():
            errors.append(f"{prefix}.alt is required")
    for claim_id, detail in portfolio.get("details", {}).items():
        prefix = f"portfolio.details.{claim_id}"
        if claim_id not in featured_ids:
            errors.append(f"{prefix} must reference a featured public claim")
            continue
        claim_bullet_ids = {bullet["id"] for bullet in claims_by_id[claim_id]["bullets"]}
        for index, metric in enumerate(detail.get("metrics", [])):
            metric_prefix = f"{prefix}.metrics[{index}]"
            if not metric.get("value", "").strip() or not metric.get("label", "").strip():
                errors.append(f"{metric_prefix} requires value and label")
            if metric.get("bullet_id") not in claim_bullet_ids:
                errors.append(f"{metric_prefix} must reference one of the claim's bullets")
        for index, link in enumerate(detail.get("links", [])):
            link_prefix = f"{prefix}.links[{index}]"
            if not link.get("label", "").strip():
                errors.append(f"{link_prefix}.label is required")
            if not is_safe_web_url(link.get("url", "")):
                errors.append(f"{link_prefix}.url must be an http(s) URL")

    resume_downloads = portfolio.get("resume_downloads", [])
    if not isinstance(resume_downloads, list) or len(resume_downloads) != len(set(resume_downloads)):
        errors.append("portfolio.resume_downloads must be a unique list")
        resume_downloads = []
    for view_name in resume_downloads:
        if view_name not in VIEW_NAMES:
            errors.append(f"portfolio.resume_downloads references unknown view: {view_name}")
            continue
        view = views.get(view_name, {})
        if not view.get("active", bool(view.get("claim_ids"))):
            errors.append(f"portfolio.resume_downloads references inactive view: {view_name}")

    serialized = canonical_profile(profile)
    if PLACEHOLDER_RE.search(serialized):
        errors.append("candidate profile contains unresolved placeholders")
    return errors


def claims_by_id(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {claim["id"]: claim for claim in profile["claims"]}


def bullets_by_id(claim: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {bullet["id"]: bullet for bullet in claim["bullets"]}


def active_view_names(profile: dict[str, Any]) -> list[str]:
    views = profile.get("resume_views", {})
    return [
        view_name
        for view_name in VIEW_NAMES
        if views.get(view_name, {}).get("active", bool(views.get(view_name, {}).get("claim_ids")))
    ]


def validate_application_request(request: dict[str, Any], profile: dict[str, Any], workspace: Path) -> list[str]:
    errors: list[str] = []
    if request.get("schema_version") != 1:
        errors.append("application request schema_version must be 1")
    for key in ("slug", "company", "role", "jd_path", "jd_sha256", "source_view"):
        if not isinstance(request.get(key), str) or not request[key].strip():
            errors.append(f"application request {key} is required")
    slug = request.get("slug", "")
    if isinstance(slug, str) and slug and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        errors.append("application request slug must use lowercase letters, numbers, and hyphens")

    jd_value = request.get("jd_path", "")
    if isinstance(jd_value, str) and jd_value:
        jd_path = Path(jd_value)
        if jd_path.is_absolute() or ".." in jd_path.parts:
            errors.append("application request jd_path must be a relative workspace path")
        else:
            source = workspace / jd_path
            if not source.is_file():
                errors.append("application request JD file does not exist")
            elif hashlib.sha256(source.read_bytes()).hexdigest() != request.get("jd_sha256"):
                errors.append("application request JD digest is stale")

    source_view = request.get("source_view")
    if source_view not in active_view_names(profile):
        errors.append("application request source_view must be active")

    claim_map = claims_by_id(profile)
    selected_ids = request.get("claim_ids", [])
    if not isinstance(selected_ids, list) or not selected_ids or len(selected_ids) != len(set(selected_ids)):
        errors.append("application request claim_ids must be a non-empty unique list")
        selected_ids = []
    for claim_id in selected_ids:
        claim = claim_map.get(claim_id)
        if not claim:
            errors.append(f"application request references unknown claim: {claim_id}")
        elif claim.get("status") == "planned":
            errors.append(f"application request references a claim unavailable to resumes: {claim_id}")

    headline = request.get("headline", "")
    if not isinstance(headline, str) or not headline.strip():
        errors.append("application request headline is required")
    summary = request.get("summary", "")
    summary_refs = request.get("summary_claim_ids", [])
    if not isinstance(summary, str):
        errors.append("application request summary must be a string")
        summary = ""
    if not isinstance(summary_refs, list):
        errors.append("application request summary_claim_ids must be a list")
        summary_refs = []
    if summary.strip() and not summary_refs:
        errors.append("application request summary_claim_ids is required when summary is present")
    for claim_id in summary_refs:
        if claim_id not in selected_ids:
            errors.append("application request summary_claim_ids must reference selected claims")

    bullet_selection = request.get("bullet_ids_by_claim", {})
    if not isinstance(bullet_selection, dict) or set(bullet_selection) != set(selected_ids):
        errors.append("application request bullet_ids_by_claim must cover exactly the selected claims")
    else:
        for claim_id, bullet_ids in bullet_selection.items():
            valid_ids = set(bullets_by_id(claim_map[claim_id])) if claim_id in claim_map else set()
            if not isinstance(bullet_ids, list):
                errors.append(f"application request bullets for {claim_id} must be a list")
                continue
            if not bullet_ids or len(bullet_ids) != len(set(bullet_ids)):
                errors.append(f"application request bullets for {claim_id} must be non-empty and unique")
            for bullet_id in bullet_ids:
                if bullet_id not in valid_ids:
                    errors.append(f"application request references invalid bullet: {bullet_id}")

    selected_bullet_ids = set()
    if isinstance(bullet_selection, dict):
        selected_bullet_ids = {
            bullet_id
            for bullet_ids in bullet_selection.values()
            if isinstance(bullet_ids, list)
            for bullet_id in bullet_ids
        }
    bullet_overrides = request.get("bullet_overrides", {})
    if not isinstance(bullet_overrides, dict):
        errors.append("application request bullet_overrides must be an object")
    else:
        current_bullets = {
            bullet["id"]: bullet["text"]
            for claim in profile.get("claims", [])
            for bullet in claim.get("bullets", [])
        }
        for bullet_id, override in bullet_overrides.items():
            prefix = f"application request bullet_overrides.{bullet_id}"
            if bullet_id not in selected_bullet_ids:
                errors.append(f"{prefix} must reference a selected bullet")
            if not isinstance(override, dict):
                errors.append(f"{prefix} must be an object")
                continue
            if override.get("source_text") != current_bullets.get(bullet_id):
                errors.append(f"{prefix}.source_text does not match the current profile")
            if not isinstance(override.get("text"), str) or not override["text"].strip():
                errors.append(f"{prefix}.text is required")

    skills = request.get("skills", [])
    if not isinstance(skills, list):
        errors.append("application request skills must be a list")
    else:
        for index, group in enumerate(skills):
            refs = group.get("evidence_claim_ids", []) if isinstance(group, dict) else []
            if not refs or any(claim_id not in selected_ids for claim_id in refs):
                errors.append(f"application request skills[{index}] must reference selected claims")

    for key in ("jd_summary", "selection_rationale"):
        if not isinstance(request.get(key), str) or not request[key].strip():
            errors.append(f"application request {key} is required")
    risks = request.get("risks", [])
    if not isinstance(risks, list) or not risks or any(not isinstance(item, str) or not item.strip() for item in risks):
        errors.append("application request risks must be a non-empty list of strings")
        risks = []

    requirements = request.get("requirements", [])
    if not isinstance(requirements, list) or not requirements:
        errors.append("application request requirements must not be empty")
        requirements = []
    else:
        requirement_ids: set[str] = set()
        for index, requirement in enumerate(requirements):
            prefix = f"application request requirements[{index}]"
            if not isinstance(requirement, dict):
                errors.append(f"{prefix} must be an object")
                continue
            requirement_id = requirement.get("id", "")
            if not requirement_id or requirement_id in requirement_ids:
                errors.append(f"{prefix}.id must be non-empty and unique")
            requirement_ids.add(requirement_id)
            if not requirement.get("requirement", "").strip():
                errors.append(f"{prefix}.requirement is required")
            mapped_ids = requirement.get("claim_ids", [])
            if not isinstance(mapped_ids, list):
                errors.append(f"{prefix}.claim_ids must be a list")
                mapped_ids = []
            if any(claim_id not in selected_ids for claim_id in mapped_ids):
                errors.append(f"{prefix}.claim_ids must reference selected claims")
            gap = requirement.get("gap", "")
            if not isinstance(gap, str):
                errors.append(f"{prefix}.gap must be a string")
                gap = ""
            if not mapped_ids and not gap.strip():
                errors.append(f"{prefix} must map evidence or state a gap")

    approval = request.get("approval", {})
    if not isinstance(approval, dict):
        errors.append("application request approval must be an object")
        approval = {}
    if approval.get("status") not in {"draft", "approved"}:
        errors.append("application request approval.status must be draft or approved")
    if approval.get("status") == "approved" and (
        not approval.get("approved_at", "").strip() or not approval.get("record", "").strip()
    ):
        errors.append("approved application request requires approved_at and record")
    if approval.get("status") == "approved":
        draft_markers = ("待填写", "待映射", "待提取", "尚未确认")
        for key in ("jd_summary", "selection_rationale"):
            value = request.get(key, "")
            if isinstance(value, str) and any(marker in value for marker in draft_markers):
                errors.append(f"approved application request must complete {key}")
        if any(any(marker in risk for marker in draft_markers) for risk in risks):
            errors.append("approved application request must complete risks")
        for index, requirement in enumerate(requirements):
            gap = requirement.get("gap", "")
            if not requirement.get("claim_ids") and isinstance(gap, str) and gap.strip() in {"", "待映射"}:
                errors.append(f"application request requirements[{index}] must be mapped or record a concrete gap")
    return errors


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def require_valid_profile(workspace: Path) -> dict[str, Any]:
    profile = load_profile(workspace)
    errors = validate_profile(profile, workspace)
    if errors:
        raise ValueError("invalid candidate profile:\n- " + "\n- ".join(errors))
    return profile
