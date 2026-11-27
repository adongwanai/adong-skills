#!/usr/bin/env python3
"""github_check.py - verify competition solution repositories and reproducibility signals.

Usage:
  python3 github_check.py OWNER/REPO [URL ...] [--track kaggle|learning|selection] [--no-issues] [--no-tree]

Env:
  GITHUB_TOKEN  optional; raises the GitHub API rate limit from 60 to 5000 requests/hour.

Defaults to --track kaggle:
  - Does NOT penalize post-competition inactivity (solution repos normally stop updating after deadline).
  - Skips wasteful release and issue-response polling to conserve unauthenticated API quota (~2 calls/repo).
  - Inspects root repository tree to surface reproducibility signals (empty/placeholder repos,
    env lockfiles, training vs inference scripts, configs, notebooks) and verifies monorepo subpaths.
  - Handles Gist links cleanly without falsely marking them NOT_FOUND.

Prints a JSON list, one object per input. Standard library only.
"""
import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
STRONG_COPYLEFT = {"AGPL-3.0", "GPL-2.0", "GPL-3.0", "SSPL-1.0"}
WEAK_COPYLEFT = {"LGPL-2.1", "LGPL-3.0", "MPL-2.0", "EPL-2.0", "EUPL-1.2"}
STALE_DAYS = {"kaggle": None, "learning": 365, "selection": 90}
MAINTAINER_ROLES = {"OWNER", "MEMBER", "COLLABORATOR"}
ISSUE_SAMPLE = 15
ISSUE_MIN_AGE_DAYS = 7

ENV_FILES_RE = re.compile(
    r"^(?:requirements[^/]*\.txt|pyproject\.toml|environment\.ya?ml|conda\.ya?ml|"
    r"pipfile|dockerfile|docker-compose\.ya?ml|setup\.py|poetry\.lock|uv\.lock)$",
    re.I,
)
TRAIN_PATH_RE = re.compile(
    r"(?:^|/)(?:train|pretrain|finetune|fit|src|code|scripts|pipeline|main|run|models?|exp|experiments?)(?:[._/-]|$)",
    re.I,
)
INFER_PATH_RE = re.compile(r"(?:^|/)(?:infer|inference|predict|submit|submission|eval)(?:[._/-]|$)", re.I)
CONFIG_PATH_RE = re.compile(r"(?:^|/)(?:configs?|params?|hparams?)(?:[._/-]|$)|\.(?:ya?ml|toml|cfg)$", re.I)
CODE_FILE_RE = re.compile(r"\.(?:py|ipynb|sh|r|jl|cpp|cu)$", re.I)
DOC_ONLY_NAMES = {"readme", "readme.md", "readme.rst", "readme.txt", "license", "license.md", "license.txt", ".gitignore", ".gitattributes"}


class RateLimited(Exception):
    pass


class ApiError(Exception):
    pass


def http_get(path):
    """Return (status, parsed_json_or_None). Replaced by a stub in unit tests."""
    req = urllib.request.Request(
        API + path,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "kaggle-prior-art-github-check",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = None
        msg = (body.get("message") if isinstance(body, dict) else "") or ""
        if (
            e.code == 429
            or (e.code == 403 and e.headers.get("X-RateLimit-Remaining") == "0")
            or (e.code == 403 and e.headers.get("Retry-After"))
            or (e.code == 403 and "rate limit" in msg.lower())
        ):
            raise RateLimited("GitHub API rate limit hit; set GITHUB_TOKEN and retry")
        return e.code, body
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ApiError(f"network error: {e}")


def api_message(status, body):
    msg = body.get("message") if isinstance(body, dict) else None
    return f"HTTP {status}" + (f": {msg[:160]}" if msg else "")


def strip_wrapping_punct(arg):
    s = arg.strip().strip("<>\"'")
    while s and s[-1] in ").,;]>\"'":
        s = s[:-1]
    return s


def parse_target(arg):
    """Parse input into a dict describing either a GitHub repo (+ optional subpath) or a Gist."""
    cleaned = strip_wrapping_punct(arg)
    m_gist = re.match(r"^(?:https?://)?gist\.github\.com/(?:([^/\s#?]+)/)?([0-9a-fA-F]{8,})(?:[/?#].*)?$", cleaned)
    if m_gist:
        return {"kind": "gist", "owner": m_gist.group(1), "gist_id": m_gist.group(2)}

    if re.match(r"^https?://", cleaned, re.I) and not re.search(r"(?:^|//)(?:www\.)?github\.com[:/]", cleaned, re.I):
        raise ValueError("not a GitHub URL: " + arg)
    if "." in cleaned.split("/")[0] and not cleaned.lower().startswith(("github.com/", "www.github.com/", "git@github.com:")):
        raise ValueError("not a GitHub repository: " + arg)

    m_url = re.search(
        r"(?:^|//|@)(?:www\.)?github\.com[/:]([^/\s#?]+)/([^/\s#?]+)(?:/(tree|blob)/([^/\s#?]+)(?:/([^\s#?]+))?)?",
        cleaned,
        re.I,
    )
    if m_url:
        owner, repo = m_url.group(1), m_url.group(2)
        ref = m_url.group(4)
        subpath = m_url.group(5).strip("/") if m_url.group(5) else None
    else:
        parts = [p for p in cleaned.split("/") if p]
        if len(parts) < 2:
            raise ValueError("cannot parse repo: " + arg)
        owner, repo = parts[0], parts[1]
        ref, subpath = None, None

    if owner.lower() in {"orgs", "users", "topics", "search", "settings", "marketplace", "explore"}:
        raise ValueError("not a repository URL: " + arg)
    repo = repo[:-4] if repo.lower().endswith(".git") else repo
    if not owner or not repo:
        raise ValueError("cannot parse repo: " + arg)
    return {"kind": "repo", "owner": owner, "repo": repo, "ref": ref, "subpath": subpath}


def parse_repo(arg):
    t = parse_target(arg)
    if t["kind"] != "repo":
        raise ValueError("not a standard repository: " + arg)
    return t["owner"], t["repo"]


def parse_time(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if s else None


def days_since(dt, now):
    return None if dt is None else (now - dt).days


def inspect_tree(full_name, branch):
    """Inspect top-level tree to evaluate competition code completeness (1 API call)."""
    ref = branch or "HEAD"
    st, data = http_get(f"/repos/{full_name}/git/trees/{ref}")
    if st != 200 or not isinstance(data, dict) or not isinstance(data.get("tree"), list):
        return None
    entries = data["tree"]
    names = [e.get("path", "") for e in entries if e.get("path")]
    has_subdirs = any(e.get("type") == "tree" and not e.get("path", "").startswith(".") for e in entries)
    has_readme = any(n.lower().startswith("readme") for n in names)
    has_env = any(ENV_FILES_RE.match(n) for n in names)
    has_train = any(TRAIN_PATH_RE.search(n) for n in names)
    has_infer = any(INFER_PATH_RE.search(n) for n in names)
    has_notebooks = any(n.lower().endswith(".ipynb") or n.lower() in {"notebooks", "notebook", "kernels"} for n in names)
    has_configs = any(CONFIG_PATH_RE.search(n) for n in names)
    has_code_files = any(CODE_FILE_RE.search(n) for n in names)

    substantive = [n for n in names if n.lower() not in DOC_ONLY_NAMES and not n.startswith(".")]
    placeholder = len(substantive) == 0 and not has_subdirs and not has_code_files

    return {
        "root_entries": len(names),
        "has_readme": has_readme,
        "has_env_spec": has_env,
        "has_train_entry": has_train,
        "has_inference_entry": has_infer,
        "has_notebooks": has_notebooks,
        "has_configs": has_configs,
        "placeholder_suspect": placeholder,
    }


def verify_subpath(full_name, subpath, ref):
    q = f"?ref={ref}" if ref else ""
    st, _ = http_get(f"/repos/{full_name}/contents/{subpath}{q}")
    if st == 200:
        return True
    if st == 404:
        return False
    return None


def issue_response(full_name, now):
    status, issues = http_get(f"/repos/{full_name}/issues?state=all&per_page=50&sort=created&direction=desc")
    if status != 200 or not isinstance(issues, list):
        return None
    issues = [
        i for i in issues
        if "pull_request" not in i and days_since(parse_time(i["created_at"]), now) >= ISSUE_MIN_AGE_DAYS
    ][:ISSUE_SAMPLE]
    if not issues:
        return {"sampled": 0}
    hours, replied = [], 0
    for issue in issues:
        if issue.get("comments", 0) == 0:
            continue
        st, comments = http_get(f"/repos/{full_name}/issues/{issue['number']}/comments?per_page=30")
        if st != 200 or not isinstance(comments, list):
            continue
        author = (issue.get("user") or {}).get("login")
        for c in comments:
            user = c.get("user") or {}
            if (
                c.get("author_association") in MAINTAINER_ROLES
                and user.get("type") != "Bot"
                and user.get("login") != author
            ):
                replied += 1
                delta = parse_time(c["created_at"]) - parse_time(issue["created_at"])
                hours.append(round(delta.total_seconds() / 3600, 1))
                break
    return {
        "sampled": len(issues),
        "maintainer_replied_ratio": round(replied / len(issues), 2),
        "median_first_response_hours": statistics.median(hours) if hours else None,
    }


def check_gist(target, arg, now):
    gid = target["gist_id"]
    out = {"input": arg, "kind": "gist", "checked_at": now.strftime("%Y-%m-%d"), "flags": []}
    st, g = http_get(f"/gists/{gid}")
    if st == 404:
        out["exists"] = False
        out["flags"].append("NOT_FOUND")
        return out
    if st != 200 or not isinstance(g, dict):
        raise ApiError(api_message(st, g))
    files = list((g.get("files") or {}).keys())
    out.update({
        "exists": True,
        "html_url": g.get("html_url"),
        "description": g.get("description"),
        "files": files,
        "created_at": g.get("created_at"),
        "updated_at": g.get("updated_at"),
    })
    if not files:
        out["flags"].append("EMPTY_GIST")
    out["flags"].append("NO_LICENSE")
    return out


def check(arg, track="kaggle", with_issues=False, now=None, with_tree=None):
    now = now or datetime.now(timezone.utc)
    if with_tree is None:
        with_tree = (track == "kaggle")
    target = parse_target(arg)
    if target["kind"] == "gist":
        return check_gist(target, arg, now)

    owner, repo = target["owner"], target["repo"]
    out = {"input": arg, "checked_at": now.strftime("%Y-%m-%d"), "flags": []}
    flags = out["flags"]
    status, r = http_get(f"/repos/{owner}/{repo}")
    if status == 404:
        out["exists"] = False
        flags.append("NOT_FOUND")
        return out
    if status != 200 or not r:
        raise ApiError(api_message(status, r))

    full = r["full_name"]
    lic = (r.get("license") or {}).get("spdx_id")
    size_kb = r.get("size")
    out.update({
        "exists": True,
        "full_name": full,
        "html_url": r.get("html_url"),
        "description": r.get("description"),
        "stars": r.get("stargazers_count"),
        "forks": r.get("forks_count"),
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
    if size_kb == 0:
        flags.append("EMPTY_REPO")
    if not lic:
        flags.append("NO_LICENSE")
    elif lic == "NOASSERTION":
        flags.append("CUSTOM_LICENSE_READ_IT")
    elif lic in STRONG_COPYLEFT:
        flags.append("STRONG_COPYLEFT:" + lic)
    elif lic in WEAK_COPYLEFT:
        flags.append("WEAK_COPYLEFT:" + lic)

    last_commit = None
    if track == "kaggle" and r.get("pushed_at"):
        last_commit = parse_time(r.get("pushed_at"))
    else:
        st, commits = http_get(f"/repos/{full}/commits?per_page=1")
        if st == 200 and commits:
            last_commit = parse_time(commits[0]["commit"]["committer"]["date"])
        elif st == 409:
            if "EMPTY_REPO" not in flags:
                flags.append("EMPTY_REPO")
        elif st != 200:
            flags.append("PARTIAL_DATA:commits " + api_message(st, commits))

    out["last_commit_at"] = last_commit.strftime("%Y-%m-%d") if last_commit else None
    out["days_since_last_commit"] = days_since(last_commit, now)

    if track != "kaggle":
        st, rel = http_get(f"/repos/{full}/releases/latest")
        rel_time = parse_time(rel.get("published_at")) if st == 200 and rel else None
        out["latest_release"] = (
            {"tag": rel.get("tag_name"), "published_at": rel.get("published_at")} if rel_time else None
        )
        out["days_since_release"] = days_since(rel_time, now)
    else:
        out["latest_release"] = None
        out["days_since_release"] = None

    limit = STALE_DAYS.get(track)
    activity = [d for d in (out["days_since_last_commit"], out["days_since_release"]) if d is not None]
    commits_known = not any(f.startswith("PARTIAL_DATA:commits") for f in flags)
    if limit is not None and commits_known and (not activity or min(activity) > limit):
        flags.append(f"STALE_OVER_{limit}D")

    if with_tree and size_kb != 0:
        repro = inspect_tree(full, r.get("default_branch"))
        if repro is not None:
            out["reproducibility"] = repro
            if repro["placeholder_suspect"] and "EMPTY_REPO" not in flags:
                flags.append("PLACEHOLDER_NO_CODE")

    if target.get("subpath"):
        out["subpath"] = target["subpath"]
        sub_ok = verify_subpath(full, target["subpath"], target.get("ref") or r.get("default_branch"))
        out["subpath_exists"] = sub_ok
        if sub_ok is False:
            flags.append("SUBPATH_NOT_FOUND:" + target["subpath"])

    if with_issues:
        ir = issue_response(full, now)
        out["issue_response"] = ir
        if ir and ir.get("sampled", 0) >= 5 and ir["maintainer_replied_ratio"] < 0.3:
            flags.append("LOW_MAINTAINER_RESPONSE")
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repos", nargs="+", help="GitHub OWNER/REPO, repository URL, monorepo subpath URL, or Gist URL")
    p.add_argument("--track", choices=sorted(STALE_DAYS), default="kaggle",
                   help="evaluation profile (default: kaggle)")
    p.add_argument("--no-issues", action="store_true", help="skip issue-response sampling in selection track")
    p.add_argument("--no-tree", action="store_true", help="skip repository root tree reproducibility inspection")
    a = p.parse_args(argv)
    with_issues = a.track == "selection" and not a.no_issues
    with_tree = a.track == "kaggle" and not a.no_tree
    results = []
    for arg in a.repos:
        try:
            results.append(check(arg, a.track, with_issues, with_tree=with_tree))
        except RateLimited as e:
            results.append({"input": arg, "error": str(e)})
            break
        except Exception as e:
            results.append({"input": arg, "error": f"{type(e).__name__}: {e}"})
    json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
