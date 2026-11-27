#!/usr/bin/env python3
"""
AI Daily Report v2 · 多源免鉴权并发采集、容错缓存与并查集跨源共振去重引擎

复用了「信息源（Sources）」模块的核心设计：
1. 免登录、零 API Key、本机直连（含 SSRF 内网地址拦截，绝不经过第三方网页转文字代理）。
2. 四大信息源矩阵：
   - cn-ai：ainav 9 站中文 AI 资讯（支持当日 404 自动回退前一日）
   - builders-x & builders-podcasts：follow-builders 一手建设者 X 动态与播客摘录
   - hf-papers：Hugging Face Daily Papers（按点赞热度排序，超时优雅降级）
   - dev-hot & rss-curated：GitHub Trending、Hacker News、OpenAI News、arXiv cs.AI、量子位/极客公园 RSS 等
3. SourceCache 单源持久化缓存：网络抖动自动回退上次成功快照，绝不白屏。
4. 跨源共振并查集（Union-Find）+ 三维相关性打分（Relevance / Freshness / log1p Heat）。
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import ipaddress
import json
import math
import os
import re
import signal
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BEIJING_TZ = timezone(timedelta(hours=8))
SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = SKILL_ROOT / "config.json"
DEFAULT_CACHE_PATH = SKILL_ROOT / "cache" / "sources-cache.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

FOLLOW_BUILDERS_BASE = "https://raw.githubusercontent.com/zarazhangrui/follow-builders/main/"

AINAV_SITES = [
    ("36kr", "36氪"),
    ("liangziwei", "量子位"),
    ("jiqizhixing", "机器之心"),
    ("baai", "智源社区"),
    ("hellogithub", "HelloGitHub"),
    ("xinzhiyuan", "新智元"),
    ("aibase", "AIbase"),
    ("ithome", "IT之家"),
    ("jikegongyuan", "极客公园"),
]

CURATED_FEEDS = [
    {"id": "rss-openai", "title": "OpenAI News", "url": "https://openai.com/news/rss.xml", "tier": "official"},
    {"id": "rss-github-blog", "title": "GitHub Blog", "url": "https://github.blog/feed/", "tier": "official"},
    {
        "id": "rss-arxiv-ai",
        "title": "arXiv cs.AI",
        "url": "https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=20",
        "tier": "papers",
    },
    {"id": "rss-qbitai", "title": "量子位 RSS", "url": "https://www.qbitai.com/feed", "tier": "media"},
    {"id": "rss-geekpark", "title": "极客公园 RSS", "url": "https://www.geekpark.net/rss", "tier": "media"},
]

STOP_BIGRAMS = {
    "我们", "你们", "他们", "这个", "那个", "一个", "什么", "怎么", "可以",
    "没有", "不是", "就是", "因为", "所以", "如果", "但是", "还是", "已经", "自己",
    "今日", "最新", "正式", "宣布", "表示",
}

# 摘要尾部按钮噪音正则（移植自 hot.js cleanSummary）
RE_BUTTON_ARROW = re.compile(
    r"\s*[（(【\[]?\s*(?:(?:点击|点此|戳)\s*)?(?:(?:查看|阅读|展开)\s*)?"
    r"(?:原文|全文|更多|详情)(?:链接)?\s*[）)】\]]?\s*[>》›»→]+"
)
RE_BUTTON_END = re.compile(
    r"\s*[（(【\[]?\s*(?:(?:点击|点此|戳)\s*)?(?:查看|阅读|展开)\s*"
    r"(?:原文|全文|更多|详情)(?:链接)?\s*[）)】\]]?\s*[…。.]*\s*$"
)
RE_EN_BUTTON = re.compile(
    r"\s*(?:Read more|Continue reading|Read the full (?:story|article))\s*(?:[»›>→]+|[.…]*\s*$)",
    re.IGNORECASE,
)
RE_ELLIPSIS_TAG = re.compile(r"\s*\[(?:…|\.\.\.)\]\s*$")

CATEGORY_RULES: list[tuple[str, list[str], int]] = [
    ("科研进展", ["arxiv", "nature", "science", "neurips", "icml", "iclr", "cvpr", "aaai", "论文", "学术", "研究团队", "实验室", "基准测试", "benchmark", "定理"], 2),
    ("融资并购", ["融资", "领投", "跟投", "估值", "收购", "并购", "ipo", "上市", "亿美元", "亿元", "万美金", "种子轮", "天使轮", "a轮", "b轮", "c轮", "战略投资"], 3),
    ("开源工具", ["开源", "github", "hugging face", "huggingface", "apache-2.0", "mit许可", "仓库", "repo", "sdk", "cli", "框架", "工具库", "stars"], 2),
    ("政策监管", ["法案", "监管", "合规", "起诉", "诉讼", "反垄断", "禁令", "版权", "网信办", "欧盟", "法案", "安全审查", "白宫", "立法", "政策"], 3),
    ("产品发布", ["发布", "推出", "上线", "新版", "公测", "内测", "app", "助手", "硬件", "眼镜", "订阅", "api开放", "正式版"], 1),
    ("技术突破", ["架构", "推理", "训练", "算子", "量化", "上下文", "kv cache", "注意力", "强化学习", "rlhf", "grpo", "vla", "多模态", "吞吐", "延迟", "sota", "世界模型"], 2),
    ("重磅观点", ["访谈", "播客", "对谈", "预测", "警告", "直言", "观点", "karpathy", "altman", "lecun", "hassabis", "amodei", "黄仁勋", "创始人谈"], 2),
    ("产业观察", ["产业链", "商业化", "竞争格局", "护城河", "生态", "转型", "趋势分析", "深度", "复盘", "算力中心", "国产芯片"], 1),
    ("行业动态", ["财报", "营收", "合作", "签约", "组织架构", "高管", "离职", "扩招", "裁员", "用户数", "月活", "arr"], 1),
]


# ---------------------------------------------------------------------------
# 网络安全直连层（SSRF 防护）
# ---------------------------------------------------------------------------

def _assert_public_host(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"不支持的协议: {parsed.scheme}")
    host = parsed.hostname
    if not host:
        raise ValueError("URL 缺少主机名")
    if host.lower() in ("localhost", "localhost.localdomain"):
        raise ValueError("禁止访问本地回环地址")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise ConnectionError(f"DNS 解析失败 ({host}): {exc}") from exc

    for info in infos:
        ip_str = info[4][0]
        ip_obj = ipaddress.ip_address(ip_str)
        if (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
        ):
            # 注意：若本机开启了 Fake-IP (198.18.0.0/15) 透明代理网段，放行基准测试网段但阻断局域网/回环
            if ip_obj in ipaddress.ip_network("198.18.0.0/15"):
                continue
            raise PermissionError(f"SSRF 防护已拦截非公网地址: {host} -> {ip_str}")


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _assert_public_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_fetch_text(url: str, timeout: float = 8.5, extra_headers: dict[str, str] | None = None) -> str:
    _assert_public_host(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(SafeRedirectHandler)
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read(4 * 1024 * 1024)  # 单响应上限 4MB
        charset = resp.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def safe_fetch_json(url: str, timeout: float = 8.5, extra_headers: dict[str, str] | None = None) -> Any:
    text = safe_fetch_text(url, timeout=timeout, extra_headers=extra_headers)
    return json.loads(text)


def translate_error(exc: Exception) -> str:
    msg = str(exc)
    if isinstance(exc, urllib.error.HTTPError):
        code = exc.code
        if code in (401, 403):
            return f"HTTP {code}: 平台限制未登录访客读取"
        if code in (412, 418):
            return f"HTTP {code}: 触发站点反爬拦截"
        if code == 429:
            return "HTTP 429: 请求过于频繁，触发限流"
        if code == 404:
            return "HTTP 404: 目标日期或接口数据尚未生成"
        if code >= 500:
            return f"HTTP {code}: 源站服务端异常"
    if "timed out" in msg.lower() or isinstance(exc, TimeoutError | socket.timeout):
        return "请求超时（网络较慢或海外源需代理）"
    return msg[:140]


# ---------------------------------------------------------------------------
# 文本清洗、分词、相似度与去重工具
# ---------------------------------------------------------------------------

def decode_html_text(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", raw)
    cleaned = html.unescape(cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def clean_summary(raw: str, max_len: int = 220) -> str:
    text = decode_html_text(raw)
    text = RE_BUTTON_ARROW.sub(" ", text)
    text = RE_EN_BUTTON.sub(" ", text)
    text = RE_ELLIPSIS_TAG.sub("", text)
    text = RE_BUTTON_END.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        # 优先在句号/分号处优雅截断
        cut = text[:max_len]
        for sep in ("。", "；", "！", "？", ". ", "; "):
            idx = cut.rfind(sep)
            if idx >= max_len * 0.55:
                return cut[: idx + len(sep)].strip()
        return cut.rstrip("，、,. ") + "…"
    return text


def normalize_url(raw: str | None, base: str | None = None) -> str | None:
    if not raw:
        return None
    val = raw.strip()
    if base:
        val = urllib.parse.urljoin(base, val)
    try:
        p = urllib.parse.urlparse(val)
    except ValueError:
        return None
    if p.scheme not in ("http", "https") or not p.netloc:
        return None
    # 剥离常见追踪参数
    query_pairs = [
        (k, v)
        for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=False)
        if not k.lower().startswith(("utm_", "spm", "scm", "from", "hmsr", "ref"))
    ]
    clean_path = p.path.rstrip("/") or "/"
    return urllib.parse.urlunparse((p.scheme.lower(), p.netloc.lower(), clean_path, "", urllib.parse.urlencode(query_pairs), ""))


def parse_iso_date(raw: str | None) -> str | None:
    if not raw:
        return None
    val = str(raw).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(val, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=BEIJING_TZ)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=BEIJING_TZ)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def tokenize(text: str) -> set[str]:
    """移植自 tokens.js：英文取词，中文取相邻双字（过滤停用词）。"""
    out: set[str] = set()
    lower = (text or "").lower()
    for word in re.findall(r"[a-z0-9][a-z0-9+#.-]{1,}", lower):
        out.add(word)
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", lower):
        for i in range(len(run) - 1):
            pair = run[i : i + 2]
            if pair not in STOP_BIGRAMS:
                out.add(pair)
    return out


def token_found(token: str, have: set[str]) -> bool:
    if token in have:
        return True
    if re.match(r"^[a-z0-9]", token) and len(token) >= 4:
        return any(w.startswith(token) for w in have)
    return False


def title_similarity(a: str, b: str) -> float:
    left = tokenize(a)
    right = tokenize(b)
    if not left or not right:
        return 0.0
    both = len(left & right)
    return both / (len(left) + len(right) - both)


# ---------------------------------------------------------------------------
# 各源解析器（移植自 builtin.js / feeds.js / hot.js）
# ---------------------------------------------------------------------------

def fetch_ainav_site(site_id: str, site_name: str, target_date: str) -> tuple[list[dict], str | None]:
    """拉取 ainav 单站 JSON；若当日 404 则自动回退前一日。"""
    dates_to_try = [target_date]
    try:
        prev_day = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        dates_to_try.append(prev_day)
    except ValueError:
        pass

    last_err: Exception | None = None
    for idx, day in enumerate(dates_to_try):
        url = f"https://www.ainav.cn/news/json/{site_id}_{day}.json"
        try:
            data = safe_fetch_json(url, timeout=8.0)
            items = data.get("items")
            if not isinstance(items, list) or not items:
                raise ValueError("返回条目为空")
            rows = []
            for rank, item in enumerate(items[:25], 1):
                title = decode_html_text(item.get("title", ""))[:200]
                link = normalize_url(item.get("link"))
                if not title or not link:
                    continue
                rows.append({
                    "title": title,
                    "url": link,
                    "date": parse_iso_date(item.get("pubDate")) or f"{day}T04:00:00+00:00",
                    "summary": clean_summary(item.get("description", "")),
                    "heat": None,
                    "heat_unit": "",
                    "author": "",
                    "role": "",
                    "rank": rank,
                    "source_id": f"ainav-{site_id}",
                    "source_name": site_name,
                    "group_id": "cn-ai",
                    "tier": "opensource" if site_id == "hellogithub" else ("papers" if site_id == "baai" else "media"),
                })
            note = f"当日未生成，已自动回退 {day}" if idx > 0 else None
            return rows, note
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code == 404 and idx == 0:
                continue
            break
        except Exception as exc:
            last_err = exc
            break
    raise RuntimeError(translate_error(last_err) if last_err else "未知采集错误")


def fetch_builders_x() -> tuple[list[dict], str | None]:
    data = safe_fetch_json(f"{FOLLOW_BUILDERS_BASE}feed-x.json", timeout=9.0)
    x_list = data.get("x")
    if not isinstance(x_list, list):
        raise ValueError("feed-x.json 结构不符")
    rows = []
    for builder in x_list:
        author = str(builder.get("name") or builder.get("handle") or "").strip()
        role = clean_summary(str(builder.get("bio") or "").split("\n")[0], 70)
        for tweet in builder.get("tweets") or []:
            raw_text = str(tweet.get("text") or "").strip()
            link = normalize_url(tweet.get("url"))
            if not raw_text or not link:
                continue
            first_line = clean_summary(raw_text.split("\n")[0], 110)
            title = f"{author}：{first_line}" if author and author.lower() not in first_line.lower() else first_line
            likes = tweet.get("likes")
            rows.append({
                "title": title,
                "url": link,
                "date": parse_iso_date(tweet.get("createdAt")),
                "summary": clean_summary(raw_text, 220),
                "heat": int(likes) if isinstance(likes, int | float) else None,
                "heat_unit": "赞",
                "author": author,
                "role": role,
                "rank": 0,
                "source_id": "builders-x",
                "source_name": "X · 建设者",
                "group_id": "builders-x",
                "tier": "builders",
            })
    rows.sort(key=lambda r: (r.get("date") or "", r.get("heat") or 0), reverse=True)
    for idx, r in enumerate(rows[:25], 1):
        r["rank"] = idx
    return rows[:25], None


def fetch_builders_podcasts() -> tuple[list[dict], str | None]:
    data = safe_fetch_json(f"{FOLLOW_BUILDERS_BASE}feed-podcasts.json", timeout=9.0)
    podcasts = data.get("podcasts")
    if not isinstance(podcasts, list):
        raise ValueError("feed-podcasts.json 结构不符")
    rows = []
    for idx, row in enumerate(podcasts[:15], 1):
        title = clean_summary(row.get("title", ""), 180)
        link = normalize_url(row.get("url"))
        if not title or not link:
            continue
        podcast_name = str(row.get("name") or "").strip()
        rows.append({
            "title": f"【播客 · {podcast_name}】{title}" if podcast_name else title,
            "url": link,
            "date": parse_iso_date(row.get("publishedAt")),
            "summary": clean_summary(row.get("transcript", ""), 220),
            "heat": None,
            "heat_unit": "",
            "author": podcast_name,
            "role": "AI 建设者播客",
            "rank": idx,
            "source_id": "builders-podcasts",
            "source_name": "播客 · 建设者",
            "group_id": "builders-podcasts",
            "tier": "builders",
        })
    return rows, None


def fetch_hf_papers() -> tuple[list[dict], str | None]:
    data = safe_fetch_json("https://huggingface.co/api/daily_papers?limit=25", timeout=6.5)
    if not isinstance(data, list):
        raise ValueError("HF Daily Papers 返回格式不符")
    rows = []
    for item in data:
        paper = item.get("paper") or {}
        pid = paper.get("id")
        title = clean_summary(paper.get("title", ""), 200)
        if not pid or not title:
            continue
        upvotes = paper.get("upvotes")
        rows.append({
            "title": title,
            "url": f"https://huggingface.co/papers/{urllib.parse.quote(str(pid))}",
            "date": parse_iso_date(paper.get("publishedAt")),
            "summary": clean_summary(paper.get("summary", ""), 220),
            "heat": int(upvotes) if isinstance(upvotes, int | float) else None,
            "heat_unit": "upvotes",
            "author": "",
            "role": "",
            "rank": 0,
            "source_id": "hf-papers",
            "source_name": "HF Daily Papers",
            "group_id": "hf-papers",
            "tier": "papers",
        })
    rows.sort(key=lambda r: r.get("heat") or 0, reverse=True)
    for idx, r in enumerate(rows[:20], 1):
        r["rank"] = idx
    return rows[:20], None


def fetch_github_trending() -> tuple[list[dict], str | None]:
    page = safe_fetch_text("https://github.com/trending", timeout=8.5)
    blocks = re.findall(r'<article class="Box-row">[\s\S]*?</article>', page)
    AI_HINT = re.compile(
        r"\b(ai|llm|agent|agents|gpt|claude|mcp|rag|vla|robot|embodied|diffusion|transformer|"
        r"inference|cuda|tensor|kernel|mlx|gguf|ollama|openai|deepseek|qwen|eval|benchmark|model|voice|tts|vision)\b",
        re.IGNORECASE,
    )
    rows = []
    for idx, block in enumerate(blocks[:25], 1):
        m_href = re.search(r'<h2[\s\S]*?<a[^>]*href="([^"]+)"', block)
        if not m_href:
            continue
        href = m_href.group(1).strip()
        repo_name = href.lstrip("/").replace("/", " / ")
        m_stars = re.search(r"([\d,]+)\s+stars?\s+today", block)
        m_desc = re.search(r'<p class="[^"]*">([\s\S]*?)</p>', block)
        desc = clean_summary(m_desc.group(1) if m_desc else "", 200)
        # 仅保留 AI / 工具链高度相关项目或今日高星项目
        stars_today = int(m_stars.group(1).replace(",", "")) if m_stars else None
        if not AI_HINT.search(f"{repo_name} {desc}") and (stars_today or 0) < 400:
            continue
        rows.append({
            "title": f"GitHub 热榜：{repo_name}",
            "url": normalize_url(href, "https://github.com/"),
            "date": datetime.now(timezone.utc).isoformat(),
            "summary": desc or "GitHub 今日热门开源仓库",
            "heat": stars_today,
            "heat_unit": "今日Star",
            "author": "",
            "role": "",
            "rank": idx,
            "source_id": "hot-github",
            "source_name": "GitHub Trending",
            "group_id": "dev-hot",
            "tier": "opensource",
        })
    return rows[:15], None


def fetch_hackernews() -> tuple[list[dict], str | None]:
    data = safe_fetch_json("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30", timeout=7.5)
    AI_HINT = re.compile(
        r"\b(ai|llm|gpt|claude|gemini|anthropic|openai|deepseek|qwen|agent|mcp|gpu|nvidia|"
        r"inference|model|neural|robot|arxiv|open-source|coding|benchmark|transformer)\b",
        re.IGNORECASE,
    )
    rows = []
    for idx, hit in enumerate(data.get("hits") or [], 1):
        title = clean_summary(hit.get("title", ""), 200)
        if not title or not AI_HINT.search(title):
            continue
        oid = hit.get("objectID", "")
        url = normalize_url(hit.get("url")) or f"https://news.ycombinator.com/item?id={oid}"
        pts = hit.get("points")
        comments = hit.get("num_comments")
        rows.append({
            "title": title,
            "url": url,
            "date": parse_iso_date(hit.get("created_at")),
            "summary": f"Hacker News 热门讨论（{comments} 条评论，{pts} points）" if comments is not None else "",
            "heat": int(pts) if isinstance(pts, int | float) else None,
            "heat_unit": "pts",
            "author": str(hit.get("author") or ""),
            "role": "",
            "rank": idx,
            "source_id": "hot-hn",
            "source_name": "Hacker News",
            "group_id": "dev-hot",
            "tier": "opensource",
        })
    return rows[:15], None


def parse_rss_or_atom(xml_text: str, base_url: str, feed_meta: dict) -> list[dict]:
    blocks = re.findall(r"<(?:item|entry)\b[\s\S]*?</(?:item|entry)>", xml_text, flags=re.IGNORECASE)
    rows = []
    for idx, block in enumerate(blocks[:18], 1):
        # 提取标题
        m_title = re.search(r"<title\b[^>]*>([\s\S]*?)</title>", block, re.IGNORECASE)
        title = decode_html_text(m_title.group(1) if m_title else "")[:200]
        # 提取链接（兼容 Atom rel="alternate" 与 RSS <link>）
        link_raw = None
        for m_link in re.finditer(r"<link\b([^>]*)/?>", block, re.IGNORECASE):
            attrs = m_link.group(1)
            if re.search(r'rel=["\']alternate["\']', attrs, re.IGNORECASE) or not re.search(r"rel=", attrs, re.IGNORECASE):
                m_href = re.search(r'href=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
                if m_href:
                    link_raw = html.unescape(m_href.group(1))
                    break
        if not link_raw:
            for tag in ("link", "guid", "id"):
                m_tag = re.search(rf"<{tag}\b[^>]*>([\s\S]*?)</{tag}>", block, re.IGNORECASE)
                if m_tag and m_tag.group(1).strip():
                    link_raw = decode_html_text(m_tag.group(1))
                    break
        url = normalize_url(link_raw, base_url)
        if not title or not url:
            continue
        # 提取摘要
        summary = ""
        for stag in ("description", "summary", "content:encoded", "content"):
            m_sum = re.search(rf"<{stag}\b[^>]*>([\s\S]*?)</{stag}>", block, re.IGNORECASE)
            if m_sum and m_sum.group(1).strip():
                summary = clean_summary(m_sum.group(1), 220)
                break
        # 提取日期
        pub_date = None
        for dtag in ("pubDate", "published", "updated", "dc:date"):
            m_date = re.search(rf"<{dtag}\b[^>]*>([\s\S]*?)</{dtag}>", block, re.IGNORECASE)
            if m_date and m_date.group(1).strip():
                pub_date = parse_iso_date(decode_html_text(m_date.group(1)))
                if pub_date:
                    break

        rows.append({
            "title": title,
            "url": url,
            "date": pub_date,
            "summary": summary,
            "heat": None,
            "heat_unit": "",
            "author": "",
            "role": "",
            "rank": idx,
            "source_id": feed_meta["id"],
            "source_name": feed_meta["title"],
            "group_id": "rss-curated",
            "tier": feed_meta["tier"],
        })
    return rows


def fetch_rss_feed(feed_meta: dict) -> tuple[list[dict], str | None]:
    xml_text = safe_fetch_text(feed_meta["url"], timeout=8.0)
    rows = parse_rss_or_atom(xml_text, feed_meta["url"], feed_meta)
    if not rows:
        raise ValueError("订阅源返回条目为空")
    return rows, None


# ---------------------------------------------------------------------------
# 持久化缓存（SourceCache）
# ---------------------------------------------------------------------------

def load_cache(cache_path: Path) -> dict[str, Any]:
    if not cache_path.exists():
        return {"sources": {}}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return {"sources": {}}


def save_cache_atomic(cache_path: Path, data: dict[str, Any]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp_path, 0o600)
    os.replace(tmp_path, cache_path)


# ---------------------------------------------------------------------------
# 智能预分类、跨源并查集聚类与三维评分
# ---------------------------------------------------------------------------

def infer_category(title: str, summary: str, tier: str, source_name: str) -> str:
    text = f"{title} {summary}".lower()
    scores: dict[str, int] = {cat: 0 for cat, _, _ in CATEGORY_RULES}

    # 信源先验偏置
    if tier == "papers" or source_name in ("arXiv cs.AI", "HF Daily Papers", "智源社区"):
        scores["科研进展"] += 3
    elif tier == "opensource" or source_name in ("HelloGitHub", "GitHub Trending"):
        scores["开源工具"] += 4
    elif tier == "builders":
        scores["重磅观点"] += 3

    for cat, kw_list, weight in CATEGORY_RULES:
        for kw in kw_list:
            if kw in text:
                scores[cat] += weight

    best_cat, best_score = max(scores.items(), key=lambda kv: kv[1])
    return best_cat if best_score > 0 else "行业动态"


def cluster_and_rank(
    raw_entries: list[dict[str, Any]],
    focus_topics: list[str],
    blocked_words: list[str],
    now_ts: float,
) -> tuple[list[dict[str, Any]], int]:
    """
    1. 屏蔽词过滤
    2. 同一来源内部对热度做 log1p + MinMax 归一化
    3. 并查集（Union-Find）合并不同来源的同一事件（URL 相同 或 标题 Jaccard >= 0.45）
    4. 三维加权打分 + 跨源共振加成
    """
    visible: list[dict[str, Any]] = []
    blocked_count = 0
    for entry in raw_entries:
        blob = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
        if any(w.strip().lower() in blob for w in blocked_words if w.strip()):
            blocked_count += 1
            continue
        visible.append(entry)

    if not visible:
        return [], blocked_count

    # 按来源内部归一化热度
    by_source: dict[str, list[int]] = {}
    for idx, item in enumerate(visible):
        by_source.setdefault(item["source_id"], []).append(idx)

    norm_heats = [0.0] * len(visible)
    for indices in by_source.values():
        logs = [
            math.log1p(visible[i]["heat"])
            if isinstance(visible[i].get("heat"), int | float) and visible[i]["heat"] >= 0
            else None
            for i in indices
        ]
        known = [v for v in logs if v is not None]
        if not known:
            continue
        lo, hi = min(known), max(known)
        for pos, val in zip(indices, logs):
            norm_heats[pos] = (val - lo) / (hi - lo) if (val is not None and hi > lo) else (0.5 if val is not None else 0.0)

    # 并查集跨源事件合并
    n = len(visible)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    token_sets = [tokenize(item["title"]) for item in visible]
    urls = [item.get("url") for item in visible]

    for i in range(n):
        for j in range(i + 1, n):
            same = False
            if urls[i] and urls[i] == urls[j]:
                same = True
            elif token_sets[i] and token_sets[j]:
                inter = len(token_sets[i] & token_sets[j])
                if inter >= 2:
                    jaccard = inter / (len(token_sets[i]) + len(token_sets[j]) - inter)
                    if jaccard >= 0.45:
                        same = True
            if same:
                parent[find(j)] = find(i)

    buckets: dict[int, list[int]] = {}
    for idx in range(n):
        buckets.setdefault(find(idx), []).append(idx)

    # 预分词方向词
    topic_tokens = [(t, tokenize(t)) for t in focus_topics if t.strip()]

    clusters: list[dict[str, Any]] = []
    for member_indices in buckets.values():
        # 挑选信息最完整的代表条目（优先有详尽摘要、权威源、标题适中）
        members = [visible[i] for i in member_indices]
        members_with_heat = list(zip(member_indices, members))
        members_with_heat.sort(
            key=lambda pair: (
                1 if len(pair[1].get("summary", "")) >= 30 else 0,
                1 if pair[1].get("tier") in ("official", "papers", "builders") else 0,
                norm_heats[pair[0]],
                -pair[1].get("rank", 99),
            ),
            reverse=True,
        )
        rep_idx, rep = members_with_heat[0]

        # 合并去重来源链接列表
        seen_sources: dict[str, dict[str, Any]] = {}
        for idx_m, m in members_with_heat:
            sname = m["source_name"]
            if sname not in seen_sources:
                seen_sources[sname] = {
                    "source_id": m["source_id"],
                    "name": sname,
                    "url": m["url"],
                    "heat": m.get("heat"),
                    "heat_unit": m.get("heat_unit", ""),
                    "tier": m.get("tier", "media"),
                }

        # 取最丰富摘要
        best_summary = max((m.get("summary", "") for m in members), key=len, default="")
        blob_text = f"{rep['title']} {best_summary}"
        have_tokens = tokenize(blob_text)
        lower_blob = blob_text.lower()

        # 计算方向命中 Relevance (0-1)
        matched_topics: list[str] = []
        best_rel = 0.0
        for raw_topic, wanted in topic_tokens:
            if not wanted:
                if raw_topic.lower() in lower_blob:
                    matched_topics.append(raw_topic)
                    best_rel = max(best_rel, 1.0)
                continue
            hit_n = sum(1 for tok in wanted if token_found(tok, have_tokens))
            share = hit_n / len(wanted)
            if share >= 0.5:
                matched_topics.append(raw_topic)
                best_rel = max(best_rel, share)

        # 计算新鲜度 Freshness (0-1，30天线性衰减，近48小时接近1)
        fresh = 0.55
        if rep.get("date"):
            try:
                dt = datetime.fromisoformat(rep["date"].replace("Z", "+00:00"))
                age_days = max(0.0, (now_ts - dt.timestamp()) / 86400.0)
                fresh = max(0.0, min(1.0, 1.0 - age_days / 30.0))
            except ValueError:
                pass

        max_norm_heat = max(norm_heats[i] for i in member_indices)
        resonance_count = len(seen_sources)
        resonance_bonus = min(0.24, 0.08 * (resonance_count - 1))

        score = round(0.65 * best_rel + 0.25 * fresh + 0.10 * max_norm_heat + resonance_bonus, 4)
        category = infer_category(rep["title"], best_summary, rep.get("tier", "media"), rep["source_name"])

        clusters.append({
            "title": rep["title"],
            "summary": best_summary,
            "primary_url": rep["url"],
            "primary_source": rep["source_name"],
            "tier": rep.get("tier", "media"),
            "author": rep.get("author", ""),
            "role": rep.get("role", ""),
            "date": rep.get("date"),
            "suggested_category": category,
            "resonance_count": resonance_count,
            "sources": list(seen_sources.values()),
            "focus_hits": matched_topics[:4],
            "score": score,
            "score_parts": {
                "relevance": round(best_rel, 3),
                "freshness": round(fresh, 3),
                "heat": round(max_norm_heat, 3),
                "resonance_bonus": round(resonance_bonus, 3),
            },
        })

    # 按综合得分、跨源共振数排序
    clusters.sort(key=lambda c: (c["score"], c["resonance_count"]), reverse=True)
    for idx, c in enumerate(clusters, 1):
        c["id"] = f"N{idx:03d}"
    return clusters, blocked_count


# ---------------------------------------------------------------------------
# 主控流程
# ---------------------------------------------------------------------------

def collect_all(
    target_date: str,
    config: dict[str, Any],
    cache_path: Path,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any]:
    enabled_groups = set(config.get("enabled_groups") or ["cn-ai", "builders-x", "builders-podcasts", "dev-hot", "rss-curated"])
    cache = load_cache(cache_path) if use_cache else {"sources": {}}
    cached_sources = cache.setdefault("sources", {})

    tasks: list[tuple[str, str, str, Any]] = []
    if "cn-ai" in enabled_groups:
        for sid, sname in AINAV_SITES:
            tasks.append((f"ainav-{sid}", sname, "cn-ai", lambda s=sid, n=sname: fetch_ainav_site(s, n, target_date)))
    if "builders-x" in enabled_groups:
        tasks.append(("builders-x", "X · 建设者", "builders-x", fetch_builders_x))
    if "builders-podcasts" in enabled_groups:
        tasks.append(("builders-podcasts", "播客 · 建设者", "builders-podcasts", fetch_builders_podcasts))
    if "hf-papers" in enabled_groups:
        tasks.append(("hf-papers", "HF Daily Papers", "hf-papers", fetch_hf_papers))
    if "dev-hot" in enabled_groups:
        tasks.append(("hot-github", "GitHub Trending", "dev-hot", fetch_github_trending))
        tasks.append(("hot-hn", "Hacker News", "dev-hot", fetch_hackernews))
    if "rss-curated" in enabled_groups:
        for feed in CURATED_FEEDS:
            tasks.append((feed["id"], feed["title"], "rss-curated", lambda f=feed: fetch_rss_feed(f)))

    raw_entries: list[dict[str, Any]] = []
    source_telemetry: list[dict[str, Any]] = []
    now_iso = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M:%S")

    def run_one(task_tuple: tuple[str, str, str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        sid, sname, gid, fn = task_tuple
        cache_key = f"{sid}:{target_date}" if sid.startswith("ainav-") else sid
        existing = cached_sources.get(cache_key) or cached_sources.get(sid)

        # 若当天已缓存且非强制刷新，同自然日内 2 小时内可直接复用缓存加速
        if use_cache and not force_refresh and existing and existing.get("fetched_day") == target_date:
            age_sec = time.time() - float(existing.get("fetched_ts", 0))
            if age_sec < 7200 and existing.get("entries"):
                entries = existing["entries"]
                return (
                    {
                        "source_id": sid,
                        "source_name": sname,
                        "group_id": gid,
                        "article_count": len(entries),
                        "status": "cached",
                        "note": "命中近2小时本地缓存",
                        "fetched_at": existing.get("fetched_at", now_iso),
                    },
                    entries,
                )

        try:
            entries, note = fn()
            cached_sources[cache_key] = {
                "fetched_day": target_date,
                "fetched_ts": time.time(),
                "fetched_at": now_iso,
                "entries": entries,
            }
            cached_sources[sid] = cached_sources[cache_key]
            return (
                {
                    "source_id": sid,
                    "source_name": sname,
                    "group_id": gid,
                    "article_count": len(entries),
                    "status": "ok",
                    "note": note or "",
                    "fetched_at": now_iso,
                },
                entries,
            )
        except Exception as exc:
            err_msg = translate_error(exc)
            # SWR 容错回退：若网络报错但存在上次成功快照，自动回退使用旧快照并标注原因
            if use_cache and existing and existing.get("entries"):
                fallback_entries = existing["entries"]
                return (
                    {
                        "source_id": sid,
                        "source_name": sname,
                        "group_id": gid,
                        "article_count": len(fallback_entries),
                        "status": "fallback_cache",
                        "note": f"实时拉取异常（{err_msg}），已回退上次缓存快照",
                        "fetched_at": existing.get("fetched_at", now_iso),
                    },
                    fallback_entries,
                )
            return (
                {
                    "source_id": sid,
                    "source_name": sname,
                    "group_id": gid,
                    "article_count": 0,
                    "status": "error",
                    "note": err_msg,
                    "fetched_at": now_iso,
                },
                [],
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(run_one, tasks))

    for meta, entries in results:
        source_telemetry.append(meta)
        raw_entries.extend(entries)

    if use_cache:
        try:
            save_cache_atomic(cache_path, cache)
        except Exception:
            pass

    focus_cfg = config.get("focus") or {}
    clusters, blocked_count = cluster_and_rank(
        raw_entries=raw_entries,
        focus_topics=focus_cfg.get("topics") or [],
        blocked_words=focus_cfg.get("blocked") or [],
        now_ts=time.time(),
    )

    pool_max = int((config.get("limits") or {}).get("candidate_pool_max", 110))
    candidates = clusters[:pool_max]

    # 兼容旧版字段（total_articles / sources），同时提供 v2 全量 candidates 账本候选池
    legacy_sources = [
        {
            "source_id": m["source_id"],
            "source_name": m["source_name"],
            "group_id": m["group_id"],
            "article_count": m["article_count"],
            "status": m["status"],
            "note": m["note"],
            "fetched_at": m["fetched_at"],
        }
        for m in source_telemetry
    ]

    return {
        "schema_version": "2.0",
        "date": target_date,
        "update_time": now_iso,
        "stats": {
            "raw_articles": len(raw_entries),
            "blocked_filtered": blocked_count,
            "unique_clusters": len(clusters),
            "candidate_count": len(candidates),
            "multi_source_clusters": sum(1 for c in clusters if c["resonance_count"] >= 2),
            "ok_sources": sum(1 for m in source_telemetry if m["status"] in ("ok", "cached", "fallback_cache")),
            "total_sources": len(source_telemetry),
        },
        "total_articles": len(raw_entries),
        "focus": focus_cfg,
        "sources": legacy_sources,
        "candidates": candidates,
    }


def load_merged_config(cfg_path: Path) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if cfg_path.exists():
        config = json.loads(cfg_path.read_text(encoding="utf-8"))
    local_override = cfg_path.with_name("config.local.json")
    if local_override.exists():
        try:
            override_data = json.loads(local_override.read_text(encoding="utf-8"))
            config.update(override_data)
        except Exception:
            pass
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="AI 行业日报 v2 · 多源免鉴权采集与跨源共振去重")
    parser.add_argument("--date", default=datetime.now(BEIJING_TZ).strftime("%Y-%m-%d"), help="目标日期 YYYY-MM-DD（北京时间）")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="配置文件路径")
    parser.add_argument("--out", default="", help="输出候选池 JSON 文件路径（默认写入 skill cache 目录，不污染工作区）")
    parser.add_argument("--force", action="store_true", help="忽略近2小时缓存，强制重新拉取")
    parser.add_argument("--no-cache", action="store_true", help="完全禁用本地缓存读写")
    parser.add_argument("--print-brief", action="store_true", help="在终端打印精简候选列表概览")
    parser.add_argument("--dump-for-agent", action="store_true", help="输出供大模型筛选的高信噪比紧凑摘要文本")
    args = parser.parse_args()

    cfg_path = Path(args.config).expanduser()
    config = load_merged_config(cfg_path)

    default_candidates_path = SKILL_ROOT / "cache" / f"{args.date}_candidates.json"
    out_path = Path(args.out).expanduser() if args.out else default_candidates_path
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        fallback_dir = Path(config.get("fallback_output_dir", str(SKILL_ROOT / "output"))).expanduser()
        fallback_dir.mkdir(parents=True, exist_ok=True)
        out_path = fallback_dir / out_path.name
        print(f"⚠️ 原输出目录受 macOS 权限限制，已自动切换至: {out_path}", file=sys.stderr)

    print(f"🚀 开始并发采集 {args.date} 多源 AI 资讯（免登录 / 零 API Key / SSRF 防护）...", file=sys.stderr)
    payload = collect_all(
        target_date=args.date,
        config=config,
        cache_path=DEFAULT_CACHE_PATH,
        use_cache=not args.no_cache,
        force_refresh=args.force,
    )

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    st = payload["stats"]
    print(
        f"✅ 采集与聚类完成！共连通 {st['ok_sources']}/{st['total_sources']} 个信源，"
        f"原始 {st['raw_articles']} 篇 → 去重合并为 {st['unique_clusters']} 个独立事件"
        f"（其中 🔥 多源共振 {st['multi_source_clusters']} 个），精选候选池 {st['candidate_count']} 条。",
        file=sys.stderr,
    )
    print(f"📦 候选池文件: {out_path}", file=sys.stderr)

    if args.print_brief:
        print("\n=== Top 15 高分/共振候选预览 ===")
        for c in payload["candidates"][:15]:
            res = f" [🔥{c['resonance_count']}源]" if c["resonance_count"] >= 2 else ""
            hits = f" 🎯{','.join(c['focus_hits'])}" if c["focus_hits"] else ""
            print(f"{c['id']} [{c['suggested_category']}]{res}{hits} {c['title']} ({c['primary_source']})")

    if args.dump_for_agent:
        print(f"# {args.date} 候选事件池（共 {len(payload['candidates'])} 条，按综合得分与跨源共振排序）\n")
        for c in payload["candidates"]:
            srcs = " / ".join(
                f"{s['name']}" + (f"({s['heat']}{s['heat_unit']})" if s.get("heat") else "")
                for s in c["sources"][:4]
            )
            res = f"🔥{c['resonance_count']}源共振 | " if c["resonance_count"] >= 2 else ""
            hits = f" | 命中:{','.join(c['focus_hits'])}" if c["focus_hits"] else ""
            summary = c.get("summary") or "（无摘要，请仅基于标题事实提炼，禁编造数字）"
            print(f"- **{c['id']}** [{c['suggested_category']}] ({res}来源: {srcs}{hits})")
            print(f"  标题: {c['title']}")
            print(f"  摘要: {summary}")


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    main()
