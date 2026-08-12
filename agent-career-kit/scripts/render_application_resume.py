#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from common import require_valid_profile, validate_application_request, workspace_path
from init_application import render_application_packet
from render_resumes import LATEX_ASSETS, render_document


def render_application(workspace: Path, request_path: Path, final: bool) -> Path:
    profile = require_valid_profile(workspace)
    absolute_request = request_path.expanduser().resolve()
    applications_root = (workspace / "outputs" / "applications").resolve()
    if applications_root not in absolute_request.parents:
        raise ValueError("投递请求必须位于工作区 outputs/applications/ 下")
    request = json.loads(absolute_request.read_text(encoding="utf-8"))
    errors = validate_application_request(request, profile, workspace)
    if errors:
        raise ValueError("投递请求无效：\n- " + "\n- ".join(errors))
    if final and request["approval"]["status"] != "approved":
        raise ValueError("最终投递快照必须先由用户确认；当前只能生成审阅草稿")
    (absolute_request.parent / "application-packet.md").write_text(
        render_application_packet(request, profile), encoding="utf-8"
    )

    snapshot = copy.deepcopy(profile)
    view_name = request["source_view"]
    snapshot_view = snapshot["resume_views"][view_name]
    snapshot_view.update(
        {
            "headline": request.get("headline") or snapshot_view["headline"],
            "summary": request.get("summary", ""),
            "summary_claim_ids": request.get("summary_claim_ids", []),
            "claim_ids": request["claim_ids"],
            "bullet_ids_by_claim": request["bullet_ids_by_claim"],
            "skills": request.get("skills", []),
        }
    )
    overrides = request.get("bullet_overrides", {})
    for claim in snapshot["claims"]:
        for bullet in claim.get("bullets", []):
            if bullet["id"] in overrides:
                bullet["text"] = overrides[bullet["id"]]["text"]
    output_dir = absolute_request.parent / ("resume" if final else "resume-draft")
    output_dir.mkdir(parents=True, exist_ok=True)
    for asset in LATEX_ASSETS:
        shutil.copy2(asset, output_dir / asset.name)
    photo = profile["candidate"].get("photo", "").strip()
    if photo:
        shutil.copy2(workspace / photo, output_dir / Path(photo).name)

    request_digest = hashlib.sha256(absolute_request.read_bytes()).hexdigest()
    tex = render_document(snapshot, view_name).replace(
        "% Layout based", f"% application-request-sha256: {request_digest}\n% Layout based", 1
    )
    tex = tex.replace(
        r"\ResumeName",
        rf"\hypersetup{{pdfkeywords={{application-request-sha256:{request_digest}}}}}" + "\n" + r"\ResumeName",
        1,
    )
    output = output_dir / "main.tex"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output_dir, delete=False) as handle:
        handle.write(tex)
        temporary = Path(handle.name)
    os.replace(temporary, output)
    return output


def compile_application(tex_path: Path) -> Path:
    tectonic = shutil.which("tectonic")
    if not tectonic:
        candidates = sorted(
            (Path.home() / ".codex" / "plugins" / "cache" / "openai-bundled" / "latex").glob("*/bin/tectonic")
        )
        if candidates:
            tectonic = str(candidates[-1])
    if not tectonic:
        raise ValueError("未找到 Tectonic；请安装 Tectonic/XeLaTeX，或先只生成 TeX 审阅稿")
    result = subprocess.run(
        [tectonic, "-X", "compile", "--outdir", str(tex_path.parent), "--outfmt", "pdf", tex_path.name],
        cwd=tex_path.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise ValueError("PDF 编译失败；请检查生成的 main.tex、字体与 Tectonic/XeLaTeX 环境")
    pdf_path = tex_path.with_suffix(".pdf")
    tex = tex_path.read_text(encoding="utf-8")
    digest_match = re.search(r"^% application-request-sha256: ([0-9a-f]{64})$", tex, flags=re.MULTILINE)
    headline_match = re.search(r"^% view-headline: (.+)$", tex, flags=re.MULTILINE)
    pages_match = re.search(r"^% expected-pages: (\d+)$", tex, flags=re.MULTILINE)
    if not digest_match or not headline_match or not pages_match:
        raise ValueError("投递 TeX 缺少 request digest、岗位标题或页数标记")
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("PDF 验收需要 pdfplumber") from None
    with pdfplumber.open(pdf_path) as pdf:
        expected_pages = int(pages_match.group(1))
        if len(pdf.pages) != expected_pages:
            raise ValueError(f"投递 PDF 应为 {expected_pages} 页，实际为 {len(pdf.pages)} 页")
        for page in pdf.pages:
            if abs(float(page.width) - 595.28) > 2 or abs(float(page.height) - 841.89) > 2:
                raise ValueError("投递 PDF 不是 A4")
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if headline_match.group(1) not in text:
            raise ValueError("投递 PDF 正文缺少目标岗位标题")
        keywords = str(pdf.metadata.get("Keywords", ""))
        if digest_match.group(1) not in keywords:
            raise ValueError("投递 PDF 元数据与当前 application request 不一致")
    return pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description="从已映射的 JD 投递包生成简历快照。")
    parser.add_argument("workspace")
    parser.add_argument("request", type=Path)
    parser.add_argument("--final", action="store_true", help="只允许已确认的投递请求生成最终稿。")
    parser.add_argument("--compile", action="store_true", help="使用 Tectonic 将快照编译为 PDF。")
    args = parser.parse_args()
    try:
        output = render_application(workspace_path(args.workspace), args.request, args.final)
        pdf = compile_application(output) if args.compile else None
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"投递简历生成失败：\n{error}") from None
    print(output)
    if pdf:
        print(pdf)


if __name__ == "__main__":
    main()
