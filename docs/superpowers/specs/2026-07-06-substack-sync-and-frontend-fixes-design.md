# Substack Sync Pipeline + Frontend Fixes — Design

Date: 2026-07-06
Status: Approved pending user review

## Context

divij-sinha.github.io is a single hand-written `index.html` on GitHub Pages. No SSG, no build step, no JS. Hard budgets: **index.html ≤ 6kb gzipped** (currently 5,618 bytes), **whole site ≤ 300kb including images**. The owner has a Substack (overlookedpod.substack.com, 5 public posts) and wants the site to act as a mirror blog: an auto-updated post list on the home page, with full post text on separate local pages.

External advice suggested a Node pipeline (turndown + sharp + markdown + SSG). Evaluated and rejected: there is no SSG here, HTML→Markdown→HTML is a wasteful round trip when the API provides `body_html`, and locally mirroring images (the IPL post alone has 9) would break the 300kb budget. The advice's *architecture* — scheduled GitHub Action polling the JSON API and committing results — is correct and retained.

## Part A: Substack sync

### Components

**1. `scripts/sync_substack.py`** — Python 3, stdlib only (urllib, json, html.parser, pathlib). No dependencies, no package manager step in CI.

Guiding principle throughout: minimalism in code — as few moving parts as possible, nothing speculative. No enforcement machinery for the size budgets; small pages are an outcome of generating only what's necessary, checked by eye.

Behavior:
- Fetch `https://overlookedpod.substack.com/api/v1/posts?limit=50` (paginate with `offset` if 50 returned). Keep posts where `is_published` is true and `audience == "everyone"`.
- **Sanitize** each post's `body_html` via a `html.parser.HTMLParser` subclass:
  - Allowlist tags: `p, h1–h6, ul, ol, li, blockquote, a, img, em, strong, b, i, code, pre, figure, figcaption, table, thead, tbody, tr, th, td, br, hr, sub, sup`.
  - Allowlist attributes: `a[href]`, `img[src, alt, width, height]`. Everything else (classes, styles, data-*) is dropped.
  - Non-allowlisted tags are handled two ways: structural wrappers (`div, span, section, article`) are unwrapped (tag dropped, children kept); interactive/cruft subtrees (`script, style, form, button, iframe, svg`, and any element whose class contains `subscribe`, `share`, `button`, or `tweet`) are dropped entirely, children included.
  - `img src` left pointing at Substack's CDN (decision: hotlink, zero local bytes; add `loading="lazy"`).
  - Substack heading anchors and internal `substack.com/p/...` links to the owner's own posts are rewritten to local `/posts/<slug>` where the slug is in the synced set; other links untouched.
- **Write `posts/<slug>.html`** from a template embedded in the script: same fonts (`../Figtree...`, `../Boldonse...` relative paths), same color scheme and minimal CSS as index, minimal nav (site name → home), title, date, sanitized body, and a footer link "Read on Substack →" to `canonical_url`. Target ~2–4kb gzipped for text posts.
- **Update `index.html`**: replace content between `<!-- substack:start -->` and `<!-- substack:end -->` markers (added once by hand inside the Personal section's grid) with one `grid-item` per post: title linking to `posts/<slug>`, date, one-line `description` from the API. Newest first.
- **Idempotent**: regeneration from unchanged API data produces byte-identical files; the Action then has nothing to commit.

**2. `.github/workflows/substack-sync.yml`**
- Triggers: `schedule: cron '0 6 * * *'` (daily), `workflow_dispatch`.
- `permissions: contents: write`.
- Steps: checkout → `python3 scripts/sync_substack.py` → commit & push iff changes (`git diff --quiet || (git commit && git push)`), bot identity.
- No setup-node, no npm, no setup-python (runner's system python3 suffices).

### index.html changes for the sync
- The two hand-written Substack entries in Personal ("A series exploring IPL through data", "Whose value is it anyways?") are removed; the generated list replaces them between the markers.
- Estimated net index growth: ≈ +350 gzipped bytes (5 entries added, 2 removed).

### Error handling
- API unreachable / non-200 / malformed JSON: script exits non-zero without touching files; CI shows red run, site unaffected.
- Unknown/new tags in body_html: dropped by allowlist (fail-closed on markup, never on the run).
- Posts removed or retitled on Substack: local `posts/*.html` are regenerated from the full API response each run; a post no longer in the API keeps its last generated file (no deletion logic — YAGNI at 5 posts).

### Testing
- Run script locally against the live API; inspect generated `posts/*.html` in a browser and diff `index.html`.
- Re-run immediately; assert zero diff (idempotence).
- Check gzipped sizes of index and each post page.
- Trigger `workflow_dispatch` once after merge to verify CI path end-to-end.

## Part B: Frontend fixes (all in `index.html` unless noted)

1. ARPA Audit and Property Tax Explainer cards: replace literal "TODO" with one-line descriptions drafted from their linked sites, same style as sibling cards (shown in diff for approval).
2. Hospital Price Transparency `[site]` → `https://healthcare.miurban-dashboards.org/`; Who Owns Chicago `[site]` → `https://whoownschi.miurban-dashboards.org/`.
3. Mail link: `href="#"` → `href="mailto:divijs@uchicago.edu"` (display text unchanged).
4. Charizard sprite: download to local file (e.g. `charizard.png`, ~1kb), reference locally; drop the pokemondb.net hotlink (site's only third-party request).
5. Typo: "help out in way I can" → "help out in any way I can".
6. Remove dead `h4 { font-family: "Gill Sans", ... }` rule (no h4 in document).
7. Add `<link rel="preload" as="font" type="font/woff2" crossorigin>` for both woff2 fonts.
8. Re-encode `col.webp` from `static/col_original.jpg` at 640px wide (2× the 320px display size), quality-tuned WebP, target 25–40kb (from 177kb). Owner eyeballs before commit.

Explicitly not changing: Teaching absent from nav (intentional), hover-removes-underline link style (deliberate), overall layout/typography.

## Out of scope
- Local image mirroring/compression for post bodies (hotlink decision).
- Deleting posts removed from Substack.
- RSS/sitemap generation, comments, analytics.
