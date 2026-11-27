from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "hf-daily-papers/2.0 (+https://github.com/adongwanai/hf-daily-papers)"
BEIJING_TZ = timezone(timedelta(hours=8))

TOPIC_ORDER = [
    "LLM",
    "Multimodal",
    "VisionGen",
    "RLPostTraining",
    "EfficiencySystems",
    "EmbodiedRobotics",
    "DataEvalSurvey",
    "ScienceOther",
]

TOPIC_META: dict[str, dict[str, str]] = {
    "LLM": {"label_zh": "大语言模型", "label_en": "Language Models", "code": "LLM"},
    "Multimodal": {"label_zh": "多模态理解", "label_en": "Multimodal", "code": "VLM"},
    "VisionGen": {"label_zh": "视觉与生成", "label_en": "Vision & Generation", "code": "GEN"},
    "RLPostTraining": {"label_zh": "强化学习与后训练", "label_en": "RL & Post-Training", "code": "RL"},
    "EfficiencySystems": {"label_zh": "推理与系统效率", "label_en": "Systems & Efficiency", "code": "SYS"},
    "EmbodiedRobotics": {"label_zh": "具身与机器人", "label_en": "Embodied & Robotics", "code": "BOT"},
    "DataEvalSurvey": {"label_zh": "数据 · 评测 · 综述", "label_en": "Benchmarks & Surveys", "code": "EVAL"},
    "ScienceOther": {"label_zh": "科学计算与其他", "label_en": "AI4Science & Other", "code": "SCI"},
}

ZH_LABEL_TO_TOPIC: dict[str, str] = {
    "大语言模型": "LLM",
    "多模态": "Multimodal",
    "多模态理解": "Multimodal",
    "视觉与生成": "VisionGen",
    "强化学习与后训练": "RLPostTraining",
    "效率与系统": "EfficiencySystems",
    "推理与系统效率": "EfficiencySystems",
    "具身与机器人": "EmbodiedRobotics",
    "数据 / 评测 / 综述": "DataEvalSurvey",
    "数据 · 评测 · 综述": "DataEvalSurvey",
    "数据/评测/综述": "DataEvalSurvey",
    "科学计算与其他": "ScienceOther",
}


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def project_root() -> Path:
    ws = os.getenv("HF_PAPER_WORKSPACE")
    if ws:
        return Path(ws).expanduser().resolve()
    return skill_root()


def load_site_config() -> dict[str, Any]:
    for base in (project_root(), skill_root()):
        cfg_path = base / "site.config.yaml"
        if cfg_path.exists():
            return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return {}


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        }
    )
    return session


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def today_beijing() -> str:
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(obj: Any, path: str | Path, compact: bool = False) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(obj, ensure_ascii=False, indent=2)
    target.write_text(text + "\n", encoding="utf-8")


def normalize_space(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def load_dotenv(path: str | Path | None = None) -> None:
    env_path = Path(path) if path else project_root() / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def normalize_topic(topic: str | None) -> str:
    if not topic:
        return "ScienceOther"
    cleaned = topic.strip()
    if cleaned in TOPIC_ORDER:
        return cleaned
    if cleaned in ZH_LABEL_TO_TOPIC:
        return ZH_LABEL_TO_TOPIC[cleaned]
    for zh_key, code in ZH_LABEL_TO_TOPIC.items():
        if zh_key in cleaned:
            return code
    return "ScienceOther"


def safe_slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-")
    return value or "item"
