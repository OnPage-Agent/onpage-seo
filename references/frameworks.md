# Where SEO lives in each framework

Check the project's actual versions before editing; APIs below are the current common ones.
Prefer the framework's built-in way over adding a package.

## Next.js (App Router: `app/`) — also v0 projects

- **Title and description:** `export const metadata = { title, description }` in `page.tsx` /
  `layout.tsx`, or `export async function generateMetadata({ params })` for dynamic pages.
  Set a title template in the root layout: `title: { default: "Brand", template: "%s | Brand" }`.
- **Canonical:** set `metadataBase: new URL("https://example.com")` in the root layout, then
  `alternates: { canonical: "/path" }` per page.
- **Open Graph:** `openGraph: { title, description, images: ["/og.png"] }`, or an
  `opengraph-image.png` file next to the page.
- **Viewport and lang:** Next adds the viewport tag by default (customise with
  `export const viewport`). Set `<html lang="en">` in `app/layout.tsx`.
- **Sitemap / robots:** `app/sitemap.ts` returning `MetadataRoute.Sitemap`, and `app/robots.ts`
  returning `MetadataRoute.Robots` with `sitemap: "https://example.com/sitemap.xml"`.
- **JSON-LD:** render `<script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />`
  in the page component. Escape `<` in strings you didn't write.
- **Redirects:** `async redirects() { return [{ source, destination, permanent: true }] }` in
  `next.config.js`.
- **Favicon:** `app/icon.png` (or `favicon.ico` in `app/`).

## Next.js (Pages Router: `pages/`)

- `<Head>` from `next/head` in each page for title, description, canonical, Open Graph.
- Sitemap: generate at build (a script writing `public/sitemap.xml`) or `pages/sitemap.xml.js`
  with `getServerSideProps` writing XML. Robots: `public/robots.txt`.
- Redirects as above in `next.config.js`.

## Astro

- Head tags in the shared layout (`src/layouts/*.astro`), with props for title/description.
- Set `site: "https://example.com"` in `astro.config.mjs`; canonical =
  `new URL(Astro.url.pathname, Astro.site)`.
- Sitemap: `@astrojs/sitemap` integration (official). Robots: `public/robots.txt`.
- Redirects: `redirects: { "/old": "/new" }` in `astro.config.mjs` (status 301 by default).
- Astro outputs HTML by default, so pages aren't JavaScript-only unless a whole page is a
  client-only island.

## React + Vite single-page apps (Lovable, Bolt, many v0 exports, Create React App)

**The main problem is that the HTML has almost no text until JavaScript runs.** Check the page
source (not DevTools): if the body is an empty `<div id="root">`, Google renders it later and many
AI crawlers never see the content. Newer Lovable projects may already render on the server, so
check before changing anything.

Options, smallest first:
1. **Prerender at build time** (best for marketing pages that don't change per visitor): a
   prerender step that writes real HTML for each route, for example `vite-react-ssg` or a
   prerender plugin for your router. Keep the client app as is.
2. **Static site generation / SSR framework**: move marketing pages to Next.js or Astro and keep
   the app separate. Bigger change: ask first.
3. **Prerendering service at the host/CDN** for bots only: works without code changes, but costs
   money and is easy to misconfigure. Mention, don't default to it.

Per-route tags: `react-helmet-async` (wrap the app in `HelmetProvider`, use `<Helmet>` per
page). Without prerendering these tags are also JavaScript-only, so do option 1 too.

Static files go in `public/`: `robots.txt`, `sitemap.xml` (generate it from the router's route
list in a small build script), `favicon.ico`, `llms.txt`.

Redirects depend on the host: Netlify `_redirects` (`/old /new 301`), Vercel `vercel.json`
`"redirects": [{ "source", "destination", "permanent": true }]`, Cloudflare Pages `_redirects`.
SPAs also need real 404s: make sure unknown routes don't all return the app shell with 200
(soft 404). Host settings usually control this.

## Nuxt

- `useSeoMeta({ title, description, ogTitle, ogImage })` and `useHead({ link: [{ rel: "canonical", href }] })`
  in pages; defaults in `nuxt.config.ts` `app.head`.
- Sitemap: the `@nuxtjs/sitemap` module. Robots: `public/robots.txt` or `@nuxtjs/robots`.
- Redirects: `routeRules: { "/old": { redirect: { to: "/new", statusCode: 301 } } }`.
- Nuxt renders on the server by default; check `ssr: false` isn't set for public pages.

## SvelteKit

- `<svelte:head>` in `+page.svelte` (or a shared component) for title, description, canonical.
- `export const prerender = true` for static pages (fixes JavaScript-only content).
- Sitemap: `src/routes/sitemap.xml/+server.ts` returning XML with
  `Content-Type: application/xml`. Robots: `static/robots.txt`.
- Redirects: `throw redirect(301, "/new")` in `+page.server.ts`, or at the host.

## Plain HTML / static site generators (Hugo, Jekyll, Eleventy)

- Edit `<head>` in the base template/layout: `<title>`, `<meta name="description">`,
  `<link rel="canonical">`, `<meta name="viewport" content="width=device-width, initial-scale=1">`,
  `<html lang>`, Open Graph tags, favicon link.
- Hugo, Jekyll (`jekyll-sitemap`) and Eleventy all have standard sitemap support; use it.

## JSON-LD to start with (any framework)

Home page: `Organization` (name, url, logo, sameAs social profiles) and `WebSite` (name, url).
Articles: `Article` or `BlogPosting` (headline, datePublished, dateModified, author, image).
Products: `Product` with `offers` (price, priceCurrency, availability). Local businesses:
`LocalBusiness` with address and opening hours. Only mark up what's visible on the page.
FAQ rich results only show for government and health sites now, so don't add `FAQPage` just
for rich results.
