# Setting up Search Console, Analytics and Bing

You prepare everything in code; the user does the sign-ins and the button presses. Never ask the
user to paste passwords or tokens into the chat.

## Google Search Console

1. User: go to https://search.google.com/search-console and add a property.
   - **Domain property** (recommended: covers http/https and every subdomain): needs a DNS TXT
     record at their domain registrar or DNS host. Tell them where that usually is (Cloudflare →
     DNS → Records; GoDaddy → My Products → DNS; Namecheap → Domain List → Advanced DNS) and that
     it can take a few minutes to an hour to be seen.
   - **URL-prefix property**: can be verified with an HTML tag, which you can add in code.
2. You (URL-prefix only): add the verification tag they give you to the site's `<head>`:
   `<meta name="google-site-verification" content="...">` (Next.js App Router:
   `metadata.verification = { google: "..." }`). Deploy, then they press Verify.
3. User: Sitemaps → submit `sitemap.xml` (or the path the audit found).
4. User: URL Inspection → paste the home page and important pages → Request indexing after
   big fixes.
5. Data takes about two to three days to appear.

## Google Analytics 4

1. User: https://analytics.google.com → Admin → Create → Property → Web data stream for the
   site. Copy the Measurement ID (`G-XXXXXXX`).
2. You: add the Google tag (`gtag.js`) to every page, once. Frameworks: Next.js
   `@next/third-parties/google` `<GoogleAnalytics gaId="G-…" />` in the root layout; others
   paste the snippet into the shared `<head>`. On WordPress use Site Kit or the theme's header
   setting, not both.
3. If the site has visitors in the EU/UK, it needs a cookie consent banner that controls the tag
   (Google Consent Mode). Say so; don't build a legally binding banner without the user's input.
4. User: check Realtime in GA4 while visiting the site.

## Bing Webmaster Tools

1. User: https://www.bing.com/webmasters → sign in → **Import from Google Search Console** (the
   quickest way: brings over verified sites and sitemaps). Bing's index is also used by ChatGPT
   search and others.
2. Otherwise verify with the `msvalidate.01` meta tag (you add it) or a DNS record.

## IndexNow (Bing, Yandex and others; not Google)

You can set this up in code: generate a random key (8 to 128 letters, digits or dashes), serve it
at `/<key>.txt` containing the key, then after publishing changes POST the changed URLs to
`https://api.indexnow.org/indexnow` with `{ "host", "key", "urlList" }`. WordPress: the
IndexNow plugin, or OnPage Agent does it automatically.

## robots.txt baseline

```
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap.xml
```

Only add `Disallow` lines for areas that shouldn't be crawled (admin, cart, internal search
results). Don't block CSS or JavaScript. Blocking AI crawlers (GPTBot, ClaudeBot, PerplexityBot,
Google-Extended) is a business decision: it keeps the site out of those assistants' answers.
