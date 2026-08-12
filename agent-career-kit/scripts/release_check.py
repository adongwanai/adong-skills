#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from pdfminer.high_level import extract_text

from common import SKILL_DIR, active_view_names, load_profile, workspace_path
from package_overleaf import package
from career_state import load_state
from render_career_dashboard import render_dashboard
from render_portfolio import render_portfolio
from render_resumes import render_resumes
from validate_workspace import validate_workspace


def require_tool(name: str, candidates: list[Path]) -> Path:
    direct = shutil.which(name)
    if direct:
        return Path(direct)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError(f"missing required release tool: {name}")


def find_tectonic() -> Path:
    candidates = sorted((Path.home() / ".codex" / "plugins" / "cache" / "openai-bundled" / "latex").glob("*/bin/tectonic"))
    return require_tool("tectonic", candidates)


def find_pdftoppm() -> Path:
    candidates = [
        Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "bin" / "override" / "pdftoppm",
        Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "bin" / "fallback" / "pdftoppm",
    ]
    return require_tool("pdftoppm", candidates)


def find_node() -> Path:
    candidates = [Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "bin" / "node"]
    return require_tool("node", candidates)


def find_playwright() -> Path:
    env_path = os.environ.get("PLAYWRIGHT_INDEX_MJS")
    if env_path:
        return Path(env_path)
    path = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node" / "node_modules" / "playwright" / "index.mjs"
    if path.exists():
        return path
    raise RuntimeError("missing Playwright module; set PLAYWRIGHT_INDEX_MJS")


def find_chrome() -> Path:
    env_path = os.environ.get("CHROME_PATH")
    if env_path:
        return Path(env_path)
    mac_chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    direct = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    if direct:
        return Path(direct)
    if mac_chrome.exists():
        return mac_chrome
    raise RuntimeError("missing Chrome/Chromium; set CHROME_PATH")


def compile_resumes(workspace: Path, tectonic: Path, view_names: list[str]) -> None:
    for view_name in view_names:
        resume_dir = workspace / "outputs" / "resumes" / view_name
        subprocess.run(
            [str(tectonic), "-X", "compile", "--outdir", str(resume_dir), "--outfmt", "pdf", "--print", "--untrusted", "main.tex"],
            cwd=resume_dir,
            check=True,
            capture_output=True,
            text=True,
        )


def compile_overleaf_packages(workspace: Path, tectonic: Path, view_names: list[str]) -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for view_name in view_names:
            extracted = root / view_name
            extracted.mkdir()
            archive_path = workspace / "outputs" / "resumes" / view_name / "overleaf.zip"
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extracted)
            subprocess.run(
                [str(tectonic), "-X", "compile", "--outdir", str(extracted), "--outfmt", "pdf", "--print", "--untrusted", "main.tex"],
                cwd=extracted,
                check=True,
                capture_output=True,
                text=True,
            )


def validate_with_second_pdf_parser(workspace: Path, profile: dict, view_names: list[str]) -> None:
    claims = {claim["id"]: claim for claim in profile["claims"]}
    for view_name in view_names:
        pdf_path = workspace / "outputs" / "resumes" / view_name / "main.pdf"
        text = extract_text(str(pdf_path))
        expected = [
            profile["candidate"]["name"],
            profile["resume_views"][view_name]["headline"],
            claims[profile["resume_views"][view_name]["claim_ids"][0]]["name"],
        ]
        if profile.get("fixture_notice", "").strip():
            expected.append(profile["fixture_notice"])
        missing = [value for value in expected if value not in text]
        if missing:
            raise RuntimeError(f"{view_name} PDF failed pdfminer text validation: {missing}")


def render_pdf_pages(workspace: Path, output_dir: Path, view_names: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for view_name in view_names:
        pdf_path = workspace / "outputs" / "resumes" / view_name / "main.pdf"
        if sys.platform == "darwin":
            swift = require_tool("swift", [])
            renderer = SKILL_DIR / "scripts" / "render_pdf_pages.swift"
            subprocess.run([str(swift), str(renderer), str(pdf_path), str(output_dir / view_name)], check=True)
        else:
            subprocess.run(
                [str(find_pdftoppm()), "-png", "-r", "150", str(pdf_path), str(output_dir / view_name)],
                check=True,
            )


def browser_check(workspace: Path, output_dir: Path, node: Path, playwright: Path, chrome: Path, profile: dict) -> None:
    portfolio = (workspace / "outputs" / "portfolio" / "index.html").resolve().as_uri()
    claims = {claim["id"]: claim for claim in profile["claims"]}
    expected_project = claims[profile["portfolio"]["featured_claim_ids"][0]]["name"]
    expected_metrics = len(profile["portfolio"]["metrics"])
    expected_cards = len(profile["portfolio"]["featured_claim_ids"])
    expected_images = len(profile["portfolio"]["visuals"])
    expected_hero = profile["portfolio"].get("label", "INTERVIEW PORTFOLIO · 2026")
    expected_notice = profile.get("fixture_notice", "").strip()
    expected_resume_views = profile.get("portfolio", {}).get("resume_downloads", active_view_names(profile))
    code = f"""
import {{ chromium }} from {str(playwright)!r};
const browser = await chromium.launch({{ headless: true, executablePath: {str(chrome)!r} }});
const url = {portfolio!r};
const expectedProject = {expected_project!r};
const expectedMetrics = {expected_metrics};
const expectedCards = {expected_cards};
const expectedImages = {expected_images};
const expectedHero = {json.dumps(expected_hero, ensure_ascii=False)};
const expectedNotice = {json.dumps(expected_notice, ensure_ascii=False)};
const expectedResumeViews = {json.dumps(expected_resume_views, ensure_ascii=False)};
for (const [name, viewport] of Object.entries({{ desktop: {{ width: 1440, height: 1200 }}, mobile: {{ width: 390, height: 1200 }} }})) {{
  const page = await browser.newPage({{ viewport }});
  await page.goto(url);
  const result = await page.evaluate(() => {{
    const text = document.body.innerText;
    const html = document.documentElement.outerHTML;
    const broken = [...document.images].filter((img) => img.hasAttribute("src") && (!img.complete || img.naturalWidth === 0)).map((img) => img.getAttribute("src"));
    const widthOk = document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1;
    return {{
      text,
      html,
      broken,
      widthOk,
      metrics: document.querySelectorAll(".metric-card").length,
      cards: document.querySelectorAll(".timeline-card").length,
      images: document.querySelectorAll(".card-visual img").length,
      resumeHrefs: [...document.querySelectorAll("a")].map((a) => a.getAttribute("href") || "").filter((href) => href.includes("../resumes/")),
    }};
  }});
  if (!result.text.includes(expectedHero)) throw new Error(`${{name}}: missing hero`);
  if (expectedNotice && !result.text.includes(expectedNotice)) throw new Error(`${{name}}: missing fixture disclosure`);
  if (!result.text.includes("成长时间轴")) throw new Error(`${{name}}: missing timeline`);
  if (!result.text.includes(expectedProject)) throw new Error(`${{name}}: missing featured project`);
  if (result.metrics !== expectedMetrics) throw new Error(`${{name}}: expected ${{expectedMetrics}} metrics, got ${{result.metrics}}`);
  if (result.cards < expectedCards) throw new Error(`${{name}}: expected timeline cards, got ${{result.cards}}`);
  if (result.images !== expectedImages) throw new Error(`${{name}}: expected ${{expectedImages}} project visuals, got ${{result.images}}`);
  if (result.broken.length) throw new Error(`${{name}}: broken images ${{result.broken.join(", ")}}`);
  if (!result.widthOk) throw new Error(`${{name}}: horizontal overflow`);
  for (const view of expectedResumeViews) {{
    if (!result.resumeHrefs.some((href) => href.includes(`../resumes/${{view}}/main.pdf`))) throw new Error(`${{name}}: missing ${{view}} resume link`);
  }}
  await page.locator('.timeline-card[data-detail-id]').first().click();
  const detail = await page.evaluate(() => {{
    const modal = document.querySelector('[data-detail-modal]');
    return {{
      open: !modal.hidden && modal.getAttribute('aria-hidden') === 'false',
      title: document.querySelector('[data-detail-title]').textContent.trim(),
      sections: document.querySelector('[data-detail-sections]').children.length,
      stars: document.querySelector('[data-detail-star]').children.length,
      closeFocused: document.activeElement?.classList.contains('detail-close'),
    }};
  }});
  if (!detail.open || !detail.title) throw new Error(`${{name}}: project detail did not open`);
  if (detail.sections < 1) throw new Error(`${{name}}: project detail has no evidence sections`);
  if (detail.stars < 1) throw new Error(`${{name}}: project detail has no STAR review`);
  if (!detail.closeFocused) throw new Error(`${{name}}: project detail close control is not focused`);
  for (let index = 0; index < 3; index += 1) {{
    await page.keyboard.press('Tab');
    const focusStayedInDialog = await page.evaluate(() => document.querySelector('[data-detail-modal]').contains(document.activeElement));
    if (!focusStayedInDialog) throw new Error(`${{name}}: keyboard focus escaped project detail`);
  }}
  await page.waitForTimeout(320);
  await page.screenshot({{ path: {str(output_dir)!r} + `/portfolio-${{name}}-detail.png`, fullPage: false }});
  await page.click('.detail-close');
  if ((await page.locator('[data-detail-modal]').getAttribute('hidden')) === null) throw new Error(`${{name}}: project detail did not close`);
  const cards = page.locator('.timeline-card');
  for (let index = 0; index < await cards.count(); index += 1) {{
    await cards.nth(index).scrollIntoViewIfNeeded();
    await page.waitForTimeout(40);
  }}
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({{ path: {str(output_dir)!r} + `/portfolio-${{name}}.png`, fullPage: true }});
  const filterButtons = page.locator('[data-filter]:not([data-filter="all"])');
  for (let index = 0; index < await filterButtons.count(); index += 1) {{
    await filterButtons.nth(index).click();
    const filterResult = await page.evaluate(() => {{
      const active = document.querySelector('[data-filter][aria-pressed="true"]');
      const allowed = new Set((active.dataset.categories || '').split(' ').filter(Boolean));
      const visible = [...document.querySelectorAll('.timeline-card:not([hidden])')];
      return {{ count: visible.length, valid: visible.every((card) => allowed.has(card.dataset.category)) }};
    }});
    if (!filterResult.count || !filterResult.valid) throw new Error(`${{name}}: timeline filter returned invalid cards`);
  }}
  await page.close();
}}
await browser.close();
"""
    subprocess.run([str(node), "--input-type=module", "-e", code], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a cold release check for an Agent Career Kit workspace.")
    parser.add_argument("workspace")
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args()

    workspace = workspace_path(args.workspace)
    profile = load_profile(workspace)
    view_names = active_view_names(profile)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else workspace / "outputs" / "qa"
    node = find_node()
    render_resumes(workspace)
    render_portfolio(workspace)
    render_dashboard(workspace, load_state(workspace))
    tectonic = find_tectonic()
    compile_resumes(workspace, tectonic, view_names)
    package(workspace)
    compile_overleaf_packages(workspace, tectonic, view_names)
    errors = validate_workspace(workspace, require_artifacts=True, require_dashboard=True)
    if errors:
        raise SystemExit("workspace validation failed:\n- " + "\n- ".join(errors))
    validate_with_second_pdf_parser(workspace, profile, view_names)
    render_pdf_pages(workspace, output_dir, view_names)
    browser_check(workspace, output_dir, node, find_playwright(), find_chrome(), profile)
    print(f"release OK: {workspace}")
    print(f"visual QA: {output_dir}")


if __name__ == "__main__":
    main()
