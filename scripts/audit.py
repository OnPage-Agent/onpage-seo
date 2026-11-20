#!/usr/bin/env python3
"""On-page SEO audit of a live website. Standard library only (Python 3.9+).

    python3 audit.py https://example.com                 # Markdown report on stdout
    python3 audit.py https://example.com --json out.json # also write every finding as JSON
    python3 audit.py https://example.com --max-pages 100

It crawls up to --max-pages HTML pages on the same host (homepage, sitemap, then links),
politely (4 at a time, robots.txt Disallow rules for * honoured), and checks each page and
the site as a whole against rules tied to Google Search Central. Nothing is sent anywhere
except requests to the site itself.

Part of the free OnPage Agent skill: https://onpageagent.com
"""
import argparse
import concurrent.futures
import hashlib
import ipaddress
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

UA = "OnPageSEO-Skill/1.0 (+https://onpageagent.com)"
TIMEOUT = 15
SKIP_EXT = re.compile(r"\.(pdf|jpe?g|png|gif|webp|avif|svg|ico|zip|mp4|mp3|webm|xml|css|js|json|txt|woff2?|ttf|eot)(\?|$)", re.I)
GENERIC_ANCHORS = re.compile(r"^(click here|here|read more|more|learn more|this|link|this page|see more|continue reading|details|go)$", re.I)
AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "anthropic-ai", "PerplexityBot",
           "Google-Extended", "CCBot", "Applebot-Extended", "Bytespider"]
SEARCH_BOTS = ["*", "Googlebot", "Bingbot"]
G = "https://developers.google.com/search/docs/"

# id: (severity, title, why it matters, how to fix, source, best practice rather than a search engine rule)
RULES = {
    "robots_blocks_search": ("critical", "robots.txt blocks search engines from the whole site", "Nothing new gets crawled or indexed.", "Remove the site-wide `Disallow: /` for Googlebot, Bingbot and `*`.", G + "crawling-indexing/robots/intro", False),
    "noindex": ("high", "Pages set to noindex", "These pages are kept out of search results.", "Remove `noindex` from pages that should rank.", G + "crawling-indexing/block-indexing", False),
    "http_errors": ("high", "Pages returning errors", "Linked pages that fail lose visitors and crawl budget.", "Restore them or 301 them to the closest live page, and update links.", "https://developers.google.com/crawling/docs/troubleshooting/http-status-codes", False),
    "no_https_redirect": ("high", "http:// doesn't redirect to https://", "An insecure copy of the site is reachable.", "Permanently (301) redirect every http:// address to https://.", G + "appearance/page-experience", False),
    "js_only": ("high", "Content only appears after JavaScript runs", "Google renders it late and AI crawlers often not at all. Common on Lovable, Bolt and React SPA sites.", "Render on the server (SSR, static generation or prerendering) so the text is in the HTML.", G + "crawling-indexing/javascript/javascript-seo-basics", False),
    "title_missing": ("high", "Pages without a title", "Pages without a title rarely rank and show a generic label.", "Add a unique, descriptive `<title>` (about 50–60 characters).", G + "appearance/title-link", False),
    "viewport_missing": ("high", "No mobile viewport tag", "Google indexes the mobile version; without it pages render as shrunken desktop pages.", 'Add `<meta name="viewport" content="width=device-width, initial-scale=1">`.', G + "crawling-indexing/mobile/mobile-sites-mobile-first-indexing", False),
    "jsonld_invalid": ("high", "Structured data that doesn't parse", "Google ignores the whole JSON-LD block.", "Fix the JSON syntax and test it in Google's Rich Results Test.", G + "appearance/structured-data/intro-structured-data", False),
    "canonical_broken": ("high", "Canonical points to a broken or redirecting URL", "The page may drop out of the index.", "Point the canonical at the page itself (or a live 200 duplicate).", G + "crawling-indexing/consolidate-duplicate-urls", False),
    "meta_missing": ("medium", "Pages without a meta description", "Google writes its own snippet, which usually lowers clicks.", "Write a 120–155 character description of what the page offers.", G + "appearance/snippet", False),
    "title_duplicate": ("medium", "Duplicate titles", "Google can't tell the pages apart.", "Make each title unique to its page.", G + "appearance/title-link", False),
    "h1_missing": ("medium", "Pages without an H1", "The main heading tells readers and Google what the page is.", "Add one H1 that names the page's topic.", G + "fundamentals/seo-starter-guide", True),
    "canonical_missing": ("medium", "Pages without a canonical tag", "URL variants with parameters can compete with each other.", "Add a self-referencing `<link rel=\"canonical\">`.", G + "crawling-indexing/consolidate-duplicate-urls", False),
    "sitemap_missing": ("medium", "No XML sitemap found", "A sitemap helps Google find new and deep pages.", "Publish /sitemap.xml and add a `Sitemap:` line to robots.txt.", G + "crawling-indexing/sitemaps/overview", False),
    "soft_404": ("medium", "Missing pages return 200 (soft 404)", "Error pages can get indexed and waste crawls.", "Return 404 or 410 for addresses that don't exist.", "https://developers.google.com/crawling/docs/troubleshooting/http-status-codes", False),
    "host_variant": ("medium", "www and non-www both serve the site", "Two copies of every page compete.", "301 one host to the other.", G + "crawling-indexing/consolidate-duplicate-urls", False),
    "redirect_chains": ("medium", "Internal links through redirects", "Each hop slows the page and loses a little link value.", "Link straight to the final URL.", G + "crawling-indexing/301-redirects", False),
    "duplicate_content": ("medium", "Pages with identical text", "Google picks one to show, maybe the wrong one.", "Merge them, or point a canonical at the main one.", G + "crawling-indexing/consolidate-duplicate-urls", False),
    "images_alt": ("medium", "Images without alt text", "Screen readers and image search rely on alt text.", "Describe each meaningful image in its `alt` attribute.", G + "appearance/google-images", False),
    "title_length": ("low", "Titles over 60 characters", "They get cut off in results.", "Keep the important words in the first 60 characters.", G + "appearance/title-link", True),
    "meta_duplicate": ("low", "Duplicate meta descriptions", "The snippets don't say what makes each page different.", "Write a description per page.", G + "appearance/snippet", False),
    "h1_multiple": ("low", "Pages with several H1s", "One H1 per page keeps the outline clear.", "Keep one H1; make the others H2.", G + "fundamentals/seo-starter-guide", True),
    "heading_skip": ("low", "Heading levels skipped", "Screen readers and summarizers rely on a clean outline.", "Don't jump levels (H2 → H4).", G + "fundamentals/seo-starter-guide", True),
    "thin": ("low", "Thin pages (under 300 words)", "They rarely rank on their own.", "Expand them with what searchers ask, or merge them.", G + "fundamentals/creating-helpful-content", True),
    "lang_missing": ("low", "No lang attribute on <html>", "Helps browsers, screen readers and translation.", 'Add `<html lang="en">` (or your language).', "https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/lang", True),
    "og_missing": ("low", "Homepage has no Open Graph title or image", "Shared links show without a proper title or picture.", "Add `og:title`, `og:description` and `og:image`.", "https://ogp.me/", True),
    "favicon_missing": ("low", "No favicon", "Google shows a site icon next to results.", 'Add `<link rel="icon" href="/favicon.ico">`.', G + "appearance/favicon-in-search", False),
    "generic_anchors": ("low", "Links with generic text", "“Click here” tells Google nothing about the target.", "Use words that describe the page you link to.", G + "crawling-indexing/links-crawlable", False),
    "security_headers": ("low", "Security headers missing", "HSTS and similar headers protect visitors.", "Add them at your host or CDN.", "https://owasp.org/www-project-secure-headers/", True),
    "ai_bots_blocked": ("info", "AI crawlers blocked in robots.txt", "Keeps you out of those assistants' answers. Fine if deliberate.", "Allow the AI search crawlers you want to be cited by (OAI-SearchBot, Claude-SearchBot, PerplexityBot).", G + "appearance/ai-features", True),
    "llms_missing": ("info", "No llms.txt", "An optional guide for AI tools to your key pages. No search engine requires it.", "Publish /llms.txt listing your most important pages.", "https://llmstxt.org/", True),
}
WEIGHT = {"critical": 6, "high": 4, "medium": 2, "low": 1, "info": 0}


class Blocked(Exception):
    pass


def public_host(host, allow_local):
    if allow_local:
        return True
    try:
        for info in socket.getaddrinfo(host, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
    except (socket.gaierror, ValueError):
        return False
    return True


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Fetcher:
    def __init__(self, allow_local=False):
        self.allow_local = allow_local
        ctx = ssl.create_default_context()
        self.opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ctx))

    def get(self, url, max_hops=5):
        """Returns dict(status, headers, body, final_url, chain, ms). Follows redirects itself to record them."""
        chain, started = [], time.time()
        current = url
        for _ in range(max_hops + 1):
            host = urllib.parse.urlparse(current).hostname or ""
            if not public_host(host, self.allow_local):
                raise Blocked("refusing private or local address " + host)
            req = urllib.request.Request(current, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8"})
            try:
                with self.opener.open(req, timeout=TIMEOUT) as res:
                    status, headers, body = res.status, res.headers, res.read(3_000_000)
            except urllib.error.HTTPError as e:
                status, headers = e.code, e.headers
                body = e.read(500_000) if e.fp else b""
                e.close()
            if status in (301, 302, 303, 307, 308) and headers.get("Location") and len(chain) < max_hops:
                chain.append({"url": current, "status": status})
                current = urllib.parse.urljoin(current, headers.get("Location"))
                continue
            return {"status": status, "headers": {k.lower(): v for k, v in headers.items()}, "body": body,
                    "final_url": current, "chain": chain, "ms": int((time.time() - started) * 1000)}
        return {"status": 0, "headers": {}, "body": b"", "final_url": current, "chain": chain, "ms": 0}


class PageParser(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "header", "noscript", "svg", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.titles, self.meta, self.links, self.imgs = "", 0, {}, [], []
        self.lang, self.canonical, self.icon, self.app_shell = None, None, False, False
        self.headings, self.jsonld, self.text = [], [], []
        self._in, self._skip, self._a, self._h, self._json = None, 0, None, None, None

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang", "").strip()
        elif tag == "title":
            self._in, self.titles = "title", self.titles + 1
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key:
                self.meta[key] = a.get("content", "")
        elif tag == "link":
            rel = a.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonical = a.get("href")
            if "icon" in rel or "apple-touch-icon" in rel:
                self.icon = True
        elif tag == "a" and a.get("href"):
            self._a = {"href": a["href"], "text": "", "nofollow": "nofollow" in a.get("rel", "")}
        elif tag == "img":
            self.imgs.append({"src": a.get("src") or a.get("data-src", ""), "alt": a.get("alt"),
                              "decorative": a.get("role") in ("presentation", "none") or a.get("aria-hidden") == "true"})
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._h = [int(tag[1]), ""]
        elif tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self._json = []
        if a.get("id") in ("root", "app", "__next", "__nuxt") or "data-reactroot" in a or "ng-version" in a:
            self.app_shell = True
        if tag in self.SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in = None
        elif tag == "a" and self._a:
            self.links.append(self._a)
            self._a = None
        elif self._h and tag == "h%d" % self._h[0]:
            self.headings.append((self._h[0], self._h[1].strip()))
            self._h = None
        elif tag == "script" and self._json is not None:
            self.jsonld.append("".join(self._json))
            self._json = None
        if tag in self.SKIP and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._in == "title":
            self.title += data
        if self._json is not None:
            self._json.append(data)
        if self._a is not None:
            self._a["text"] += data
        if self._h is not None:
            self._h[1] += data
        if not self._skip:
            self.text.append(data)


class Audit:
    def __init__(self, start, max_pages=50, allow_local=False, log=sys.stderr):
        if "://" not in start:
            start = "https://" + start
        u = urllib.parse.urlparse(start)
        self.base = "%s://%s" % (u.scheme, u.netloc)
        self.host = u.hostname or ""
        self.max_pages = max_pages
        self.fetch = Fetcher(allow_local)
        self.log = log
        self.pages, self.facts, self.findings = {}, {}, []

    def say(self, msg):
        print(msg, file=self.log, flush=True)

    def url(self, path):
        return self.base + path

    def norm(self, href, page_url):
        """Same-host path for a link, or None."""
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            return None
        u = urllib.parse.urlparse(urllib.parse.urljoin(page_url, href))
        if u.scheme not in ("http", "https") or (u.hostname or "").lower().removeprefix("www.") != self.host.lower().removeprefix("www."):
            return None
        path = u.path or "/"
        return path + ("?" + u.query if u.query else "")

    # ---- crawl -------------------------------------------------------------------

    def run(self):
        self.say("Auditing %s (up to %d pages)…" % (self.base, self.max_pages))
        self.read_robots()
        sitemap = self.read_sitemaps()
        self.facts["sitemap"] = {"found": bool(sitemap), "urls": len(sitemap)}
        queue, seen = ["/"] + [p for p in sitemap if p != "/"], set()
        depth = {"/": 0}
        for p in sitemap:
            depth.setdefault(p, 1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            while queue and len(self.pages) < self.max_pages:
                batch = []
                while queue and len(batch) < 8 and len(self.pages) + len(batch) < self.max_pages:
                    p = queue.pop(0)
                    if p in seen or SKIP_EXT.search(p) or self.disallowed(p):
                        continue
                    seen.add(p)
                    batch.append(p)
                for path, page in zip(batch, pool.map(self.crawl_one, batch)):
                    page["depth"] = depth.get(path, 1)
                    page["in_sitemap"] = path in sitemap
                    self.pages[path] = page
                    for link in page.get("links", []):
                        if link["path"] not in seen and link["path"] not in depth:
                            depth[link["path"]] = page["depth"] + 1
                            queue.append(link["path"])
                self.say("  crawled %d pages" % len(self.pages))
        self.probe_site()
        self.check()
        return self

    def crawl_one(self, path):
        try:
            r = self.fetch.get(self.url(path))
        except Blocked as e:
            return {"path": path, "status": 0, "error": str(e)}
        except Exception as e:  # network errors are findings, not crashes
            return {"path": path, "status": 0, "error": type(e).__name__}
        page = {"path": path, "status": r["status"], "chain": r["chain"], "ms": r["ms"], "bytes": len(r["body"]),
                "final": self.norm(r["final_url"], r["final_url"])}
        if r["chain"] and page["final"] != path:
            page["status"] = r["chain"][0]["status"]
            return page
        ctype = r["headers"].get("content-type", "")
        if r["status"] != 200 or "html" not in ctype:
            return page
        if path == "/":
            self.facts["headers"] = {k: v for k, v in r["headers"].items() if k in (
                "strict-transport-security", "x-content-type-options", "x-frame-options", "content-security-policy", "referrer-policy")}
        parser = PageParser()
        try:
            parser.feed(r["body"].decode("utf-8", "replace"))
        except Exception:
            pass
        text = re.sub(r"\s+", " ", " ".join(parser.text)).strip()
        links = []
        for a in parser.links:
            p = self.norm(a["href"], r["final_url"])
            if p:
                links.append({"path": p.split("#")[0], "text": re.sub(r"\s+", " ", a["text"]).strip()})
        robots_meta = parser.meta.get("robots", "").lower()
        page.update({
            "title": re.sub(r"\s+", " ", parser.title).strip(), "titles": parser.titles,
            "meta": parser.meta.get("description", "").strip(), "noindex": "noindex" in robots_meta,
            "canonical": parser.canonical, "lang": parser.lang, "viewport": "viewport" in parser.meta,
            "og": bool(parser.meta.get("og:title")) and bool(parser.meta.get("og:image")), "icon": parser.icon,
            "h1": [t for lvl, t in parser.headings if lvl == 1], "headings": [lvl for lvl, _ in parser.headings],
            "words": len([w for w in text.split() if re.search(r"\w", w)]), "text_hash": hashlib.sha1(text.lower().encode()).hexdigest(),
            "links": links, "imgs": parser.imgs, "jsonld": parser.jsonld, "app_shell": parser.app_shell,
        })
        return page

    def read_robots(self):
        self.groups, self.sitemaps_in_robots = [], []
        try:
            r = self.fetch.get(self.url("/robots.txt"))
        except Exception:
            r = {"status": 0, "body": b""}
        self.facts["robots_status"] = r["status"]
        if r["status"] != 200:
            return
        current = None
        for line in r["body"].decode("utf-8", "replace").splitlines():
            key, _, val = line.split("#")[0].partition(":")
            key, val = key.strip().lower(), val.strip()
            if key == "user-agent":
                if current is None or current["rules"]:
                    current = {"agents": [], "rules": []}
                    self.groups.append(current)
                current["agents"].append(val)
            elif key in ("allow", "disallow"):
                if current is None:
                    current = {"agents": ["*"], "rules": []}
                    self.groups.append(current)
                current["rules"].append((key, val))
            elif key == "sitemap" and val:
                self.sitemaps_in_robots.append(val)

    def group_for(self, agent):
        for g in self.groups:
            if any(a.lower() == agent.lower() for a in g["agents"]):
                return g
        return next((g for g in self.groups if "*" in g["agents"]), None)

    def blocks_all(self, agent):
        g = self.group_for(agent)
        return bool(g) and ("disallow", "/") in g["rules"] and ("allow", "/") not in g["rules"]

    def disallowed(self, path):
        g = self.group_for("*")
        return bool(g) and any(k == "disallow" and v and path.startswith(v) for k, v in g["rules"])

    def read_sitemaps(self):
        candidates = self.sitemaps_in_robots + [self.url(p) for p in ("/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml")]
        for url in candidates:
            paths = self.sitemap_paths(url)
            if paths:
                return paths
        return []

    def sitemap_paths(self, url, depth=0):
        try:
            r = self.fetch.get(url)
            if r["status"] != 200:
                return []
            root = ET.fromstring(r["body"])
        except Exception:
            return []
        locs = [e.text.strip() for e in root.iter() if e.tag.endswith("loc") and e.text]
        if root.tag.endswith("sitemapindex") and depth == 0:
            out = []
            for child in locs[:10]:
                out += self.sitemap_paths(child, 1)
            return out
        return [p for p in (self.norm(u, u) for u in locs) if p][:2000]

    def probe_site(self):
        self.say("Checking robots.txt, llms.txt, HTTPS and host redirects…")
        try:
            r = self.fetch.get(self.url("/llms.txt"))
            self.facts["llms_txt"] = r["status"] == 200 and "html" not in r["headers"].get("content-type", "")
        except Exception:
            self.facts["llms_txt"] = None
        try:
            r = self.fetch.get(self.url("/onpage-check-%s-not-a-page" % uuid.uuid4().hex[:8]))
            self.facts["soft_404"] = r["status"] == 200
        except Exception:
            self.facts["soft_404"] = None
        if self.base.startswith("https://"):
            for key, url in (("http", "http://%s/" % self.host),
                             ("alt_host", "https://%s/" % (self.host[4:] if self.host.startswith("www.") else "www." + self.host))):
                try:
                    r = self.fetch.get(url)
                    self.facts[key] = {"status": r["status"], "final": r["final_url"], "temporary": any(c["status"] in (302, 303, 307) for c in r["chain"])}
                except Exception as e:
                    self.facts[key] = {"error": type(e).__name__}

    # ---- checks ------------------------------------------------------------------

    def add(self, rule, urls, evidence):
        if urls:
            self.findings.append({"rule": rule, "urls": list(urls)[:50], "count": len(urls), "evidence": evidence})

    def check(self):
        pages = self.pages
        html = {p: d for p, d in pages.items() if d.get("status") == 200 and "title" in d}
        live = {p: d for p, d in html.items() if not d["noindex"] and (not d["canonical"] or self.norm(d["canonical"], self.url(p)) in (p, None))}
        n = max(len(live), 1)

        if any(self.blocks_all(a) for a in SEARCH_BOTS) and self.facts.get("robots_status") == 200:
            self.add("robots_blocks_search", ["/robots.txt"], "Disallow: / applies to search engines")
        blocked_ai = [b for b in AI_BOTS if self.blocks_all(b)] if self.facts.get("robots_status") == 200 else []
        self.add("ai_bots_blocked", ["/robots.txt"] if blocked_ai else [], "Blocked: " + ", ".join(blocked_ai))
        if not self.facts["sitemap"]["found"]:
            self.add("sitemap_missing", ["/sitemap.xml"], "No sitemap in robots.txt or the usual locations")
        if self.facts.get("soft_404"):
            self.add("soft_404", ["/a-page-that-does-not-exist"], "A made-up address answered 200 OK")
        if self.facts.get("llms_txt") is False:
            self.add("llms_missing", ["/llms.txt"], "Not found")
        http = self.facts.get("http") or {}
        if http.get("final", "").startswith("http://") and http.get("status") == 200:
            self.add("no_https_redirect", ["http://" + self.host + "/"], "http:// serves the site")
        elif http.get("temporary"):
            self.add("no_https_redirect", ["http://" + self.host + "/"], "Redirects with a temporary (302/307) redirect; make it 301")
        alt = self.facts.get("alt_host") or {}
        alt_host = urllib.parse.urlparse(alt.get("final", "")).hostname or ""
        if alt.get("status") == 200 and alt_host and alt_host != self.host:
            self.add("host_variant", [alt.get("final")], alt_host + " serves the site too")
        headers = self.facts.get("headers")
        if headers is not None and self.base.startswith("https://"):
            missing = [h for h, k in (("HSTS", "strict-transport-security"), ("X-Content-Type-Options", "x-content-type-options"), ("Referrer-Policy", "referrer-policy")) if k not in headers]
            if len(missing) >= 2:
                self.add("security_headers", ["/"], "Missing: " + ", ".join(missing))

        errors = [p for p, d in pages.items() if d.get("status", 0) >= 400 or d.get("status") == 0]
        self.add("http_errors", errors, "; ".join("%s (%s)" % (p, pages[p].get("status") or pages[p].get("error", "unreachable")) for p in errors[:5]))
        self.add("noindex", [p for p, d in html.items() if d["noindex"]], "meta robots noindex")

        home = html.get("/")
        if home:
            if not home["lang"]:
                self.add("lang_missing", ["/"], "<html> has no lang")
            if not home["icon"]:
                self.add("favicon_missing", ["/"], "No <link rel=\"icon\">")
            if not home["og"]:
                self.add("og_missing", ["/"], "og:title or og:image missing")

        def per_page(rule, test, ev):
            hits = [p for p, d in live.items() if test(d)]
            self.add(rule, hits, ev(live[hits[0]]) if hits else "")

        per_page("title_missing", lambda d: not d["title"], lambda d: "Empty or missing <title>")
        per_page("title_length", lambda d: len(d["title"]) > 60, lambda d: "%d characters: %s" % (len(d["title"]), d["title"][:80]))
        per_page("meta_missing", lambda d: not d["meta"], lambda d: "No meta description")
        per_page("h1_missing", lambda d: not d["h1"], lambda d: "No <h1>")
        per_page("h1_multiple", lambda d: len(d["h1"]) > 1, lambda d: "%d H1s" % len(d["h1"]))
        per_page("viewport_missing", lambda d: not d["viewport"], lambda d: "No <meta name=\"viewport\">")
        per_page("canonical_missing", lambda d: not d["canonical"], lambda d: "No rel=canonical")
        per_page("js_only", lambda d: d["app_shell"] and d["words"] < 80, lambda d: "%d words in the HTML, JavaScript app root present" % d["words"])
        per_page("thin", lambda d: d["path"] != "/" and 0 < d["words"] < 300 and not d["app_shell"], lambda d: "%d words" % d["words"])

        def skip(levels):
            return next(("H%d → H%d" % (a, b) for a, b in zip(levels, levels[1:]) if b > a + 1), None)
        per_page("heading_skip", lambda d: skip(d["headings"]), lambda d: skip(d["headings"]))

        bad_json = []
        for p, d in live.items():
            for block in d["jsonld"]:
                try:
                    json.loads(block)
                except ValueError:
                    bad_json.append(p)
                    break
        self.add("jsonld_invalid", bad_json, "A JSON-LD block fails to parse")

        for field, rule in (("title", "title_duplicate"), ("meta", "meta_duplicate")):
            groups = {}
            for p, d in live.items():
                if d[field]:
                    groups.setdefault(d[field].strip().lower(), []).append(p)
            dups = [ps for ps in groups.values() if len(ps) > 1]
            self.add(rule, [p for ps in dups for p in ps[1:]], "; ".join("“%s” on %d pages" % (live[ps[0]][field][:70], len(ps)) for ps in dups[:3]))
        texts = {}
        for p, d in live.items():
            if d["words"] >= 50:
                texts.setdefault(d["text_hash"], []).append(p)
        dup = [ps for ps in texts.values() if len(ps) > 1]
        self.add("duplicate_content", [p for ps in dup for p in ps[1:]], "; ".join("same text as %s" % ps[0] for ps in dup[:3]))

        no_alt, chains, generic, bad_canon = set(), set(), set(), []
        for p, d in html.items():
            for img in d["imgs"]:
                if (img["alt"] is None or not img["alt"].strip()) and not img["decorative"] and img["src"] and not re.search(r"facebook\.com/tr|pixel|analytics", img["src"]):
                    no_alt.add(p)
            for link in d["links"]:
                target = pages.get(link["path"])
                if target and target.get("chain"):
                    chains.add(p)
                if GENERIC_ANCHORS.match(link["text"]):
                    generic.add(p)
            if d["canonical"]:
                c = self.norm(d["canonical"], self.url(p))
                t = pages.get(c) if c and c != p else None
                if t and (t.get("status", 0) >= 300 or t.get("status") == 0):
                    bad_canon.append(p)
        self.add("images_alt", sorted(no_alt), "%d pages have images without alt text" % len(no_alt))
        self.add("redirect_chains", sorted(chains), "Links point at URLs that redirect")
        self.add("generic_anchors", sorted(generic), "Links like “click here” or “read more”")
        self.add("canonical_broken", bad_canon, "Canonical target redirects or fails")

        # Impact ranks the work; it doesn't predict traffic.
        for f in self.findings:
            sev = RULES[f["rule"]][0]
            site_wide = f["urls"] and not f["urls"][0] in pages
            share = 1.0 if site_wide else min(f["count"] / n, 1.0)
            f["severity"] = sev
            f["impact"] = round(WEIGHT[sev] * (0.6 + 0.4 * share), 2)
        self.findings.sort(key=lambda f: -f["impact"])

    def score(self):
        n = max(len([d for d in self.pages.values() if d.get("status") == 200]), 1)
        penalty = 0
        for f in self.findings:
            cap = {"critical": 40, "high": 20, "medium": 10, "low": 4, "info": 0}[f["severity"]]
            share = 1.0 if f["urls"] and f["urls"][0] not in self.pages else min(f["count"] / n, 1.0)
            penalty += cap * max(share, 0.25)
        return max(0, min(100, round(100 - penalty)))

    # ---- output ------------------------------------------------------------------

    def markdown(self):
        crawled = len(self.pages)
        ok = len([d for d in self.pages.values() if d.get("status") == 200])
        out = ["# SEO audit: %s" % self.base, "",
               "Score **%d/100** · %d pages crawled (%d returned 200) · %s" % (self.score(), crawled, ok, time.strftime("%Y-%m-%d")), ""]
        if crawled >= self.max_pages:
            out += ["_Stopped at %d pages (`--max-pages`). Larger sites are sampled._" % self.max_pages, ""]
        if not self.findings:
            out += ["No issues found by these checks."]
        for i, f in enumerate(self.findings, 1):
            sev, title, why, fix, src, heuristic = RULES[f["rule"]]
            out += ["## %d. %s (%s)" % (i, title, sev), "",
                    "%s %s" % (why, "_Best practice, not a search engine requirement._" if heuristic else ""), "",
                    "- **Where:** %s%s" % (", ".join("`%s`" % u for u in f["urls"][:8]), " and %d more" % (f["count"] - 8) if f["count"] > 8 else ""),
                    "- **Evidence:** %s" % f["evidence"], "- **Fix:** %s" % fix, "- **Source:** %s" % src, ""]
        out += ["---", "",
                "This is a one-off check of the live HTML. To have these fixed on your site automatically, with rollback, "
                "and checked every day against your real Google data, try [OnPage Agent](https://onpageagent.com/free-trial)."]
        return "\n".join(out)

    def as_json(self):
        return {"site": self.base, "score": self.score(), "facts": self.facts, "findings": self.findings,
                "rules": {k: {"severity": v[0], "title": v[1], "fix": v[3], "source": v[4], "best_practice": v[5]} for k, v in RULES.items()},
                "pages": [{k: v for k, v in d.items() if k not in ("links", "imgs", "jsonld", "text_hash")} for d in self.pages.values()]}


def main():
    ap = argparse.ArgumentParser(description="On-page SEO audit of a live website.")
    ap.add_argument("url")
    ap.add_argument("--max-pages", type=int, default=50)
    ap.add_argument("--json", help="also write the full results to this file")
    ap.add_argument("--allow-local", action="store_true", help="allow localhost and private addresses (for testing your own dev server)")
    args = ap.parse_args()
    audit = Audit(args.url, max_pages=args.max_pages, allow_local=args.allow_local).run()
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(audit.as_json(), fh, indent=2, default=str)
    print(audit.markdown())


if __name__ == "__main__":
    main()
