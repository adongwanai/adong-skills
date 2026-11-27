import io
import json
import os
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from datetime import datetime, timezone
from email.message import Message
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import github_check as gc

NOW = datetime(2026, 11, 27, tzinfo=timezone.utc)


def stub(routes):
    def fake(path):
        for prefix, resp in routes.items():
            if path.startswith(prefix):
                if isinstance(resp, Exception):
                    raise resp
                return resp
        return 404, None
    return fake


def repo(full, **kw):
    base = {
        "full_name": full,
        "html_url": "https://github.com/" + full,
        "homepage": "https://docs.example.com",
        "language": "Python",
        "stargazers_count": 1200,
        "forks_count": 120,
        "subscribers_count": 30,
        "open_issues_count": 12,
        "archived": False,
        "fork": False,
        "license": {"spdx_id": "MIT"},
        "topics": ["agents"],
        "created_at": "2024-01-01T00:00:00Z",
    }
    base.update(kw)
    return 200, base


def commit(date):
    return 200, [{"commit": {"committer": {"date": date}}}]


class FakeHttpResponse:
    def __init__(self, status, payload):
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestGithubCheck(unittest.TestCase):
    def setUp(self):
        self._orig_http_get = gc.http_get
        self._orig_resolve_token = gc.resolve_token
        gc.resolve_token = lambda: None

    def tearDown(self):
        gc.http_get = self._orig_http_get
        gc.resolve_token = self._orig_resolve_token

    def test_not_found(self):
        gc.http_get = stub({})
        out = gc.check("ghost/nothing", "selection", False, NOW)
        self.assertFalse(out["exists"])
        self.assertIn("NOT_FOUND", out["flags"])

    def test_parse_repo_rejects_non_github_urls_and_domains(self):
        with self.assertRaises(ValueError):
            gc.parse_repo("https://huggingface.co/learn/agents-course")
        with self.assertRaises(ValueError):
            gc.parse_repo("huggingface.co/huggingface/smolagents")
        self.assertEqual(gc.parse_repo("https://github.com/vercel/next.js.git"), ("vercel", "next.js"))
        self.assertEqual(gc.parse_repo("owner/repo#readme"), ("owner", "repo"))

    def test_active_mit_selection_and_package_downloads(self):
        gc.http_get = stub({
            "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
            "/repos/a/b/releases/latest": (200, {"tag_name": "v1", "published_at": "2026-11-01T00:00:00Z"}),
            "/repos/a/b": repo("a/b"),
            "https://pypistats.org/api/packages/b/recent": (200, {"data": {"last_month": 350000}}),
        })
        pypi_specs = gc._parse_pkg_specs(["b"])
        out = gc.check("https://github.com/a/b.git", "selection", False, NOW, pypi_specs=pypi_specs)
        self.assertTrue(out["exists"])
        self.assertEqual(out["flags"], [])
        self.assertEqual(out["days_since_last_commit"], 7)
        self.assertEqual(out["latest_release"]["tag"], "v1")
        self.assertEqual(out["homepage"], "https://docs.example.com")
        self.assertEqual(out["pypi"]["downloads_last_month"], 350000)

    def test_stale_depends_on_track(self):
        routes = {"/repos/a/b/commits": commit("2026-05-01T00:00:00Z"), "/repos/a/b": repo("a/b")}
        gc.http_get = stub(routes)
        self.assertIn("STALE_OVER_90D", gc.check("a/b", "selection", False, NOW)["flags"])
        self.assertFalse(any(f.startswith("STALE") for f in gc.check("a/b", "learning", False, NOW)["flags"]))
        self.assertFalse(any(f.startswith("STALE") for f in gc.check("a/b", "archive", False, NOW)["flags"]))
        self.assertFalse(any(f.startswith("STALE") for f in gc.check("a/b", "kaggle", False, NOW)["flags"]))

    def test_license_variants_rename_fork_archive_and_star_farming(self):
        gc.http_get = stub({
            "/repos/New/b/commits": commit("2026-11-20T00:00:00Z"),
            "/repos/old/b": repo(
                "New/b",
                license={"spdx_id": "AGPL-3.0-only"},
                archived=True,
                fork=True,
                parent={"full_name": "orig/b"},
                stargazers_count=5000,
                forks_count=10,
                subscribers_count=3,
            ),
        })
        f = gc.check("old/b", "selection", False, NOW)["flags"]
        self.assertIn("RENAMED_USE:New/b", f)
        self.assertIn("ARCHIVED", f)
        self.assertIn("FORK_OF:orig/b", f)
        self.assertIn("STRONG_COPYLEFT:AGPL-3.0-only", f)
        self.assertIn("SUSPICIOUS_STAR_RATIO", f)

        gc.http_get = stub({
            "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
            "/repos/a/b": repo("a/b", license={"spdx_id": "CC-BY-NC-4.0"}),
        })
        self.assertIn(
            "NON_COMMERCIAL_OR_SOURCE_AVAILABLE:CC-BY-NC-4.0",
            gc.check("a/b", "selection", False, NOW)["flags"],
        )

        gc.http_get = stub({
            "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
            "/repos/a/b": repo("a/b", license={"spdx_id": "NOASSERTION"}),
        })
        self.assertIn("CUSTOM_LICENSE_READ_IT", gc.check("a/b", "selection", False, NOW)["flags"])

        gc.http_get = stub({
            "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
            "/repos/a/b": repo("a/b", license=None),
        })
        self.assertIn("NO_LICENSE", gc.check("a/b", "selection", False, NOW)["flags"])

    def test_issue_response_via_search_and_fallback(self):
        def issue(n, created, comments=1, state="open"):
            return {
                "number": n, "created_at": created, "comments": comments,
                "state": state, "user": {"login": "asker"},
            }

        issues = [
            issue(1, "2026-11-25T00:00:00Z"),  # too new -> ignored on fallback
            {"number": 2, "pull_request": {}, "created_at": "2026-10-01T00:00:00Z"},  # PR -> ignored
            issue(3, "2026-10-01T00:00:00Z", state="closed"),
            issue(4, "2026-10-02T00:00:00Z"),
            issue(5, "2026-10-03T00:00:00Z"),
            issue(6, "2026-10-04T00:00:00Z", 0, state="closed"),
            issue(7, "2026-10-05T00:00:00Z"),
            issue(8, "2026-10-06T00:00:00Z"),
            issue(9, "2026-10-07T00:00:00Z"),  # comment endpoint returns 500 -> excluded from denominator
        ]
        maint = lambda t: {"author_association": "MEMBER", "user": {"login": "dev", "type": "User"}, "created_at": t}
        contrib = lambda t: {"author_association": "CONTRIBUTOR", "user": {"login": "core_priv", "type": "User"}, "created_at": t}
        bot = {"author_association": "MEMBER", "user": {"login": "stale[bot]", "type": "Bot"}, "created_at": "2026-10-02T00:00:00Z"}

        # Fallback route (/search/issues returns 404 in stub -> falls back to /repos/a/b/issues)
        gc.http_get = stub({
            "/repos/a/b/issues/3/comments": (200, [maint("2026-10-01T10:00:00Z")]),
            "/repos/a/b/issues/4/comments": (200, [bot]),
            "/repos/a/b/issues/5/comments": (200, [contrib("2026-10-03T04:00:00Z")]),
            "/repos/a/b/issues/7/comments": (200, [maint("2026-10-05T02:00:00Z")]),
            "/repos/a/b/issues/8/comments": (200, [{"author_association": "OWNER", "user": {"login": "asker"}, "created_at": "2026-10-06T01:00:00Z"}]),
            "/repos/a/b/issues/9/comments": (500, None),
            "/repos/a/b/issues": (200, issues),
            "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
            "/repos/a/b": repo("a/b"),
        })
        out = gc.check("a/b", "selection", True, NOW)
        ir = out["issue_response"]
        self.assertEqual(ir["sampled"], 6)  # 3,4,5,6,7,8 inspected; #9 errored out of denominator
        self.assertEqual(ir["maintainer_replied_ratio"], round(3 / 6, 2))  # 3 (MEMBER), 5 (CONTRIBUTOR), 7 (MEMBER)
        self.assertEqual(ir["public_member_replied_ratio"], round(2 / 6, 2))
        self.assertEqual(ir["median_first_response_hours"], 4.0)  # median of 10h, 4h, 2h
        self.assertTrue(ir["partial"])
        self.assertIn("PARTIAL_DATA:issue_comments", out["flags"])
        self.assertNotIn("LOW_MAINTAINER_RESPONSE", out["flags"])

    def test_permission_error_is_not_not_found(self):
        gc.http_get = stub({"/repos/a/b": (403, {"message": "access not enabled"})})
        buf = io.StringIO()
        with redirect_stdout(buf):
            gc.main(["a/b", "--no-issues"])
        res = json.loads(buf.getvalue())
        self.assertIn("error", res[0])
        self.assertIn("403", res[0]["error"])
        self.assertNotIn("flags", res[0])

    def test_commit_failure_and_empty_repo(self):
        gc.http_get = stub({"/repos/a/b/commits": (500, None), "/repos/a/b": repo("a/b")})
        f = gc.check("a/b", "selection", False, NOW)["flags"]
        self.assertTrue(any(x.startswith("PARTIAL_DATA:commits") for x in f))
        self.assertFalse(any(x.startswith("STALE") for x in f))

        gc.http_get = stub({"/repos/a/b/commits": (409, None), "/repos/a/b": repo("a/b")})
        f = gc.check("a/b", "selection", False, NOW)["flags"]
        self.assertIn("EMPTY_REPO", f)
        self.assertIn("STALE_OVER_90D", f)

    def test_rate_limit_on_subendpoint_preserves_repo_data_and_deduplicates(self):
        gc.http_get = stub({
            "/repos/a/b/commits": commit("2026-11-20T00:00:00Z"),
            "/repos/a/b/releases/latest": gc.RateLimited("secondary limit"),
            "/repos/a/b": repo("a/b"),
        })
        buf = io.StringIO()
        with redirect_stdout(buf):
            gc.main(["a/b", "https://github.com/A/B.git", "--no-issues"])
        res = json.loads(buf.getvalue())
        self.assertEqual(len(res), 1)
        self.assertTrue(res[0]["exists"])
        self.assertIn("PARTIAL_DATA:releases rate_limited", res[0]["flags"])

    def test_real_http_get_secondary_rate_limit_and_token_isolation(self):
        seen_Requests = []

        def fake_urlopen(req, timeout=20):
            seen_Requests.append(req)
            if "pypistats.org" in req.full_url:
                return FakeHttpResponse(200, {"data": {"last_month": 42}})
            hdrs = Message()
            hdrs["Retry-After"] = "60"
            raise urllib.error.HTTPError(
                req.full_url, 403, "Forbidden", hdrs,
                io.BytesIO(b'{"message": "You have exceeded a secondary rate limit."}'),
            )

        gc.resolve_token = lambda: "ghp_secret_token"
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            # External registry MUST NOT receive GitHub Authorization header
            st, body = self._orig_http_get("https://pypistats.org/api/packages/foo/recent")
            self.assertEqual(st, 200)
            self.assertIsNone(seen_Requests[0].get_header("Authorization"))

            # GitHub secondary rate limit raises RateLimited even without X-RateLimit-Remaining == 0
            with self.assertRaises(gc.RateLimited):
                self._orig_http_get("/repos/a/b")
            self.assertEqual(seen_Requests[1].get_header("Authorization"), "Bearer ghp_secret_token")


if __name__ == "__main__":
    unittest.main()
