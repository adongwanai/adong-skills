#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from common import FACT_STATUSES, SKILL_DIR, claims_by_id, profile_digest, require_valid_profile, workspace_path


CATEGORY_LABELS = {
    "education": "教育",
    "experience": "实习经历",
    "leadership": "工作经历",
    "project": "项目",
    "open_source": "开源",
    "research": "论文 / 研究",
    "publication": "论文",
    "award": "荣誉",
}

FILTER_GROUPS = (
    ("education", ("education",), "教育"),
    ("work", ("experience", "leadership"), "工作"),
    ("project", ("project",), "项目"),
    ("research", ("research", "publication"), "论文 / 研究"),
    ("open_source", ("open_source",), "开源"),
)


def render_links(candidate: dict[str, Any]) -> str:
    links = [
        '<a class="button primary" href="../resumes/development/main.pdf">开发简历</a>',
        '<a class="button" href="../resumes/algorithm/main.pdf">算法简历</a>',
    ]
    selected = set(candidate["contact_visibility"]["public"])
    for link in candidate.get("links", []):
        if link["label"] not in selected:
            continue
        links.append(
            f'<a class="button" href="{html.escape(link["url"], quote=True)}">{html.escape(link["label"])}</a>'
        )
    return "\n".join(links)


def render_metrics(metrics: list[dict[str, str]]) -> str:
    return "\n".join(
        f'<div class="metric-card"><strong>{html.escape(metric["value"])}</strong><span>{html.escape(metric["label"])}</span></div>'
        for metric in metrics
    )


def render_filters(profile: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    categories = {claim["category"] for claim in claims}
    if any(
        item["status"] in FACT_STATUSES and item["visibility"] == "public" and item["public_safe"] is True
        for item in profile.get("education", [])
    ):
        categories.add("education")
    buttons = ['<button type="button" class="active" data-filter="all" aria-pressed="true">全部</button>']
    for name, members, label in FILTER_GROUPS:
        if categories.intersection(members):
            buttons.append(
                f'<button type="button" data-filter="{name}" data-categories="{" ".join(members)}" '
                f'aria-pressed="false">{label}</button>'
            )
    return "\n".join(buttons)


def copy_visuals(workspace: Path, output_dir: Path, profile: dict[str, Any]) -> dict[str, dict[str, str]]:
    copied: dict[str, dict[str, str]] = {}
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    for index, visual in enumerate(profile.get("portfolio", {}).get("visuals", []), start=1):
        source = workspace / visual["path"]
        target_name = f"project-{index}{source.suffix.lower()}"
        shutil.copy2(source, assets_dir / target_name)
        copied[visual["claim_id"]] = {"path": f"assets/{target_name}", "alt": visual["alt"]}
    return copied


def date_range(item: dict[str, Any]) -> str:
    start = item.get("start", "")
    end = item.get("end", "")
    if start and end and end != "Present":
        return f"{start} — {end}"
    if start and end == "Present":
        return f"{start} — 至今"
    return start or end


def render_card_stats(metrics: list[dict[str, str]], claim_id: str) -> str:
    claim_metrics = [metric for metric in metrics if metric.get("claim_id") == claim_id]
    if not claim_metrics:
        return ""
    cards = "".join(
        f'<div><strong>{html.escape(metric["value"])}</strong><span>{html.escape(metric["label"])}</span></div>'
        for metric in claim_metrics
    )
    return f'<div class="card-stats">{cards}</div>'


def render_claim_card(claim: dict[str, Any], metrics: list[dict[str, str]], visuals: dict[str, dict[str, str]]) -> str:
    tags = "".join(f"<span>{html.escape(tag)}</span>" for tag in claim.get("tags", []))
    category = claim["category"]
    label = CATEGORY_LABELS.get(category, category)
    visual = visuals.get(claim["id"])
    visual_html = ""
    if visual:
        visual_html = (
            f'<figure class="card-visual"><img src="{html.escape(visual["path"], quote=True)}" '
            f'alt="{html.escape(visual["alt"], quote=True)}"></figure>'
        )
    return f"""
<article class="timeline-card" data-category="{html.escape(category)}" data-detail-id="{html.escape(claim["id"], quote=True)}" role="button" tabindex="0" aria-label="查看 {html.escape(claim['name'], quote=True)} 详情">
  <div class="timeline-date">
    <time>{html.escape(date_range(claim))}</time>
    <span>{html.escape(label)}</span>
  </div>
  <div class="timeline-dot" aria-hidden="true"></div>
  <div class="timeline-content">
    <p class="card-kicker">{html.escape(claim.get('role', ''))}</p>
    <h3>{html.escape(claim['name'])}</h3>
    <p class="organization">{html.escape(claim.get('organization', ''))}</p>
    {visual_html}
    <p class="description">{html.escape(claim.get('contribution', ''))}</p>
    {render_card_stats(metrics, claim["id"])}
    <div class="tags">{tags}</div>
    <span class="detail-cue">查看详情</span>
  </div>
</article>"""


def render_education_card(item: dict[str, Any]) -> str:
    title = item["school"]
    detail = " · ".join(value for value in (item.get("degree", ""), item.get("detail", "")) if value)
    return f"""
<article class="timeline-card" data-category="education">
  <div class="timeline-date">
    <time>{html.escape(date_range(item))}</time>
    <span>教育</span>
  </div>
  <div class="timeline-dot" aria-hidden="true"></div>
  <div class="timeline-content">
    <p class="card-kicker">{html.escape(item.get('degree', ''))}</p>
    <h3>{html.escape(title)}</h3>
    <p class="organization">{html.escape(detail)}</p>
  </div>
</article>"""


def render_timeline(profile: dict[str, Any], claims: list[dict[str, Any]], visuals: dict[str, dict[str, str]]) -> str:
    cards: list[tuple[str, str]] = []
    metrics = profile["portfolio"].get("metrics", [])
    public_education = [
        item
        for item in profile.get("education", [])
        if item["status"] in FACT_STATUSES and item["visibility"] == "public" and item["public_safe"] is True
    ]
    for item in public_education:
        cards.append((item.get("start", ""), render_education_card(item)))
    for claim in claims:
        if claim["category"] == "award":
            continue
        cards.append((claim.get("start", ""), render_claim_card(claim, metrics, visuals)))
    return "\n".join(card for _, card in sorted(cards, key=lambda item: item[0], reverse=True))


def render_skills(profile: dict[str, Any], public_claim_ids: set[str]) -> str:
    sections: list[str] = []
    for view_name, label in (("development", "Agent 开发"), ("algorithm", "Agent 算法")):
        groups = [
            group
            for group in profile["resume_views"][view_name].get("skills", [])
            if set(group["evidence_claim_ids"]) & public_claim_ids
        ]
        items = ""
        for group in groups:
            if group.get("text", "").strip():
                items += f'<section class="skill-block"><h3>核心技能</h3><p>{html.escape(group["text"])}</p></section>'
            else:
                items += (
                    f'<section class="skill-block"><h3>{html.escape(group["group"])}</h3><div>'
                    + "".join(f"<span>{html.escape(item)}</span>" for item in group.get("items", []))
                    + "</div></section>"
                )
        sections.append(f'<div class="skill-column"><h3>{label}</h3>{items}</div>')
    return "\n".join(sections)


def render_honors(claims: list[dict[str, Any]]) -> str:
    honors: list[str] = []
    for claim in claims:
        if claim["category"] == "award":
            honors.extend(item["text"] for item in claim["bullets"])
    return "\n".join(f"<li>{html.escape(item)}</li>" for item in honors)


def render_contact(candidate: dict[str, Any]) -> str:
    selected = set(candidate["contact_visibility"]["public"])
    contacts: list[str] = []
    if "location" in selected:
        contacts.append(f"<span>{html.escape(candidate['location'])}</span>")
    if "email" in selected:
        email = html.escape(candidate["email"], quote=True)
        contacts.append(f'<a href="mailto:{email}">{html.escape(candidate["email"])}</a>')
    if "phone" in selected:
        phone = html.escape(candidate["phone"], quote=True)
        contacts.append(f'<a href="tel:{phone}">{html.escape(candidate["phone"])}</a>')
    return "".join(contacts)


def detail_payload(profile: dict[str, Any], featured: list[dict[str, Any]], visuals: dict[str, dict[str, str]]) -> str:
    configured = profile.get("portfolio", {}).get("details", {})
    metrics = profile["portfolio"].get("metrics", [])
    details: dict[str, Any] = {}
    for claim in featured:
        claim_id = claim["id"]
        extra = configured.get(claim_id, {})
        claim_metrics = [
            {"value": metric["value"], "label": metric["label"]}
            for metric in metrics
            if metric.get("claim_id") == claim_id
        ]
        sections = extra.get("sections") or [{"title": "证据摘录", "items": [item["text"] for item in claim["bullets"]]}]
        links = extra.get("links", [])
        detail_metrics = [
            {"value": metric["value"], "label": metric["label"]}
            for metric in extra.get("metrics", [])
        ]
        details[claim_id] = {
            "category": CATEGORY_LABELS.get(claim["category"], claim["category"]),
            "date": date_range(claim),
            "title": claim["name"],
            "kicker": extra.get("kicker") or claim.get("role") or claim.get("organization", ""),
            "organization": claim.get("organization", ""),
            "summary": extra.get("summary") or claim.get("contribution", ""),
            "abstract": extra.get("abstract") or claim.get("limitation", ""),
            "visual": visuals.get(claim_id),
            "visual_caption": extra.get("visual_caption", ""),
            "metrics": detail_metrics or claim_metrics,
            "sections": sections,
            "star": extra.get("star", {}),
            "tradeoff": extra.get("tradeoff", ""),
            "tags": claim.get("tags", []),
            "links": links,
        }
    return json.dumps(details, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_portfolio(workspace: Path) -> Path:
    profile = require_valid_profile(workspace)
    output_parent = workspace / "outputs"
    output_parent.mkdir(parents=True, exist_ok=True)
    output_dir = output_parent / "portfolio"
    staging = Path(tempfile.mkdtemp(prefix=".portfolio-", dir=output_parent))
    assets = SKILL_DIR / "assets" / "portfolio"
    shutil.copy2(assets / "style.css", staging / "style.css")
    shutil.copy2(assets / "app.js", staging / "app.js")

    candidate = profile["candidate"]
    claim_map = claims_by_id(profile)
    public_claims = [
        claim
        for claim in profile["claims"]
        if claim["status"] in FACT_STATUSES and claim["visibility"] == "public" and claim["public_safe"] is True
    ]
    public_claim_ids = {claim["id"] for claim in public_claims}
    featured = [claim_map[claim_id] for claim_id in profile["portfolio"]["featured_claim_ids"]]
    visuals = copy_visuals(workspace, staging, profile)
    title = f"{candidate['name']} · {candidate['headline']}"
    data = {
        "title": html.escape(title, quote=True),
        "name": html.escape(candidate["name"]),
        "headline": html.escape(candidate["headline"]),
        "portfolio_label": html.escape(profile["portfolio"].get("label", "INTERVIEW PORTFOLIO · 2026")),
        "fixture_notice": html.escape(profile.get("fixture_notice", "")),
        "summary": html.escape(profile["portfolio"]["summary"]),
        "links": render_links(candidate),
        "metrics": render_metrics(profile["portfolio"].get("metrics", [])),
        "filters": render_filters(profile, featured),
        "timeline": render_timeline(profile, featured, visuals),
        "skills": render_skills(profile, public_claim_ids),
        "honors": render_honors(public_claims),
        "honors_hidden": "" if any(claim["category"] == "award" for claim in public_claims) else " hidden",
        "contact": render_contact(candidate),
        "details_json": detail_payload(profile, featured, visuals),
    }
    template = (assets / "index.html.template").read_text(encoding="utf-8")
    template = f"<!-- profile-sha256: {profile_digest(profile)} -->\n" + template
    for key, value in data.items():
        template = template.replace("{{" + key + "}}", value)
    template = "\n".join(line.rstrip() for line in template.splitlines()) + "\n"
    output = staging / "index.html"
    output.write_text(template, encoding="utf-8")
    backup = output_parent / ".portfolio-backup"
    if backup.exists():
        shutil.rmtree(backup)
    if output_dir.exists():
        os.replace(output_dir, backup)
    try:
        os.replace(staging, output_dir)
    except Exception:
        if backup.exists():
            os.replace(backup, output_dir)
        raise
    if backup.exists():
        shutil.rmtree(backup)
    return output_dir / "index.html"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a public-safe static Agent portfolio.")
    parser.add_argument("workspace")
    args = parser.parse_args()
    print(render_portfolio(workspace_path(args.workspace)))


if __name__ == "__main__":
    main()
