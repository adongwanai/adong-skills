#!/usr/bin/env python3
"""url_check.py - fast batch verification for non-GitHub links (courses, docs, blogs, posts).

Checks reachability, cross-domain redirects, page title/canonical URL, and flags common
Chinese mirror/repost farms (CSDN, Gitee/GitCode mirrors) or QR-code/group-chat promo traps.

Usage:
  python3 url_check.py URL [URL ...] [--workers 6] [--timeout 12]

Prints a JSON list, one object per deduplicated URL. Standard library only.
"""
import argparse
import concurrent.futures
import html.parser
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

MAX_READ_BYTES = 131072  # 128 KB is plenty for <head> + main article text sample

MIRROR_OR_REPOST_HOSTS = (
    "csdn.net",
    "gitee.com",
    "gitcode.com",
    "51cto.com",
    "cnblogs.com",
    "cloud.tencent.com",
    "developer.aliyun.com",
)

PROMO_PATTERNS = [
    ("扫码领", re.compile(r"扫码.{0,8}(领取|领资料|加群|进群|获取)")),
    ("加群领资料", re.compile(r"(加群|进群|微信群).{0,8}(领资料|领源码|获取源码)")),
    ("公众号回复引流", re.compile(r"(关注公众号|后台|私信).{0,10}回复.{0,12}(领取|获取|解锁|源码|资料)")),
    ("付费训练营导流", re.compile(r"(训练营|付费专栏|限时秒杀|原价\s*\d+\s*元)")),
]


class _MetaParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_title = False
        self._skip_text = 0
        self.title_parts = []
        self.text_parts = []
        self.description = None
        self.canonical = None
        self.published_at = None

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t == "title":
            self._in_title = True
            return
        if t in ("script", "style", "noscript"):
            self._skip_text += 1
            return
        attr = {k.lower(): (v or "") for k, v in attrs if k}
        if t == "link" and "canonical" in attr.get("rel", "").lower():
            if attr.get("href"):
                self.canonical = attr["href"].strip()
        elif t == "meta":
            name = (attr.get("name") or attr.get("property") or "").lower()
            content = attr.get("content", "").strip()
            if not content:
                return
            if name in ("description", "og:description") and not self.description:
                self.description = content[:240]
            elif name in (
                "article:published_time", "article:modified_time",
                "og:updated_time", "publishdate", "date",
            ) and not self.published_at:
                self.published_at = content[:32]

    def handle_endtag(self, tag):
        t = tag.lower()
        if t == "title":
            self._in_title = False
        elif t in ("script", "style", "noscript") and self._skip_text > 0:
            self._skip_text -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        elif self._skip_text == 0:
            cleaned = data.strip()
            if cleaned:
                self.text_parts.append(cleaned)


def _norm_host(url):
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _check_mirror_host(host):
    for m in MIRROR_OR_REPOST_HOSTS:
        if host == m or host.endswith("." + m):
            return m
    return None


def http_fetch(url, timeout=12):
    """Return (status, final_url, content_type, body_bytes, error_msg). Stubbable in tests."""
    req = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = resp.headers.get("Content-Type", "")
            raw = resp.read(MAX_READ_BYTES)
            return resp.status, resp.geturl(), ctype, raw, None
    except urllib.error.HTTPError as e:
        try:
            raw = e.read(4096)
        except Exception:
            raw = b""
        return e.code, e.geturl() or url, e.headers.get("Content-Type", "") if e.headers else "", raw, None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        return 0, url, "", b"", str(e)


def check_url(url, timeout=12):
    clean = url.strip()
    out = {"input": clean, "flags": []}
    flags = out["flags"]

    parsed = urllib.parse.urlparse(clean)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        out["reachable"] = False
        flags.append("INVALID_URL")
        return out

    orig_host = _norm_host(clean)
    mirror = _check_mirror_host(orig_host)
    if mirror:
        flags.append(f"REPOST_OR_MIRROR_SITE:{mirror}")

    status, final_url, ctype, raw, err = http_fetch(clean, timeout=timeout)
    out["status"] = status
    out["final_url"] = final_url

    if status == 0:
        out["reachable"] = False
        out["error"] = err or "network failure"
        flags.append("UNREACHABLE")
        return out

    if status in (404, 410):
        out["reachable"] = False
        flags.append(f"DEAD_LINK:HTTP_{status}")
        return out

    if status in (401, 403, 429):
        # Anti-bot walls (Cloudflare/Reddit/Medium) return 403/429 even when page exists.
        out["reachable"] = None
        flags.append(f"BOT_WALL_OR_RESTRICTED:HTTP_{status}")
        return out

    if status >= 400:
        out["reachable"] = False
        flags.append(f"HTTP_ERROR:{status}")
        return out

    out["reachable"] = True
    final_host = _norm_host(final_url)
    if final_host and final_host != orig_host:
        flags.append(f"REDIRECTED_DOMAIN:{final_host}")
        final_mirror = _check_mirror_host(final_host)
        if final_mirror and f"REPOST_OR_MIRROR_SITE:{final_mirror}" not in flags:
            flags.append(f"REPOST_OR_MIRROR_SITE:{final_mirror}")

    text = raw.decode("utf-8", errors="replace")
    if "html" in ctype.lower() or "<html" in text[:1000].lower() or "<title" in text[:1000].lower():
        parser = _MetaParser()
        try:
            parser.feed(text)
        except Exception:
            pass
        title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
        out["title"] = title[:160] if title else None
        if parser.description:
            out["description"] = parser.description
        if parser.canonical and parser.canonical != final_url:
            out["canonical_url"] = parser.canonical
        if parser.published_at:
            out["published_at"] = parser.published_at

        body_sample = " ".join(parser.text_parts)[:20000]
        for label, pat in PROMO_PATTERNS:
            if pat.search(body_sample):
                flags.append(f"PROMO_FUNNEL_DETECTED:{label}")
    elif "json" in ctype.lower():
        out["content_type"] = "json"
    else:
        # e.g. plain text / llms.txt / markdown
        first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        out["preview"] = first_line[:160] or None

    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("urls", nargs="+", help="HTTP/HTTPS URLs to verify")
    p.add_argument("--workers", type=int, default=6, help="concurrent workers (default: 6)")
    p.add_argument("--timeout", type=int, default=12, help="per-URL timeout in seconds (default: 12)")
    a = p.parse_args(argv)

    seen = set()
    targets = []
    for u in a.urls:
        s = u.strip()
        if s and s not in seen:
            seen.add(s)
            targets.append(s)

    workers = max(1, min(a.workers, len(targets)))
    ordered = [None] * len(targets)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        fut_to_idx = {pool.submit(check_url, u, a.timeout): idx for idx, u in enumerate(targets)}
        for fut in concurrent.futures.as_completed(fut_to_idx):
            idx = fut_to_idx[fut]
            try:
                ordered[idx] = fut.result()
            except Exception as e:
                ordered[idx] = {"input": targets[idx], "reachable": False, "error": str(e), "flags": ["ERROR"]}

    json.dump(ordered, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
