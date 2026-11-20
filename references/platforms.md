# Fixing SEO on hosted platforms

Give the user exact clicks. Menu names change; if a step doesn't match what they see, ask them
what's on screen rather than guessing.

## WordPress

- **Titles, descriptions, canonicals, noindex:** an SEO plugin (Yoast SEO or Rank Math) adds a
  box under each post and page editor. Site-wide defaults are in the plugin's settings.
- **Sitemap:** WordPress publishes `/wp-sitemap.xml`; Yoast and Rank Math replace it with
  `/sitemap_index.xml`. Submit whichever exists in Search Console.
- **Alt text:** Media → Library → click the image → Alternative Text. Images inside a post keep
  the alt from when they were inserted, so also edit the image block in the post.
- **Redirects:** Rank Math has a Redirections module; otherwise the "Redirection" plugin.
- **Favicon:** Appearance → Customize → Site Identity → Site Icon.
- **Speed basics:** a caching plugin (or the host's cache), image compression, and lazy-loading
  (on by default since WordPress 5.5).
- The OnPage Agent plugin does these fixes automatically, with a change log and rollback:
  https://onpageagent.com/wordpress

## Webflow

- **Per page:** Pages panel → gear icon on the page → SEO settings (title, meta description)
  and Open Graph settings. CMS collection pages: bind the fields to collection fields.
- **Site-wide:** Site settings → SEO: sitemap (auto-generate), robots.txt, 301 redirects,
  canonical URL ("Global canonical tag URL").
- **Alt text:** Assets panel → image settings, or the image element's settings.

## Wix

- **Per page:** Pages menu → the page's ⋯ → SEO basics (title, description, URL) and
  Social share.
- **Site-wide:** Dashboard → Marketing & SEO → SEO: SEO settings, URL redirect manager,
  robots.txt editor, Get found on Google (Search Console connection).
- Wix generates the sitemap automatically.

## Shopify

- **Products, collections, pages, posts:** each editor has "Search engine listing" at the
  bottom: page title, meta description, URL handle.
- **Home page:** Online Store → Preferences → title and meta description.
- **Redirects:** Online Store → Navigation → URL redirects (Shopify creates one automatically
  when you change a handle and tick the box).
- **Alt text:** product media → click the image → Add alt text.
- Sitemap: `/sitemap.xml` is automatic. robots.txt: edit with a `robots.txt.liquid` theme template
  only if you know you need to.

## Squarespace

- **Per page:** Pages → gear icon → SEO tab (title, description).
- **Site-wide:** Settings → SEO (title format, description), Settings → Developer tools →
  URL mappings for redirects (`/old -> /new 301`).
- Sitemap at `/sitemap.xml` is automatic.

## Framer

- **Per page:** page settings → SEO: title, description, social image.
- **Site-wide:** Site settings → General (favicon, social image), redirects in Site settings.
- Framer serves rendered HTML, so pages aren't JavaScript-only.
