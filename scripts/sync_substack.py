"""Mirror overlookedpod.substack.com posts into this site.

Stdlib only. Fetches the Substack JSON API, sanitizes post bodies through a
tag allowlist, writes posts/<slug>.html, and rewrites the marker-delimited
list in index.html. Deterministic: unchanged input produces identical output.
"""

import html
import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

SITE = "https://overlookedpod.substack.com"
EXCLUDE = {"ideas", "hello", "coming-soon"}

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
        if p.get("is_published")
        and p.get("audience") == "everyone"
        and slug_of(p) not in EXCLUDE
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
