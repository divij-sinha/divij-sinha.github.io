# Substack Sync + Frontend Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the known frontend bugs in `index.html`, then add a zero-dependency pipeline that mirrors overlookedpod.substack.com posts as local pages and an auto-updated list in the Personal section.

**Architecture:** A single stdlib-only Python script (`scripts/sync_substack.py`) fetches the Substack JSON API, sanitizes `body_html` through an allowlist HTMLParser, writes one minimal page per post to `posts/<slug>.html`, and rewrites a marker-delimited block in `index.html`. A daily GitHub Action runs it and commits changes. No SSG, no npm, no pip.

**Tech Stack:** Python 3 stdlib (urllib, json, html.parser, unittest), GitHub Actions, `sips` + `cwebp` (one-off local image re-encode only).

## Global Constraints

- Minimalism in code: stdlib only, no new dependencies, no speculative features, no budget-enforcement machinery (owner's explicit preference).
- Site is hand-written static HTML at repo root; posts pages go in `posts/`; images in post bodies stay hotlinked to Substack's CDN.
- Generated output must be deterministic: re-running the script on unchanged API data produces byte-identical files.
- The spec is `docs/superpowers/specs/2026-07-06-substack-sync-and-frontend-fixes-design.md`.
- Owner review needed on: the two drafted card descriptions (Task 1) and the re-encoded photo (Task 3).

---

### Task 1: index.html content and CSS fixes

**Files:**
- Modify: `index.html`

**Interfaces:**
- Produces: corrected static content; no code interfaces.

- [ ] **Step 1: Fix the two `[site]` links**

In the Hospital Price Transparency card, change:

```html
<a href="https://ctastopwatch.miurban-dashboards.org">[site]</a>
```
(the one inside the card whose header is "Hospital Price Transparency") to:
```html
<a href="https://healthcare.miurban-dashboards.org/">[site]</a>
```

In the "Who Owns Chicago?" card, change its
```html
<a href="https://ctastopwatch.miurban-dashboards.org">[site]</a>
```
to:
```html
<a href="https://whoownschi.miurban-dashboards.org/">[site]</a>
```

The CTA StopWatch card's link to `ctastopwatch.miurban-dashboards.org` is correct and stays.

- [ ] **Step 2: Replace the two TODO card bodies**

ARPA Audit card: replace `TODO` with:
```
Dashboard auditing how Chicago allocated and spent its American Rescue Plan Act (ARPA) federal relief funds.
```

Property Tax Explainer card: replace `TODO` with:
```
Interactive explainer that breaks down Cook County property tax bills for any address or PIN and compares changes across assessment years.
```

(ARPA description drafted from context — the site itself is a JS dashboard with no crawlable text; flag both descriptions to the owner in the task report.)

- [ ] **Step 3: Fix the mail link**

```html
<a href="#">Mail - divijs at uchicago dot edu</a><br />
```
becomes
```html
<a href="mailto:divijs@uchicago.edu">Mail - divijs at uchicago dot edu</a><br />
```

- [ ] **Step 4: Fix the typo**

`help out in way I can` → `help out in any way I can`.

- [ ] **Step 5: Remove the dead h4 rule**

Delete:
```css
      h4 {
        font-family: "Gill Sans", "Gill Sans MT";
      }
```
(No `<h4>` exists in the document.)

- [ ] **Step 6: Add font preloads**

Immediately after the `<link rel="canonical" ...>` line, add:
```html
    <link rel="preload" href="Figtree-VariableFont_wght.woff2" as="font" type="font/woff2" crossorigin />
    <link rel="preload" href="Boldonse-Regular.woff2" as="font" type="font/woff2" crossorigin />
```

- [ ] **Step 7: Verify**

Run: `gzip -c index.html | wc -c` — expect roughly 5.6–5.8k (was 5,618).
Open the page locally (`open index.html`) and click the two fixed `[site]` links and the mail link.

- [ ] **Step 8: Commit**

```bash
git add index.html
git commit -m "fix: dashboard links, TODO cards, mailto, typo, dead css, font preloads"
```

---

### Task 2: Localize the Charizard sprite

**Files:**
- Create: `charizard.png` (repo root)
- Modify: `index.html` (the `.nav-sprite` img)

**Interfaces:**
- Produces: local sprite file; removes the site's only third-party request.

- [ ] **Step 1: Download the sprite**

```bash
curl -sL -o charizard.png https://img.pokemondb.net/sprites/ruby-sapphire/normal/charizard.png
ls -la charizard.png   # expect ~1-2kb PNG
file charizard.png     # expect: PNG image data
```

- [ ] **Step 2: Point the img at it**

In `index.html`:
```html
        <img
          src="https://img.pokemondb.net/sprites/ruby-sapphire/normal/charizard.png"
          alt="Pokemon Xanthic"
        />
```
becomes
```html
        <img src="charizard.png" alt="Pokemon Xanthic" />
```

- [ ] **Step 3: Verify**

`open index.html` — sprite renders next to the nav on a wide window.

- [ ] **Step 4: Commit**

```bash
git add charizard.png index.html
git commit -m "fix: serve nav sprite locally instead of hotlinking pokemondb"
```

---

### Task 3: Re-encode col.webp (177kb → ~30kb)

**Files:**
- Modify: `col.webp` (regenerated from `static/col_original.jpg`)

**Interfaces:**
- Produces: smaller `col.webp`, same filename so `index.html` needs no change.

- [ ] **Step 1: Resize with sips (applies EXIF rotation), then encode with cwebp**

```bash
sips --resampleWidth 640 static/col_original.jpg --out "$SCRATCHPAD/col640.jpg"
cwebp -q 80 "$SCRATCHPAD/col640.jpg" -o col.webp
ls -la col.webp   # expect ~20-45kb
```
(`$SCRATCHPAD` = the session scratchpad directory. Do not overwrite `static/col_original.jpg`.)

- [ ] **Step 2: Owner eyeballs**

Send/open `col.webp` and `open index.html` to confirm the photo looks right (orientation, sharpness at 320px display width). **Wait for owner confirmation before committing.**

- [ ] **Step 3: Commit**

```bash
git add col.webp
git commit -m "perf: re-encode about photo at 640px, 177kb -> ~30kb"
```

---

### Task 4: Sanitizer — `sanitize()` with tests

**Files:**
- Create: `scripts/sync_substack.py`
- Create: `scripts/test_sync_substack.py`

**Interfaces:**
- Produces: `sanitize(body_html: str, own_slugs: set[str]) -> str` — returns cleaned HTML fragment. Also module constants `SITE = "https://overlookedpod.substack.com"`.
- Tests run with: `python3 -m unittest discover scripts -v` (run from repo root).

- [ ] **Step 1: Write the failing tests**

Create `scripts/test_sync_substack.py`:

```python
import unittest

from sync_substack import sanitize


class TestSanitize(unittest.TestCase):
    def test_unwraps_wrappers_and_strips_attrs(self):
        html = '<div class="x"><p style="color:red">hi <em>there</em></p></div>'
        self.assertEqual(sanitize(html, set()), "<p>hi <em>there</em></p>")

    def test_drops_cruft_subtrees(self):
        html = (
            '<div class="subscription-widget-wrap">'
            '<form><input type="email"><p>Subscribe!</p></form></div>'
            '<p class="button-wrapper"><a class="button">Share</a></p>'
            "<p>keep</p>"
        )
        self.assertEqual(sanitize(html, set()), "<p>keep</p>")

    def test_keeps_img_adds_lazy_drops_picture_source(self):
        html = (
            '<picture><source srcset="x.avif">'
            '<img src="https://s.example/x.png" alt="pic" width="800" height="600" class="z">'
            "</picture>"
        )
        self.assertEqual(
            sanitize(html, set()),
            '<img src="https://s.example/x.png" alt="pic" width="800" height="600" loading="lazy">',
        )

    def test_rewrites_own_post_links_only(self):
        html = (
            '<p><a href="https://overlookedpod.substack.com/p/hello">a</a> '
            '<a href="https://overlookedpod.substack.com/p/other">b</a> '
            '<a href="https://example.com">c</a></p>'
        )
        out = sanitize(html, {"hello"})
        self.assertIn('href="/posts/hello"', out)
        self.assertIn('href="https://overlookedpod.substack.com/p/other"', out)
        self.assertIn('href="https://example.com"', out)

    def test_reescapes_text(self):
        self.assertEqual(sanitize("<p>a &lt; b &amp; c</p>", set()), "<p>a &lt; b &amp; c</p>")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd scripts && python3 -m unittest test_sync_substack -v; cd ..`
Expected: `ModuleNotFoundError: No module named 'sync_substack'` (or ImportError for `sanitize`).

- [ ] **Step 3: Implement the sanitizer**

Create `scripts/sync_substack.py`:

```python
"""Mirror overlookedpod.substack.com posts into this site.

Stdlib only. Fetches the Substack JSON API, sanitizes post bodies through a
tag allowlist, writes posts/<slug>.html, and rewrites the marker-delimited
list in index.html. Deterministic: unchanged input produces identical output.
"""

import html
import re
from html.parser import HTMLParser

SITE = "https://overlookedpod.substack.com"

ALLOWED = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "blockquote",
    "a", "img", "em", "strong", "b", "i", "code", "pre", "figure",
    "figcaption", "table", "thead", "tbody", "tr", "th", "td", "br", "hr",
    "sub", "sup",
}
VOID = {
    "img", "br", "hr", "input", "source", "embed", "wbr", "area", "base",
    "col", "link", "meta", "track", "param",
}
DROP = {"script", "style", "form", "button", "iframe", "svg", "input", "source", "audio", "video"}
DROP_CLASS_WORDS = ("subscri", "share", "button", "tweet")

_OWN_POST = re.compile(r"https?://overlookedpod\.substack\.com/p/([\w-]+)/?$")


class _Sanitizer(HTMLParser):
    def __init__(self, own_slugs):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.own_slugs = own_slugs

    def _dropped(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        return tag in DROP or any(w in cls for w in DROP_CLASS_WORDS)

    def _emit(self, tag, attrs):
        kept = []
        for k, v in attrs:
            v = v or ""
            if tag == "a" and k == "href":
                m = _OWN_POST.match(v)
                if m and m.group(1) in self.own_slugs:
                    v = "/posts/" + m.group(1)
                kept.append((k, v))
            elif tag == "img" and k in ("src", "alt", "width", "height"):
                kept.append((k, v))
        if tag == "img":
            kept.append(("loading", "lazy"))
        parts = "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in kept)
        self.out.append(f"<{tag}{parts}>")

    def handle_starttag(self, tag, attrs):
        if tag in VOID:
            if not self.skip and tag in ALLOWED and not self._dropped(tag, attrs):
                self._emit(tag, attrs)
            return
        if self.skip:
            self.skip += 1
        elif self._dropped(tag, attrs):
            self.skip = 1
        elif tag in ALLOWED:
            self._emit(tag, attrs)
        # any other tag (div, span, section, picture, ...): unwrap silently

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.skip:
            self.skip -= 1
        elif tag in ALLOWED:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(html.escape(data))


def sanitize(body_html, own_slugs):
    s = _Sanitizer(own_slugs)
    s.feed(body_html)
    s.close()
    return "".join(s.out)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_sync_substack -v; cd ..`
Expected: 5 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/sync_substack.py scripts/test_sync_substack.py
git commit -m "feat: substack body_html sanitizer, allowlist-based, stdlib only"
```

---

### Task 5: Rendering — post pages and index list, with tests

**Files:**
- Modify: `scripts/sync_substack.py` (append functions)
- Modify: `scripts/test_sync_substack.py` (append tests)

**Interfaces:**
- Consumes: `sanitize()` from Task 4.
- Produces:
  - `slug_of(post: dict) -> str`
  - `render_post(post: dict, body: str) -> str` — full HTML document for `posts/<slug>.html`
  - `render_items(posts: list[dict]) -> str` — grid-item block for index
  - `update_index(index_html: str, items: str) -> str` — replaces text between `<!-- substack:start -->` / `<!-- substack:end -->`

- [ ] **Step 1: Append failing tests to `scripts/test_sync_substack.py`**

```python
from sync_substack import render_items, render_post, slug_of, update_index

POST = {
    "title": "T & T",
    "slug": "t-t",
    "post_date": "2025-04-25T12:00:00.000Z",
    "description": "A  post\nabout <things>",
    "canonical_url": "https://overlookedpod.substack.com/p/t-t",
}


class TestRender(unittest.TestCase):
    def test_slug_of_falls_back_to_canonical_url(self):
        self.assertEqual(slug_of(POST), "t-t")
        self.assertEqual(slug_of({"canonical_url": "https://x.substack.com/p/abc"}), "abc")

    def test_render_post_page(self):
        page = render_post(POST, "<p>body</p>")
        self.assertIn("<title>T &amp; T - Divij Sinha</title>", page)
        self.assertIn("<p>body</p>", page)
        self.assertIn("25 April 2025", page)
        self.assertIn('href="https://overlookedpod.substack.com/p/t-t"', page)
        self.assertIn('content="A post about &lt;things&gt;"', page)

    def test_render_items(self):
        out = render_items([POST])
        self.assertIn('href="posts/t-t"', out)
        self.assertIn("T &amp; T", out)
        self.assertIn("Apr 2025", out)

    def test_update_index_is_idempotent(self):
        idx = "a\n      <!-- substack:start -->\nOLD\n      <!-- substack:end -->\nb"
        out = update_index(idx, "NEW")
        self.assertEqual(
            out, "a\n      <!-- substack:start -->\nNEW\n      <!-- substack:end -->\nb"
        )
        self.assertEqual(update_index(out, "NEW"), out)
```

Note: these imports go at the top of the test file alongside the existing import.

- [ ] **Step 2: Run to verify failure**

Run: `cd scripts && python3 -m unittest test_sync_substack -v; cd ..`
Expected: ImportError on `render_items`.

- [ ] **Step 3: Append implementation to `scripts/sync_substack.py`**

```python
from datetime import date

POST_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title} - Divij Sinha</title>
    <meta name="description" content="{description}" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="canonical" href="{canonical_url}" />
    <link rel="preload" href="/Figtree-VariableFont_wght.woff2" as="font" type="font/woff2" crossorigin />
    <link rel="preload" href="/Boldonse-Regular.woff2" as="font" type="font/woff2" crossorigin />
    <style>
      @font-face {{
        font-family: "Figtree";
        src: url("/Figtree-VariableFont_wght.woff2") format("woff2-variations");
        font-weight: 300 900;
        font-display: swap;
      }}
      @font-face {{
        font-family: "Boldonse";
        src: url("/Boldonse-Regular.woff2") format("woff2");
        font-weight: 400;
        font-display: swap;
      }}
      body {{
        margin: 0 auto;
        padding: 1rem 1rem 4rem;
        box-sizing: border-box;
        background: #eeeeee;
        color: #333333;
        font-family: "Figtree", sans-serif;
        font-size: 1.1rem;
        line-height: 1.6;
        max-width: 680px;
        width: 90%;
      }}
      h1 {{
        font-family: "Boldonse", system-ui;
        font-weight: 400;
        font-size: 1.5rem;
        line-height: 1.5;
      }}
      h2, h3, h4, h5, h6 {{
        font-family: "Boldonse", system-ui;
        font-weight: 400;
        font-size: 1.1rem;
      }}
      a {{
        border-bottom: 0.15rem solid #333333;
        color: #333333;
        text-decoration: none;
      }}
      a:hover {{
        border-bottom-color: #eeeeee;
      }}
      img {{
        max-width: 100%;
        height: auto;
      }}
      blockquote {{
        border-left: 0.2rem solid #a0a0a0;
        margin: 1rem 0;
        padding: 0 0.75rem;
        color: #555555;
      }}
      pre {{
        overflow-x: auto;
      }}
      .meta {{
        color: #555555;
        font-size: 0.9rem;
      }}
      .home {{
        font-family: "Boldonse", system-ui;
        font-size: 0.9rem;
      }}
    </style>
  </head>

  <body>
    <p class="home"><a href="/">Divij Sinha</a></p>
    <h1>{title}</h1>
    <p class="meta">{long_date} &middot; <a href="{canonical_url}">on substack</a></p>
    {body}
  </body>
</html>
"""

ITEM = """      <div class="grid-item">
        <div class="item-header">
          <a href="posts/{slug}">{title}</a>
        </div>
        <div class="item-body">{short_date} &mdash; {description}</div>
      </div>"""


def slug_of(post):
    return post.get("slug") or post["canonical_url"].rstrip("/").rsplit("/", 1)[-1]


def _clean(text):
    return html.escape(" ".join((text or "").split()))


def _dt(post):
    return date.fromisoformat(post["post_date"][:10])


def render_post(post, body):
    d = _dt(post)
    return POST_PAGE.format(
        title=_clean(post["title"]),
        description=_clean(post.get("description")),
        canonical_url=post["canonical_url"],
        long_date=f"{d.day} {d.strftime('%B %Y')}",
        body=body,
    )


def render_items(posts):
    return "\n".join(
        ITEM.format(
            slug=slug_of(p),
            title=_clean(p["title"]),
            short_date=_dt(p).strftime("%b %Y"),
            description=_clean(p.get("description")),
        )
        for p in posts
    )


START, END = "<!-- substack:start -->", "<!-- substack:end -->"


def update_index(index_html, items):
    pre, _, rest = index_html.partition(START)
    _, _, post = rest.partition(END)
    return pre + START + "\n" + items + "\n      " + END + post
```

Note: `import html` already exists at the top from Task 4; only `from datetime import date` is new (place it with the other imports at the top of the file).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd scripts && python3 -m unittest test_sync_substack -v; cd ..`
Expected: 9 tests, all PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/sync_substack.py scripts/test_sync_substack.py
git commit -m "feat: post page and index list rendering for substack sync"
```

---

### Task 6: Fetch + main, index markers, first real sync

**Files:**
- Modify: `scripts/sync_substack.py` (append `fetch_posts` and `main`)
- Modify: `index.html` (replace the two hand-written Substack cards with markers)
- Create: `posts/*.html` (generated)

**Interfaces:**
- Consumes: everything from Tasks 4–5.
- Produces: runnable `python3 scripts/sync_substack.py`; marker block in `index.html`.

- [ ] **Step 1: Append fetch/main to `scripts/sync_substack.py`**

```python
import json
from pathlib import Path
from urllib.request import Request, urlopen


def fetch_posts():
    posts, offset = [], 0
    while True:
        req = Request(
            f"{SITE}/api/v1/posts?limit=50&offset={offset}",
            headers={"User-Agent": "Mozilla/5.0 (divij-sinha.github.io sync)"},
        )
        with urlopen(req, timeout=30) as resp:
            batch = json.load(resp)
        posts += batch
        if len(batch) < 50:
            return posts
        offset += 50


def main():
    root = Path(__file__).resolve().parent.parent
    posts = [
        p for p in fetch_posts()
        if p.get("is_published") and p.get("audience") == "everyone"
    ]
    posts.sort(key=lambda p: p["post_date"], reverse=True)
    own_slugs = {slug_of(p) for p in posts}

    (root / "posts").mkdir(exist_ok=True)
    for p in posts:
        body = sanitize(p.get("body_html") or "", own_slugs)
        path = root / "posts" / f"{slug_of(p)}.html"
        path.write_text(render_post(p, body), encoding="utf-8")

    index = root / "index.html"
    index.write_text(
        update_index(index.read_text(encoding="utf-8"), render_items(posts)),
        encoding="utf-8",
    )
    print(f"synced {len(posts)} posts")


if __name__ == "__main__":
    main()
```

(Imports go at the top of the file with the others.)

- [ ] **Step 2: Put markers in index.html**

In the Personal section's `grid-container`, delete these two hand-written cards entirely:
- the card headed "A series exploring IPL through data" (with the `[Part 1: ...]` link)
- the card headed with the link "Whose value is it anyways?"

In their place (as the first children of the grid container, before the Job Harvester card) insert:

```html
      <!-- substack:start -->
      <!-- substack:end -->
```

- [ ] **Step 3: Run the sync**

Run: `python3 scripts/sync_substack.py`
Expected: `synced 5 posts`; `posts/` contains 5 `.html` files; `git diff index.html` shows 5 generated cards between the markers.

- [ ] **Step 4: Verify idempotence and output quality**

```bash
python3 scripts/sync_substack.py
git status --short   # expect: same file list, no new changes vs after step 3
gzip -c index.html | wc -c
for f in posts/*.html; do printf '%s ' "$f"; gzip -c "$f" | wc -c; done
```
Open the biggest page: `open posts/ipl-series-part-1-teams-and-stadiums.html` (slug per API) — check headings, images (hotlinked, lazy), no subscribe/share widgets, links work. Open `index.html` — Personal grid shows 5 post cards, newest first.

- [ ] **Step 5: Commit**

```bash
git add scripts/sync_substack.py index.html posts/
git commit -m "feat: substack sync script wired into index; first mirrored posts"
```

---

### Task 7: GitHub Action

**Files:**
- Create: `.github/workflows/substack-sync.yml`

**Interfaces:**
- Consumes: `scripts/sync_substack.py` CLI entry point.

- [ ] **Step 1: Write the workflow**

```yaml
name: Sync Substack
on:
  schedule:
    - cron: "0 6 * * *"
  workflow_dispatch:
permissions:
  contents: write
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python3 scripts/sync_substack.py
      - run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -A
          git diff --cached --quiet || { git commit -m "content: sync substack posts" && git push; }
```

- [ ] **Step 2: Commit and push everything**

```bash
git add .github/workflows/substack-sync.yml
git commit -m "ci: daily substack sync workflow"
git push
```

- [ ] **Step 3: Verify end-to-end in CI**

```bash
gh workflow run substack-sync.yml
gh run watch $(gh run list --workflow=substack-sync.yml --limit 1 --json databaseId -q '.[0].databaseId')
```
Expected: run succeeds; since Task 6 already synced, it commits nothing. Then check the live site once Pages redeploys.
