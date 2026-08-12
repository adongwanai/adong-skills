#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import zipfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from common import workspace_path


SUPPORTED_SUFFIXES = {".pdf", ".docx", ".md", ".txt", ".json", ".html", ".htm", ".tex"}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.parts.append(value)


def extract_pdf(path: Path) -> tuple[str, int]:
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("读取 PDF 需要 pdfplumber") from None
    with pdfplumber.open(path) as pdf:
        pages = [page.extract_text(x_tolerance=2, y_tolerance=3) or "" for page in pdf.pages]
    text = "\n\n".join(value.strip() for value in pages if value.strip())
    if not text:
        raise ValueError(f"PDF 没有可提取文字，可能需要 OCR: {path.name}")
    return text, len(pages)


def extract_docx(path: Path) -> tuple[str, int]:
    try:
        with zipfile.ZipFile(path) as archive:
            document = archive.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError):
        raise ValueError(f"Word 文件损坏或格式不受支持: {path.name}") from None
    root = ElementTree.fromstring(document)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(namespace + "p"):
        parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == namespace + "t" and node.text:
                parts.append(node.text)
            elif node.tag == namespace + "tab":
                parts.append("\t")
        value = "".join(parts).strip()
        if value:
            paragraphs.append(value)
    text = "\n".join(paragraphs)
    if not text:
        raise ValueError(f"Word 文件没有可提取文字: {path.name}")
    return text, 0


def extract_text(path: Path) -> tuple[str, int]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix == ".docx":
        return extract_docx(path)
    raw = path.read_text(encoding="utf-8-sig")
    if suffix in {".html", ".htm"}:
        parser = TextExtractor()
        parser.feed(raw)
        raw = "\n".join(parser.parts)
    text = re.sub(r"\n{3,}", "\n\n", raw).strip()
    if not text:
        raise ValueError(f"文件没有可提取文字: {path.name}")
    return text, 0


def safe_name(path: Path, digest: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", path.stem).strip("-.") or "material"
    return f"{stem}-{digest[:8]}{path.suffix.lower()}"


def import_materials(workspace: Path, paths: list[Path], kind: str) -> list[dict]:
    workspace = workspace.resolve()
    manifest_path = workspace / "source-materials" / "materials.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = manifest_path.parent / ".materials.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {"schema_version": 1, "materials": []}
        known = {item["sha256"]: item for item in manifest["materials"]}
        imported: list[dict] = []
        for raw_path in paths:
            source = raw_path.expanduser().resolve()
            if not source.is_file():
                raise ValueError(f"材料不存在: {source}")
            if source.suffix.lower() not in SUPPORTED_SUFFIXES:
                raise ValueError(f"不支持的材料格式: {source.suffix or '<无扩展名>'}")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest in known:
                imported.append(known[digest])
                continue
            target_dir = workspace / ("jd-bank" if kind == "jd" else "source-materials")
            target_name = safe_name(source, digest)
            target = target_dir / target_name
            target_dir.mkdir(parents=True, exist_ok=True)
            if source != target:
                shutil.copy2(source, target)
            text, page_count = extract_text(target)
            extracted = workspace / "source-materials" / "extracted" / f"{Path(target_name).stem}.txt"
            extracted.parent.mkdir(parents=True, exist_ok=True)
            extracted.write_text(text + "\n", encoding="utf-8")
            item = {
                "id": f"material-{len(manifest['materials']) + 1:03d}",
                "kind": kind,
                "original_name": source.name,
                "stored_path": target.relative_to(workspace).as_posix(),
                "extracted_path": extracted.relative_to(workspace).as_posix(),
                "sha256": digest,
                "imported_at": date.today().isoformat(),
                "characters": len(text),
                "pages": page_count,
                "status": "ready_for_agent",
            }
            manifest["materials"].append(item)
            known[digest] = item
            imported.append(item)
        temporary = manifest_path.with_name(f".{manifest_path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, manifest_path)
        render_intake_materials(workspace, manifest["materials"])
        return imported


def render_intake_materials(workspace: Path, materials: list[dict]) -> Path:
    intake = workspace / "intake.md"
    current = intake.read_text(encoding="utf-8") if intake.is_file() else "# 开始使用\n"
    marker = "## 已导入材料"
    before = current.split(marker, 1)[0].rstrip()
    rows = [
        "",
        marker,
        "",
        "| ID | 类型 | 原文件 | 提取文本 | 状态 |",
        "| --- | --- | --- | --- | --- |",
    ]
    rows.extend(
        f"| {item['id']} | {item['kind']} | `{item['stored_path']}` | `{item['extracted_path']}` | 已提取，等待 Agent 结构化 |"
        for item in materials
    )
    rows.extend(("", "下一步：Agent 读取提取文本，生成岗位定位、候选人档案和首版内容。", ""))
    intake.write_text(before + "\n" + "\n".join(rows), encoding="utf-8")
    return intake


def main() -> None:
    parser = argparse.ArgumentParser(description="导入简历、JD 或项目材料，并生成 Agent 可直接读取的规范文本。")
    parser.add_argument("workspace")
    parser.add_argument("materials", nargs="+", type=Path)
    parser.add_argument("--kind", choices=("resume", "jd", "project", "interview", "other"), default="other")
    args = parser.parse_args()
    try:
        imported = import_materials(workspace_path(args.workspace), args.materials, args.kind)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(f"材料导入失败：\n{error}") from None
    for item in imported:
        print(f"{item['id']}: {item['extracted_path']}")
    print("下一步：读取以上提取文本，更新候选人档案；用户不需要编辑 JSON。")


if __name__ == "__main__":
    main()
