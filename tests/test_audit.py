"""Offline tests: a tiny local site with known problems, served on 127.0.0.1. No network, no keys.

    python3 -m unittest discover -s tests -v
"""
import http.server
import os
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import audit  # noqa: E402

PAGES = {
    "/": '<html><head><title>Acme CRM</title><meta name="description" content="CRM for small teams."><link rel="canonical" href="/">'
         '<meta name="viewport" content="width=device-width"><link rel="icon" href="/f.ico"></head><body><h1>Acme</h1>'
         '<a href="/pricing">Pricing</a> <a href="/about">click here</a> <a href="/gone">old</a> <a href="/old">moved</a> <a href="/app">app</a>'
         '<img src="/hero.png"><script type="application/ld+json">{"@type": "Organization",}</script></body></html>',
    "/pricing": '<html lang="en"><head><title>Acme CRM</title><link rel="canonical" href="/pricing"><meta name="viewport" content="x"></head>'
                '<body><h1>Pricing</h1><h1>Plans</h1><h2>Solo</h2><h4>Notes</h4><p>' + "word " * 120 + "</p></body></html>",
    "/about": '<html lang="en"><head><title>About Acme</title><meta name="robots" content="noindex"></head><body><h1>About</h1></body></html>',
    "/app": '<html lang="en"><head><title>App</title><link rel="canonical" href="/app"><meta name="viewport" content="x"></head><body><div id="root"></div><script src="/a.js"></script></body></html>',
    "/robots.txt": "User-agent: *\nDisallow: /private/\n\nUser-agent: GPTBot\nDisallow: /\n\nSitemap: http://127.0.0.1:{port}/sitemap.xml\n",
    "/sitemap.xml": '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>http://127.0.0.1:{port}/pricing</loc></url></urlset>',
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/old":
            self.send_response(301)
            self.send_header("Location", "/pricing")
            self.end_headers()
            return
        body = PAGES.get(path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        body = body.replace("{port}", str(self.server.server_port)).encode()
        self.send_response(200)
        ctype = "text/plain" if path.endswith(".txt") else "application/xml" if path.endswith(".xml") else "text/html; charset=utf-8"
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class AuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % cls.server.server_port
        cls.devnull = open(os.devnull, "w")
        cls.audit = audit.Audit(base, allow_local=True, log=cls.devnull).run()
        cls.rules = {f["rule"]: f for f in cls.audit.findings}

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.devnull.close()

    def test_finds_known_problems(self):
        for rule in ("http_errors", "noindex", "title_duplicate", "meta_missing", "h1_multiple", "heading_skip",
                     "js_only", "jsonld_invalid", "images_alt", "generic_anchors", "redirect_chains", "lang_missing",
                     "og_missing", "ai_bots_blocked", "llms_missing"):
            self.assertIn(rule, self.rules, rule)
        self.assertIn("/gone", self.rules["http_errors"]["urls"])
        self.assertIn("GPTBot", self.rules["ai_bots_blocked"]["evidence"])

    def test_does_not_report_what_is_fine(self):
        for rule in ("robots_blocks_search", "sitemap_missing", "soft_404", "favicon_missing"):
            self.assertNotIn(rule, self.rules, rule)

    def test_report_and_json(self):
        md = self.audit.markdown()
        self.assertIn("# SEO audit:", md)
        self.assertIn("onpageagent.com", md)
        data = self.audit.as_json()
        self.assertTrue(0 <= data["score"] <= 100)
        self.assertEqual(self.audit.findings[0]["impact"], max(f["impact"] for f in self.audit.findings), "highest impact first")

    def test_refuses_private_addresses_by_default(self):
        with self.assertRaises(audit.Blocked):
            audit.Fetcher().get("http://127.0.0.1:%d/" % self.server.server_port)


if __name__ == "__main__":
    unittest.main()
