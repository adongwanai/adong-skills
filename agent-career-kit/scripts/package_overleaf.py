#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import tempfile
import zipfile
from pathlib import Path

from common import RENDERER_VERSION, VIEW_NAMES, profile_digest, require_valid_profile, workspace_path
from render_resumes import LATEX_ASSETS, render_document, selected_views


ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
NOTICE = """Agent Career Kit resume renderer
Layout source: LLM-Resume-Template by @adongwanai
https://github.com/adongwanai/LLM-Resume-Template/commit/9673d5baeec3d8c54611d0e0d1040495cbca8989
License notice: CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/
The included resume-photo.cls differs only by trailing-whitespace normalization from that reviewed commit; its macros and layout are unchanged. Its header identifies Feng Kaiyu as the class author, and the upstream README credits https://github.com/liweitianux/resume.
Agent Career Kit modifies the surrounding renderer: main.tex and all candidate text are generated dynamically from the candidate workspace.
"""


def add_text(archive: zipfile.ZipFile, name: str, text: str) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, text.encode("utf-8"))


def add_binary(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    archive.writestr(info, data)


def package(workspace: Path, view_names: list[str] | None = None) -> list[Path]:
    profile = require_valid_profile(workspace)
    view_names = selected_views(profile, view_names)
    digest = profile_digest(profile)
    outputs: list[Path] = []
    for view_name in view_names:
        resume_dir = workspace / "outputs" / "resumes" / view_name
        tex_path = resume_dir / "main.tex"
        if not tex_path.is_file():
            raise ValueError(f"render resume before packaging: {tex_path}")
        class_path = resume_dir / LATEX_ASSETS[0].name
        if not class_path.is_file():
            raise ValueError(f"render resume before packaging: {class_path}")
        photo = profile["candidate"].get("photo", "").strip()
        photo_name = Path(photo).name if photo else ""
        photo_path = resume_dir / photo_name if photo else None
        if photo and (not photo_path or not photo_path.is_file()):
            raise ValueError(f"render resume before packaging: {photo_path}")
        tex = tex_path.read_text(encoding="utf-8")
        expected = render_document(profile, view_name)
        if tex != expected:
            raise ValueError(f"stale resume: rerender before packaging: {tex_path}")
        class_text = class_path.read_text(encoding="utf-8")
        if class_text != LATEX_ASSETS[0].read_text(encoding="utf-8"):
            raise ValueError(f"stale resume class: rerender before packaging: {class_path}")
        zip_path = resume_dir / "overleaf.zip"
        manifest = json.dumps(
            {"profile_sha256": digest, "renderer_version": RENDERER_VERSION, "view": view_name},
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ) + "\n"
        with tempfile.NamedTemporaryFile(dir=resume_dir, delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w") as archive:
            add_text(archive, "main.tex", tex)
            add_text(archive, LATEX_ASSETS[0].name, class_text)
            if photo_path:
                add_binary(archive, photo_name, photo_path.read_bytes())
            add_text(archive, "NOTICE.txt", NOTICE)
            add_text(archive, "manifest.json", manifest)
        os.replace(temporary, zip_path)
        outputs.append(zip_path)
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Create deterministic Overleaf ZIP files.")
    parser.add_argument("workspace")
    parser.add_argument("--view", action="append", choices=VIEW_NAMES, dest="views")
    args = parser.parse_args()
    try:
        outputs = package(workspace_path(args.workspace), args.views)
    except ValueError as error:
        raise SystemExit(f"Overleaf 打包失败：\n{error}") from None
    print("\n".join(str(path) for path in outputs))


if __name__ == "__main__":
    main()
