import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import github_check as gc

NOW = datetime(2026, 11, 27, tzinfo=timezone.utc)


def stub(routes, call_log=None):
    def fake(path):
        if call_log is not None:
            call_log.append(path)
        # Match longest prefix first so specific sub-routes win over '/repos/a/b'
        for prefix in sorted(routes, key=len, reverse=True):
            if path.startswith(prefix):
                return routes[prefix]
        return 404, None
    return fake


def repo(full, **kw):
    base = {
        "full_name": full,
        "html_url": "https://github.com/" + full,
        "stargazers_count": 100,
        "forks_count": 5,
        "size": 512,
        "default_branch": "main",
        "pushed_at": "2026-11-20T00:00:00Z",
        "archived": False,
        "fork": False,
        "license": {"spdx_id": "MIT"},
        "topics": [],
        "created_at": "2024-01-01T00:00:00Z",
    }
    base.update(kw)
    return 200, base


def commit(date):
    return 200, [{"commit": {"committer": {"date": date}}}]


def tree(*entries):
    return 200, {"tree": [{"path": p, "type": "tree" if p.endswith("/") else "blob"} for p in entries]}


def test_not_found(monkeypatch):
    monkeypatch.setattr(gc, "http_get", stub({}))
    out = gc.check("ghost/nothing", "kaggle", False, NOW)
    assert out["exists"] is False and "NOT_FOUND" in out["flags"]


def test_default_track_is_kaggle_and_saves_quota(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/a/b/git/trees/main": tree("README.md", "requirements.txt", "train.py", "infer.py"),
        "/repos/a/b": repo("a/b", pushed_at="2023-05-01T00:00:00Z"),
    }, calls))
    gc.main(["a/b"])  # default track should be 'kaggle'
    res = json.loads(capsys.readouterr().out)[0]
    assert res["exists"] is True
    assert res["flags"] == []  # 3+ year old Kaggle repo is NOT flagged stale
    assert len(calls) == 2     # only /repos/a/b and /git/trees/main (no releases or issues)
    rep = res["reproducibility"]
    assert rep["has_readme"] and rep["has_env_spec"] and rep["has_train_entry"] and rep["has_inference_entry"]
    assert rep["placeholder_suspect"] is False


def test_placeholder_and_empty_repo_detection(monkeypatch):
    # Repo with only README.md ("code coming soon") and LICENSE -> PLACEHOLDER_NO_CODE
    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/a/coming-soon/git/trees/main": tree("README.md", "LICENSE"),
        "/repos/a/coming-soon": repo("a/coming-soon"),
    }))
    out = gc.check("a/coming-soon", "kaggle", False, NOW)
    assert "PLACEHOLDER_NO_CODE" in out["flags"]

    # Zero-byte repository -> EMPTY_REPO
    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/a/empty": repo("a/empty", size=0),
    }))
    out_empty = gc.check("a/empty", "kaggle", False, NOW)
    assert "EMPTY_REPO" in out_empty["flags"]


def test_subpath_gist_and_url_hygiene(monkeypatch):
    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/gm/monorepo/contents/2024-hms": (200, [{"name": "train.py"}]),
        "/repos/gm/monorepo/contents/missing": (404, {"message": "Not Found"}),
        "/repos/gm/monorepo": repo("gm/monorepo"),
        "/gists/abcdef123456": (200, {
            "html_url": "https://gist.github.com/u/abcdef123456",
            "description": "QWK postproc",
            "files": {"rounder.py": {}},
            "created_at": "2024-07-01T00:00:00Z",
            "updated_at": "2024-07-02T00:00:00Z",
        }),
    }))
    # Trailing Markdown parenthesis + valid subpath
    ok = gc.check("https://github.com/gm/monorepo/tree/main/2024-hms).", "kaggle", False, NOW, with_tree=False)
    assert ok["subpath"] == "2024-hms" and ok["subpath_exists"] is True and ok["flags"] == []

    # Broken monorepo subpath
    bad = gc.check("https://github.com/gm/monorepo/tree/main/missing", "kaggle", False, NOW, with_tree=False)
    assert "SUBPATH_NOT_FOUND:missing" in bad["flags"]

    # Valid Gist is NOT treated as NOT_FOUND repo
    gist = gc.check("https://gist.github.com/u/abcdef123456", "kaggle", False, NOW)
    assert gist["kind"] == "gist" and gist["exists"] is True and gist["files"] == ["rounder.py"]

    # Non-GitHub domain raises ValueError rather than faking NOT_FOUND
    try:
        gc.check("https://gitlab.com/foo/bar", "kaggle", False, NOW)
    except ValueError as e:
        assert "not a GitHub" in str(e)
    else:
        raise AssertionError("expected ValueError for non-GitHub URL")


def test_active_mit_selection(monkeypatch):
    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
        "/repos/a/b/releases/latest": (200, {"tag_name": "v1", "published_at": "2026-11-01T00:00:00Z"}),
        "/repos/a/b": repo("a/b"),
    }))
    out = gc.check("https://github.com/a/b.git", "selection", False, NOW)
    assert out["exists"] and out["flags"] == [], out
    assert out["days_since_last_commit"] == 7 and out["latest_release"]["tag"] == "v1"


def test_stale_depends_on_track(monkeypatch):
    routes = {"/repos/a/b/commits": commit("2026-05-01T00:00:00Z"), "/repos/a/b": repo("a/b", pushed_at="2026-05-01T00:00:00Z")}
    monkeypatch.setattr(gc, "http_get", stub(routes))
    assert "STALE_OVER_90D" in gc.check("a/b", "selection", False, NOW)["flags"]
    assert not any(f.startswith("STALE") for f in gc.check("a/b", "learning", False, NOW)["flags"])
    assert not any(f.startswith("STALE") for f in gc.check("a/b", "kaggle", False, NOW)["flags"])


def test_license_rename_fork_archive_flags(monkeypatch):
    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/New/b/commits": commit("2026-11-20T00:00:00Z"),
        "/repos/old/b": repo("New/b", license={"spdx_id": "AGPL-3.0"}, archived=True,
                             fork=True, parent={"full_name": "orig/b"}),
    }))
    f = gc.check("old/b", "selection", False, NOW)["flags"]
    assert "RENAMED_USE:New/b" in f and "ARCHIVED" in f and "FORK_OF:orig/b" in f
    assert "STRONG_COPYLEFT:AGPL-3.0" in f

    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
        "/repos/a/b": repo("a/b", license={"spdx_id": "NOASSERTION"}),
    }))
    assert "CUSTOM_LICENSE_READ_IT" in gc.check("a/b", "selection", False, NOW)["flags"]

    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
        "/repos/a/b": repo("a/b", license=None),
    }))
    assert "NO_LICENSE" in gc.check("a/b", "selection", False, NOW)["flags"]


def test_issue_response(monkeypatch):
    def issue(n, created, comments=1):
        return {"number": n, "created_at": created, "comments": comments, "user": {"login": "asker"}}

    issues = [
        issue(1, "2026-11-25T00:00:00Z"),
        {"number": 2, "pull_request": {}, "created_at": "2026-10-01T00:00:00Z"},
        issue(3, "2026-10-01T00:00:00Z"), issue(4, "2026-10-02T00:00:00Z"),
        issue(5, "2026-10-03T00:00:00Z"), issue(6, "2026-10-04T00:00:00Z", 0),
        issue(7, "2026-10-05T00:00:00Z"), issue(8, "2026-10-06T00:00:00Z"),
    ]
    maint = lambda t: {"author_association": "MEMBER", "user": {"login": "dev", "type": "User"}, "created_at": t}
    bot = {"author_association": "MEMBER", "user": {"login": "stale[bot]", "type": "Bot"}, "created_at": "2026-10-02T00:00:00Z"}
    monkeypatch.setattr(gc, "http_get", stub({
        "/repos/a/b/issues/3/comments": (200, [maint("2026-10-01T10:00:00Z")]),
        "/repos/a/b/issues/4/comments": (200, [bot]),
        "/repos/a/b/issues/5/comments": (200, [{"author_association": "NONE", "user": {"login": "x"}, "created_at": "2026-10-03T01:00:00Z"}]),
        "/repos/a/b/issues/7/comments": (200, [maint("2026-10-05T02:00:00Z")]),
        "/repos/a/b/issues/8/comments": (200, [{"author_association": "OWNER", "user": {"login": "asker"}, "created_at": "2026-10-06T01:00:00Z"}]),
        "/repos/a/b/issues": (200, issues),
        "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
        "/repos/a/b": repo("a/b"),
    }))
    out = gc.check("a/b", "selection", True, NOW)
    ir = out["issue_response"]
    assert ir["sampled"] == 6
    assert ir["maintainer_replied_ratio"] == round(2 / 6, 2)
    assert ir["median_first_response_hours"] == 6.0
    assert "LOW_MAINTAINER_RESPONSE" not in out["flags"]


def test_permission_error_and_partial_commits(monkeypatch, capsys):
    monkeypatch.setattr(gc, "http_get", stub({"/repos/a/b": (403, {"message": "access not enabled"})}))
    gc.main(["a/b", "--no-issues"])
    res = json.loads(capsys.readouterr().out)
    assert "error" in res[0] and "403" in res[0]["error"] and "flags" not in res[0]

    monkeypatch.setattr(gc, "http_get", stub({"/repos/a/b/commits": (500, None), "/repos/a/b": repo("a/b", pushed_at=None)}))
    f = gc.check("a/b", "selection", False, NOW)["flags"]
    assert any(x.startswith("PARTIAL_DATA:commits") for x in f)
    assert not any(x.startswith("STALE") for x in f)


def test_rate_limit_stops_batch(monkeypatch, capsys):
    def boom(path):
        raise gc.RateLimited("limit")
    monkeypatch.setattr(gc, "http_get", boom)
    gc.main(["a/b", "c/d", "--no-issues"])
    res = json.loads(capsys.readouterr().out)
    assert len(res) == 1 and "error" in res[0]
