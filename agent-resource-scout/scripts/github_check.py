#!/usr/bin/env python3
"""github_check.py - verify GitHub repos before recommending them.

Usage:
  python3 github_check.py OWNER/REPO [URL ...] [--track learning|selection|archive] [--no-issues]
                          [--pypi [OWNER/REPO=]PKG ...] [--npm [OWNER/REPO=]PKG ...] [--workers N]

Env:
  GITHUB_TOKEN / GH_TOKEN  optional; raises GitHub API rate limit from 60 to 5000 requests/hour.
                           Falls back to `gh auth token` automatically when available.

Prints a JSON list, one object per deduplicated repo. Standard library only.
"""
import argparse
import concurrent.futures
import json
import os
import re
import statistics
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
PERMISSIVE_LICENSES = {
    "MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "BSD-3-Clause-Clear", "0BSD", "ISC", "Unlicense", "CC0-1.0",
    "CC-BY-4.0", "Zlib", "PSF-2.0", "BlueOak-1.0.0", "Artistic-2.0", "WTFPL",
}
STRONG_COPYLEFT_PREFIXES = ("AGPL-", "GPL-", "SSPL-", "OSL-", "CPAL-")
WEAK_COPYLEFT_PREFIXES = ("LGPL-", "MPL-", "EPL-", "EUPL-", "CDDL-", "CECILL-C")
NON_COMMERCIAL_IDS = {"BSL-1.1", "ELv2", "Commons-Clause"}

# "kaggle" kept as backward-compatible alias for "archive" (no staleness cutoff).
STALE_DAYS = {"learning": 365, "selection": 90, "archive": None, "kaggle": None}
# Note: GitHub Organizations default member visibility to Private, causing core team
# maintainers with merged commits to appear as "CONTRIBUTOR" via REST API (whereas random
# passersby appear as "NONE").
MAINTAINER_ROLES = {"OWNER", "MEMBER", "COLLABORATOR", "CONTRIBUTOR"}
STRICT_MEMBER_ROLES = {"OWNER", "MEMBER", "COLLABORATOR"}
ISSUE_SAMPLE = 15        # issues whose comments are inspected
ISSUE_MIN_AGE_DAYS = 7   # ignore issues too new to have had a chance of a reply

_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_TOKEN_RESOLVED = False
_CACHED_TOKEN = None
_SEARCH_LOCK = threading.Lock()
_LAST_SEARCH_TS = 0.0


class RateLimited(Exception):
    pass


class ApiError(Exception):
    pass


def resolve_token():
    """Resolve GitHub token from env vars or `gh auth token` CLI fallback (cached)."""
    env_tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env_tok:
        return env_tok.strip()
    global _TOKEN_RESOLVED, _CACHED_TOKEN
    if not _TOKEN_RESOLVED:
        _TOKEN_RESOLVED = True
        try:
            proc = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True, text=True, timeout=2, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                _CACHED_TOKEN = proc.stdout.strip()
        except Exception:
            _CACHED_TOKEN = None
    return _CACHED_TOKEN


def _is_rate_limited_http_error(e, body):
    if e.code == 429:
        return True
    if e.code != 403:
        return False
    if e.headers and e.headers.get("X-RateLimit-Remaining") == "0":
        return True
    if e.headers and e.headers.get("Retry-After"):
        return True
    msg = (body.get("message") if isinstance(body, dict) else "") or ""
    return "rate limit" in msg.lower()


def http_get(path_or_url):
    """Return (status, parsed_json_or_None). Replaced by a stub in tests."""
    is_full_url = path_or_url.startswith(("http://", "https://"))
    url = path_or_url if is_full_url else API + path_or_url
    headers = {"User-Agent": "agent-resource-scout"}
    if not is_full_url or url.startswith(API):
        headers["Accept"] = "application/vnd.github+json"
        token = resolve_token()
        if token:
            headers["Authorization"] = "Bearer " + token
    else:
        headers["Accept"] = "application/json"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = None
        if (not is_full_url or url.startswith(API)) and _is_rate_limited_http_error(e, body):
            raise RateLimited("GitHub API rate limit hit; set GITHUB_TOKEN (or login via `gh auth login`) and retry")
        return e.code, body
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, {"message": f"network error: {e}"}


def api_message(status, body):
    msg = body.get("message") if isinstance(body, dict) else None
    label = f"HTTP {status}" if status else "NETWORK_ERROR"
    return label + (f": {msg[:160]}" if msg else "")


def parse_repo(arg):
    raw = arg.strip().rstrip(".,;)")
    if "://" in raw or raw.startswith(("www.", "git@")):
        m = re.search(r"(?:https?://|git@)?(?:www\.)?github\.com[/:]([^/\s#?]+)/([^/\s#?]+)", raw)
        if not m:
            raise ValueError(f"not a GitHub repository URL: {arg}")
        owner, repo = m.group(1), m.group(2)
    else:
        clean = re.split(r"[#?]", raw, maxsplit=1)[0].strip("/")
        parts = clean.split("/")
        if len(parts) < 2:
            raise ValueError("cannot parse repo: " + arg)
        # GitHub usernames never contain dots; catches accidental "huggingface.co/org/repo".
        if "." in parts[0]:
            raise ValueError(f"not a GitHub owner/repo (looks like another domain): {arg}")
        owner, repo = parts[0], parts[1]

    if repo.endswith(".git"):
        repo = repo[:-4]
    if not _OWNER_RE.match(owner) or not _REPO_RE.match(repo) or repo in (".", ".."):
        raise ValueError("invalid GitHub owner/repo: " + arg)
    return owner, repo


def parse_time(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if s else None


def days_since(dt, now):
    return None if dt is None else max(0, (now - dt).days)


def classify_license(lic):
    if not lic:
        return "NO_LICENSE"
    if lic == "NOASSERTION":
        return "CUSTOM_LICENSE_READ_IT"
    if lic in PERMISSIVE_LICENSES:
        return None
    tokens = lic.upper().split("-")
    if "NC" in tokens or lic in NON_COMMERCIAL_IDS:
        return "NON_COMMERCIAL_OR_SOURCE_AVAILABLE:" + lic
    if lic.startswith(STRONG_COPYLEFT_PREFIXES):
        return "STRONG_COPYLEFT:" + lic
    if lic.startswith(WEAK_COPYLEFT_PREFIXES):
        return "WEAK_COPYLEFT:" + lic
    return "CHECK_LICENSE:" + lic


def _fetch_eligible_issues(full_name, now):
    global _LAST_SEARCH_TS
    cutoff_dt = now - timedelta(days=ISSUE_MIN_AGE_DAYS)
    cutoff_str = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    q = urllib.parse.quote(f"repo:{full_name} is:issue created:<={cutoff_str}", safe=":")
    try:
        with _SEARCH_LOCK:
            gap = 0.35 - (time.monotonic() - _LAST_SEARCH_TS)
            if gap > 0 and http_get.__module__ == __name__:
                time.sleep(gap)
            st, search_data = http_get(
                f"/search/issues?q={q}&sort=created&order=desc&per_page={ISSUE_SAMPLE}"
            )
            _LAST_SEARCH_TS = time.monotonic()
    except RateLimited:
        st, search_data = 0, None
    if st == 200 and isinstance(search_data, dict) and isinstance(search_data.get("items"), list):
        return [
            i for i in search_data["items"]
            if "pull_request" not in i
            and (days_since(parse_time(i.get("created_at")), now) or 0) >= ISSUE_MIN_AGE_DAYS
        ][:ISSUE_SAMPLE]

    # Fallback: repository issues endpoint (mixes PRs + issues; use per_page=100).
    status, issues = http_get(
        f"/repos/{full_name}/issues?state=all&per_page=100&sort=created&direction=desc"
    )
    if status != 200 or not isinstance(issues, list):
        return None
    return [
        i for i in issues
        if "pull_request" not in i
        and (days_since(parse_time(i.get("created_at")), now) or 0) >= ISSUE_MIN_AGE_DAYS
    ][:ISSUE_SAMPLE]


def issue_response(full_name, now):
    issues = _fetch_eligible_issues(full_name, now)
    if issues is None:
        return None
    if not issues:
        return {"sampled": 0}

    hours, replied, strict_replied = [], 0, 0
    inspected, comment_errors = 0, 0
    closed_count = sum(1 for i in issues if i.get("state") == "closed")

    for issue in issues:
        if issue.get("comments", 0) == 0:
            inspected += 1
            continue
        try:
            st, comments = http_get(f"/repos/{full_name}/issues/{issue['number']}/comments?per_page=30")
        except RateLimited:
            comment_errors += 1
            break
        if st != 200 or not isinstance(comments, list):
            comment_errors += 1
            continue

        inspected += 1
        author = (issue.get("user") or {}).get("login")
        maint_hit = False
        strict_hit = False
        for c in comments:
            user = c.get("user") or {}
            if user.get("type") == "Bot" or user.get("login") == author:
                continue
            assoc = c.get("author_association")
            if assoc in MAINTAINER_ROLES:
                if not maint_hit:
                    maint_hit = True
                    delta = parse_time(c["created_at"]) - parse_time(issue["created_at"])
                    hours.append(round(max(0.0, delta.total_seconds()) / 3600, 1))
                if assoc in STRICT_MEMBER_ROLES:
                    strict_hit = True
                    break
        if maint_hit:
            replied += 1
        if strict_hit:
            strict_replied += 1

    if inspected == 0:
        return {"sampled": 0, "partial": comment_errors > 0}

    result = {
        "sampled": inspected,
        "maintainer_replied_ratio": round(replied / inspected, 2),
        "median_first_response_hours": statistics.median(hours) if hours else None,
        "closed_ratio": round(closed_count / len(issues), 2),
    }
    if strict_replied != replied:
        result["public_member_replied_ratio"] = round(strict_replied / inspected, 2)
    if comment_errors > 0:
        result["partial"] = True
    return result


def fetch_package_downloads(registry, package):
    """Fetch last-month downloads from public JSON endpoints (no API key needed)."""
    try:
        if registry == "pypi":
            enc = urllib.parse.quote(package.strip(), safe="")
            st, data = http_get(f"https://pypistats.org/api/packages/{enc}/recent")
            if st == 200 and isinstance(data, dict):
                dl = (data.get("data") or {}).get("last_month")
                return {"package": package, "downloads_last_month": dl}
            return {"package": package, "error": api_message(st, data)}
        if registry == "npm":
            enc = urllib.parse.quote(package.strip(), safe="")
            st, data = http_get(f"https://api.npmjs.org/downloads/point/last-month/{enc}")
            if st == 200 and isinstance(data, dict):
                return {"package": package, "downloads_last_month": data.get("downloads")}
            return {"package": package, "error": api_message(st, data)}
    except Exception as e:
        return {"package": package, "error": str(e)}
    return None


def _norm_pkg_key(name):
    return re.sub(r"[-_.]+", "-", name.lower()).strip("-")


def _parse_pkg_specs(specs):
    """Parse ['pkg', 'owner/repo=pkg'] into (explicit_by_repo, by_norm_name)."""
    explicit, by_name = {}, {}
    for item in specs or []:
        if "=" in item:
            repo_part, pkg = item.split("=", 1)
            try:
                o, r = parse_repo(repo_part)
                explicit[f"{o}/{r}".lower()] = pkg.strip()
            except ValueError:
                explicit[repo_part.strip().lower()] = pkg.strip()
        else:
            pkg = item.strip()
            short = pkg.split("/")[-1]  # handles @scope/pkg -> pkg
            by_name[_norm_pkg_key(short)] = pkg
    return explicit, by_name


def _match_pkg(full_name, input_owner_repo, explicit, by_name):
    for key in (full_name.lower(), input_owner_repo.lower()):
        if key in explicit:
            return explicit[key]
    repo_short = full_name.split("/")[-1]
    return by_name.get(_norm_pkg_key(repo_short))


def check(arg, track, with_issues, now=None, pypi_specs=None, npm_specs=None):
    now = now or datetime.now(timezone.utc)
    out = {"input": arg, "checked_at": now.strftime("%Y-%m-%d"), "flags": []}
    flags = out["flags"]
    owner, repo = parse_repo(arg)
    status, r = http_get(f"/repos/{owner}/{repo}")
    if status == 404:
        out["exists"] = False
        flags.append("NOT_FOUND")
        return out
    if status != 200 or not r:
        # Never report a network/permission failure as "repo does not exist".
        raise ApiError(api_message(status, r))

    full = r["full_name"]
    lic = (r.get("license") or {}).get("spdx_id")
    desc = r.get("description")
    stars = r.get("stargazers_count")
    forks = r.get("forks_count")
    watchers = r.get("subscribers_count")
    out.update({
        "exists": True,
        "full_name": full,
        "html_url": r.get("html_url"),
        "homepage": r.get("homepage") or None,
        "description": (desc[:300] + "…") if isinstance(desc, str) and len(desc) > 300 else desc,
        "language": r.get("language"),
        "stars": stars,
        "forks": forks,
        "watchers": watchers,
        "open_issues": r.get("open_issues_count"),
        "archived": r.get("archived", False),
        "fork": r.get("fork", False),
        "parent": (r.get("parent") or {}).get("full_name"),
        "license": lic,
        "topics": r.get("topics", []),
        "created_at": r.get("created_at"),
    })
    if full.lower() != f"{owner}/{repo}".lower():
        flags.append("RENAMED_USE:" + full)
    if r.get("archived"):
        flags.append("ARCHIVED")
    if r.get("fork"):
        flags.append("FORK_OF:" + str(out["parent"]))

    lic_flag = classify_license(lic)
    if lic_flag:
        flags.append(lic_flag)

    if (stars or 0) >= 1000 and (forks or 0) / stars < 0.015 and (watchers is None or watchers / stars < 0.005):
        flags.append("SUSPICIOUS_STAR_RATIO")

    # Commits on default branch (gracefully degrade on sub-request rate limit).
    last_commit = None
    try:
        st, commits = http_get(f"/repos/{full}/commits?per_page=1")
        if st == 200 and commits:
            last_commit = parse_time(commits[0]["commit"]["committer"]["date"])
        elif st == 409:  # empty repository
            flags.append("EMPTY_REPO")
        elif st != 200:
            flags.append("PARTIAL_DATA:commits " + api_message(st, commits))
    except RateLimited:
        flags.append("PARTIAL_DATA:commits rate_limited")
    out["last_commit_at"] = last_commit.strftime("%Y-%m-%d") if last_commit else None
    out["days_since_last_commit"] = days_since(last_commit, now)

    # Latest release (optional signal; 404 simply means repo doesn't cut GitHub Releases).
    rel_time, rel = None, None
    try:
        st, rel = http_get(f"/repos/{full}/releases/latest")
        rel_time = parse_time(rel.get("published_at")) if st == 200 and isinstance(rel, dict) else None
    except RateLimited:
        flags.append("PARTIAL_DATA:releases rate_limited")
    out["latest_release"] = {"tag": rel.get("tag_name"), "published_at": rel.get("published_at")} if rel_time else None
    out["days_since_release"] = days_since(rel_time, now)

    limit = STALE_DAYS.get(track)
    activity = [d for d in (out["days_since_last_commit"], out["days_since_release"]) if d is not None]
    commits_known = not any(f.startswith("PARTIAL_DATA:commits") for f in flags)
    if limit is not None and commits_known and (not activity or min(activity) > limit):
        flags.append(f"STALE_OVER_{limit}D")

    if with_issues:
        try:
            ir = issue_response(full, now)
            out["issue_response"] = ir
            if ir is None:
                flags.append("PARTIAL_DATA:issues")
            else:
                if ir.get("partial"):
                    flags.append("PARTIAL_DATA:issue_comments")
                if ir.get("sampled", 0) >= 5 and ir["maintainer_replied_ratio"] < 0.3 and ir.get("closed_ratio", 0) < 0.5:
                    flags.append("LOW_MAINTAINER_RESPONSE")
        except RateLimited:
            out["issue_response"] = None
            flags.append("PARTIAL_DATA:issues rate_limited")

    input_key = f"{owner}/{repo}"
    if pypi_specs:
        pkg = _match_pkg(full, input_key, *pypi_specs)
        if pkg:
            out["pypi"] = fetch_package_downloads("pypi", pkg)
    if npm_specs:
        pkg = _match_pkg(full, input_key, *npm_specs)
        if pkg:
            out["npm"] = fetch_package_downloads("npm", pkg)

    return out


def _deduplicate_inputs(repos):
    """Preserve input order while deduplicating equivalent owner/repo targets."""
    seen = set()
    unique = []
    for arg in repos:
        try:
            owner, repo = parse_repo(arg)
            key = f"{owner}/{repo}".lower()
            if key in seen:
                continue
            seen.add(key)
        except ValueError:
            pass
        unique.append(arg)
    return unique


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repos", nargs="+", help="GitHub OWNER/REPO or URL(s)")
    p.add_argument("--track", choices=sorted(STALE_DAYS), default="selection",
                   help="learning (365d), selection (90d), or archive (no staleness limit)")
    p.add_argument("--no-issues", action="store_true",
                   help="skip issue-response sampling (saves ~15 calls/repo)")
    p.add_argument("--pypi", nargs="+", metavar="[REPO=]PKG",
                   help="optional PyPI package(s) to attach last-month download counts")
    p.add_argument("--npm", nargs="+", metavar="[REPO=]PKG",
                   help="optional npm package(s) to attach last-month download counts")
    p.add_argument("--workers", type=int, default=4,
                   help="parallel workers when checking multiple repos (default: 4; use 1 for serial)")
    a = p.parse_args(argv)

    with_issues = a.track == "selection" and not a.no_issues
    pypi_specs = _parse_pkg_specs(a.pypi) if a.pypi else None
    npm_specs = _parse_pkg_specs(a.npm) if a.npm else None
    targets = _deduplicate_inputs(a.repos)

    # Run sequentially when workers <= 1 or unauthenticated (avoids bursting 60/hr limit).
    workers = a.workers if (a.workers > 1 and len(targets) > 1 and resolve_token()) else 1

    if workers == 1:
        results = []
        for arg in targets:
            try:
                results.append(check(arg, a.track, with_issues, pypi_specs=pypi_specs, npm_specs=npm_specs))
            except RateLimited as e:
                results.append({"input": arg, "error": str(e)})
                break
            except Exception as e:
                results.append({"input": arg, "error": f"{type(e).__name__}: {e}"})
    else:
        ordered = [None] * len(targets)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, len(targets))) as pool:
            fut_to_idx = {
                pool.submit(check, arg, a.track, with_issues, None, pypi_specs, npm_specs): (idx, arg)
                for idx, arg in enumerate(targets)
            }
            for fut in concurrent.futures.as_completed(fut_to_idx):
                idx, arg = fut_to_idx[fut]
                try:
                    ordered[idx] = fut.result()
                except Exception as e:
                    ordered[idx] = {"input": arg, "error": f"{type(e).__name__}: {e}"}
        results = [r for r in ordered if r is not None]

    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
