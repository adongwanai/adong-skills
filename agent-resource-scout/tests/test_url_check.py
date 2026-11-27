import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import url_check as uc


class TestUrlCheck(unittest.TestCase):
    def setUp(self):
        self._orig_fetch = uc.http_fetch

    def tearDown(self):
        uc.http_fetch = self._orig_fetch

    def test_valid_course_page_extracts_title_and_description(self):
        html = (
            b"<html><head><title>  HF Agents Course  </title>"
            b'<meta name="description" content="Learn to build agents step by step.">'
            b'<meta property="article:published_time" content="2026-02-10T00:00:00Z">'
            b"</head><body><h1>Welcome</h1></body></html>"
        )
        uc.http_fetch = lambda url, timeout=12: (200, url, "text/html; charset=utf-8", html, None)
        out = uc.check_url("https://huggingface.co/learn/agents-course")
        self.assertTrue(out["reachable"])
        self.assertEqual(out["title"], "HF Agents Course")
        self.assertEqual(out["description"], "Learn to build agents step by step.")
        self.assertEqual(out["published_at"], "2026-02-10T00:00:00Z")
        self.assertEqual(out["flags"], [])

    def test_mirror_site_and_promo_funnel_flagged(self):
        html = (
            "<html><head><title>某搬运教程</title></head>"
            "<body><p>干货分享，关注公众号并回复 666 领取完整源码，或者扫码进群领资料！</p></body></html>"
        ).encode("utf-8")
        uc.http_fetch = lambda url, timeout=12: (200, url, "text/html", html, None)
        out = uc.check_url("https://blog.csdn.net/someone/article/details/123")
        self.assertIn("REPOST_OR_MIRROR_SITE:csdn.net", out["flags"])
        self.assertIn("PROMO_FUNNEL_DETECTED:公众号回复引流", out["flags"])
        self.assertIn("PROMO_FUNNEL_DETECTED:扫码领", out["flags"])

    def test_dead_link_bot_wall_and_cross_domain_redirect(self):
        uc.http_fetch = lambda url, timeout=12: (404, url, "text/html", b"not found", None)
        dead = uc.check_url("https://example.com/missing")
        self.assertFalse(dead["reachable"])
        self.assertIn("DEAD_LINK:HTTP_404", dead["flags"])

        uc.http_fetch = lambda url, timeout=12: (403, url, "text/html", b"cloudflare", None)
        wall = uc.check_url("https://www.reddit.com/r/LocalLLaMA")
        self.assertIsNone(wall["reachable"])
        self.assertIn("BOT_WALL_OR_RESTRICTED:HTTP_403", wall["flags"])

        uc.http_fetch = lambda url, timeout=12: (
            200, "https://huggingface.co/papers/trending", "text/html", b"<title>Trending Papers</title>", None
        )
        redir = uc.check_url("https://paperswithcode.com/")
        self.assertTrue(redir["reachable"])
        self.assertIn("REDIRECTED_DOMAIN:huggingface.co", redir["flags"])

    def test_cli_deduplicates_urls(self):
        uc.http_fetch = lambda url, timeout=12: (200, url, "text/plain", b"# LLMs.txt index\n", None)
        buf = io.StringIO()
        with redirect_stdout(buf):
            uc.main(["https://modelcontextprotocol.io/llms.txt", "https://modelcontextprotocol.io/llms.txt"])
        res = json.loads(buf.getvalue())
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["preview"], "# LLMs.txt index")


if __name__ == "__main__":
    unittest.main()
