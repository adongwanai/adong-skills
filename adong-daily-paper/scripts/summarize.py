from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests

from _common import (
    load_dotenv,
    load_site_config,
    normalize_space,
    normalize_topic,
    now_iso,
    project_root,
    read_json,
    skill_root,
    write_json,
)


class SummarizeFailed(RuntimeError):
    pass


def render_summarize_prompt(arxiv_id: str, title: str, abstract: str) -> str:
    sroot = skill_root()
    template = (sroot / "prompts" / "summarize_paper.md").read_text(encoding="utf-8")
    taxonomy = (sroot / "references" / "topic_taxonomy.md").read_text(encoding="utf-8")
    return (
        template.replace("{TAXONOMY_RULES}", taxonomy)
        .replace("{ARXIV_ID}", arxiv_id)
        .replace("{TITLE}", title)
        .replace("{ABSTRACT}", abstract)
    )


def _strip_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_first_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if char == "\\" and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def parse_json_loose(text: str) -> dict[str, Any]:
    cleaned = _strip_fence(text)
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        block = _extract_first_json_object(cleaned)
        if not block:
            raise SummarizeFailed("model did not return a JSON object")
        try:
            obj = json.loads(block)
        except json.JSONDecodeError as exc:
            raise SummarizeFailed(f"invalid JSON from model: {exc}") from exc
    if not isinstance(obj, dict):
        raise SummarizeFailed("model JSON is not an object")
    return obj


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [normalize_space(str(item)) for item in value if normalize_space(str(item))]
    text = str(value).strip()
    if not text:
        return []
    lines = re.split(r"\n+|(?:^|\s)(?:\d+[\.\、]|[-*])\s+", text)
    items = [line.strip(" -•\t\r\n") for line in lines if line.strip(" -•\t\r\n")]
    return items or [text]


def _normalize_summary(arxiv_id: str, raw: dict[str, Any], focus_keywords: list[str]) -> dict[str, Any]:
    score = raw.get("insight_score")
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 3
    score = min(5, max(1, score))
    extra = normalize_space(str(raw.get("extra_commentary") or "")) or None
    if score < 4:
        extra = None
    ideas = _normalize_string_list(raw.get("ideas_and_insights"))
    directions = _normalize_string_list(raw.get("new_paper_directions"))
    tags = _normalize_string_list(raw.get("tags"))[:4]
    cap = 3 if score >= 4 else 2
    haystack = " ".join(
        [
            str(raw.get("title_zh") or ""),
            str(raw.get("tldr") or ""),
            str(raw.get("method") or ""),
            " ".join(tags),
        ]
    ).lower()
    focus_match = any(kw.lower() in haystack for kw in focus_keywords) if focus_keywords else False

    return {
        "arxiv_id": arxiv_id,
        "title_zh": normalize_space(str(raw.get("title_zh") or "")),
        "topic": normalize_topic(raw.get("topic")),
        "tags": tags,
        "tldr": normalize_space(str(raw.get("tldr") or "")),
        "problem": normalize_space(str(raw.get("problem") or "")),
        "method": normalize_space(str(raw.get("method") or "")),
        "contribution": normalize_space(str(raw.get("contribution") or "")),
        "result": normalize_space(str(raw.get("result") or "")) or None,
        "insight_score": score,
        "focus_match": focus_match,
        "extra_commentary": extra,
        "plain_explanation": normalize_space(str(raw.get("plain_explanation") or "")),
        "ideas_and_insights": ideas[:cap],
        "new_paper_directions": directions[:cap],
        "summarize_failed": False,
        "summarize_error": None,
    }


def fallback_summary(paper: dict[str, Any], error: str) -> dict[str, Any]:
    return {
        "arxiv_id": paper.get("arxiv_id"),
        "title_zh": paper.get("title") or "",
        "topic": "ScienceOther",
        "tags": paper.get("ai_keywords", [])[:3],
        "tldr": paper.get("ai_summary") or paper.get("title") or "",
        "problem": "",
        "method": "",
        "contribution": "",
        "result": None,
        "insight_score": 2,
        "focus_match": False,
        "extra_commentary": None,
        "plain_explanation": "",
        "ideas_and_insights": [],
        "new_paper_directions": [],
        "summarize_failed": True,
        "summarize_error": error,
    }


def _normalized_openai_endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if "api.deepseek.com" in base:
        return f"{base}/chat/completions"
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/chat/completions"


def call_llm(prompt: str, model: str, provider: str, max_tokens: int = 1800) -> str:
    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise SummarizeFailed("missing ANTHROPIC_API_KEY")
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    api_key = os.getenv("HF_DAILY_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = (
        os.getenv("HF_DAILY_LLM_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.deepseek.com"
    )
    if not api_key:
        raise SummarizeFailed("missing HF_DAILY_LLM_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY")
    endpoint = _normalized_openai_endpoint(base_url)
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=95)
    if resp.status_code == 400 and "max_tokens" in resp.text:
        payload.pop("max_tokens", None)
        payload["max_completion_tokens"] = max_tokens
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=95)
    if resp.status_code >= 400:
        raise SummarizeFailed(f"HTTP {resp.status_code}: {resp.text[:240]}")
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def summarize_one(
    paper: dict[str, Any],
    model: str,
    provider: str,
    max_retries: int,
    focus_keywords: list[str],
) -> dict[str, Any]:
    abstract = paper.get("abstract") or paper.get("hf_brief") or ""
    if not abstract.strip():
        return fallback_summary(paper, "missing abstract")
    prompt = render_summarize_prompt(
        arxiv_id=str(paper.get("arxiv_id") or ""),
        title=str(paper.get("title") or ""),
        abstract=abstract,
    )
    last_error = "unknown error"
    for attempt in range(max_retries + 1):
        try:
            text = call_llm(prompt, model=model, provider=provider)
            parsed = parse_json_loose(text)
            return _normalize_summary(paper["arxiv_id"], parsed, focus_keywords)
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
    return fallback_summary(paper, last_error)


def synthesize_daily_brief(items: list[dict[str, Any]], model: str, provider: str) -> str:
    valid = [x for x in items if not x.get("summarize_failed") and x.get("tldr")]
    if not valid:
        return ""
    bullet_lines = [f"- [{x['topic']}] {x['title_zh']}: {x['tldr']}" for x in valid[:25]]
    prompt = (
        "请根据以下今日收录论文列表，用 2 句平实、克制的中文（合计 90 字以内）概括今日论文最集中的 2-3 个具体研究问题与代表性路线。"
        "禁止使用感叹号、Emoji 或“百花齐放”“里程碑”“不仅…而且…”等套话，直接给事实判断：\n\n"
        + "\n".join(bullet_lines)
    )
    try:
        return normalize_space(call_llm(prompt, model=model, provider=provider, max_tokens=300)).strip('"“”')
    except Exception:
        return ""


def resolve_provider(requested: str) -> str:
    if requested != "auto":
        return requested
    env_p = os.getenv("HF_DAILY_LLM_PROVIDER", "").lower()
    if env_p == "anthropic":
        return "anthropic"
    if os.getenv("HF_DAILY_LLM_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "openai"


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Summarize papers.json with incremental resume.")
    parser.add_argument("--in", dest="infile", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--existing", default=None, help="Existing summaries.json or daily/{date}.json for resume.")
    parser.add_argument("--model", default=os.getenv("HF_DAILY_LLM_MODEL", "deepseek-chat"))
    parser.add_argument("--provider", choices=["auto", "openai", "anthropic"], default="auto")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--max-retries", type=int, default=2)
    args = parser.parse_args()

    cfg = load_site_config()
    focus_keywords = cfg.get("focus_keywords") or []
    papers_payload = read_json(args.infile)
    papers = papers_payload.get("papers", [])
    provider = resolve_provider(args.provider)

    reused_map: dict[str, dict[str, Any]] = {}
    for candidate in (args.existing, args.out):
        if candidate and Path(candidate).exists():
            try:
                old = read_json(candidate)
                old_items = old.get("items") or old.get("papers") or []
                for it in old_items:
                    aid = it.get("arxiv_id")
                    if aid and not it.get("summarize_failed") and it.get("tldr"):
                        reused_map[aid] = it
            except Exception:
                pass

    results: list[dict[str, Any] | None] = [None] * len(papers)
    todo_indices: list[int] = []
    for idx, paper in enumerate(papers):
        aid = paper.get("arxiv_id")
        if aid in reused_map:
            results[idx] = reused_map[aid]
        else:
            todo_indices.append(idx)

    if todo_indices:
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
            futs = {
                executor.submit(
                    summarize_one,
                    papers[i],
                    args.model,
                    provider,
                    args.max_retries,
                    focus_keywords,
                ): i
                for i in todo_indices
            }
            for fut in as_completed(futs):
                i = futs[fut]
                try:
                    results[i] = fut.result()
                except Exception as exc:
                    results[i] = fallback_summary(papers[i], str(exc))

    final_items = [r for r in results if r is not None]
    daily_brief = synthesize_daily_brief(final_items, model=args.model, provider=provider)
    out_payload = {
        "date": papers_payload.get("date"),
        "summarized_at": now_iso(),
        "model": args.model,
        "provider": provider,
        "daily_brief": daily_brief,
        "items": final_items,
    }
    write_json(out_payload, args.out)
    failed = sum(1 for x in final_items if x.get("summarize_failed"))
    print(
        f"[summarize] wrote {args.out}: total={len(final_items)}, reused={len(papers)-len(todo_indices)}, failed={failed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
