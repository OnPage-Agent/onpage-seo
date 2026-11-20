# SEO audit: https://onpageagent.com

Score **97/100** · 30 pages crawled (30 returned 200) · 2026-11-20

_Stopped at 30 pages (`--max-pages`). Larger sites are sampled._

## 1. Heading levels skipped (low)

Screen readers and summarizers rely on a clean outline. _Best practice, not a search engine requirement._

- **Where:** `/ideas`, `/alternatives/otto-seo`, `/alternatives/surfer-seo`
- **Evidence:** H1 → H3
- **Fix:** Don't jump levels (H2 → H4).
- **Source:** https://developers.google.com/search/docs/fundamentals/seo-starter-guide

## 2. Duplicate meta descriptions (low)

The snippets don't say what makes each page different. 

- **Where:** `/privacy`, `/terms`
- **Evidence:** “Automated SEO for WordPress. An AI SEO agent audits your site every da” on 3 pages
- **Fix:** Write a description per page.
- **Source:** https://developers.google.com/search/docs/appearance/snippet

## 3. Titles over 60 characters (low)

They get cut off in results. _Best practice, not a search engine requirement._

- **Where:** `/insights/best-seo-plugin-for-wordpress`
- **Evidence:** 65 characters: The best SEO plugin for WordPress: Yoast vs Rank Math vs the rest
- **Fix:** Keep the important words in the first 60 characters.
- **Source:** https://developers.google.com/search/docs/appearance/title-link

## 4. No llms.txt (info)

An optional guide for AI tools to your key pages. No search engine requires it. _Best practice, not a search engine requirement._

- **Where:** `/llms.txt`
- **Evidence:** Not found
- **Fix:** Publish /llms.txt listing your most important pages.
- **Source:** https://llmstxt.org/

---

This is a one-off check of the live HTML. To have these fixed on your site automatically, with rollback, and checked every day against your real Google data, try [OnPage Agent](https://onpageagent.com/free-trial).
