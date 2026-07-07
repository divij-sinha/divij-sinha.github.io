import unittest

from sync_substack import (
    render_items,
    render_post,
    sanitize,
    slug_of,
    toc_and_ids,
    update_index,
)

POST = {
    "title": "T & T",
    "slug": "t-t",
    "post_date": "2025-04-25T12:00:00.000Z",
    "description": "A  post\nabout <things>",
    "canonical_url": "https://overlookedpod.substack.com/p/t-t",
}


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

    def test_intext_footnote_anchor_gets_sup(self):
        html = (
            '<p>fact<a class="footnote-anchor" id="footnote-anchor-1" '
            'href="#footnote-1" target="_self">1</a></p>'
        )
        self.assertEqual(
            sanitize(html, set()),
            '<p>fact<sup><a id="footnote-anchor-1" href="#footnote-1">1</a></sup></p>',
        )

    def test_footnote_block_kept_and_urls_linkified(self):
        html = (
            '<div class="footnote" data-component-name="FootnoteToDOM">'
            '<a id="footnote-1" href="#footnote-anchor-1" class="footnote-number">1</a>'
            '<div class="footnote-content"><p>see https://example.com/x for more</p></div>'
            "</div>"
        )
        self.assertEqual(
            sanitize(html, set()),
            '<div class="footnote"><a id="footnote-1" href="#footnote-anchor-1">1</a>'
            '<p>see <a href="https://example.com/x">https://example.com/x</a> for more</p></div>',
        )


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
        self.assertIn('<a href="/">home</a>', page)

    def test_render_items(self):
        out = render_items([POST])
        self.assertIn('href="posts/t-t"', out)
        self.assertIn("T &amp; T", out)
        self.assertIn("Apr 2025", out)

    def test_toc_and_ids(self):
        body = "<h2>Introduction</h2><p>x</p><h3>The Teams!</h3><h2>Introduction</h2>"
        out, toc = toc_and_ids(body)
        self.assertEqual(
            out,
            '<h2 id="introduction">Introduction</h2><p>x</p>'
            '<h3 id="the-teams">The Teams!</h3><h2 id="introduction-2">Introduction</h2>',
        )
        self.assertEqual(
            toc,
            [
                ("h2", "introduction", "Introduction"),
                ("h3", "the-teams", "The Teams!"),
                ("h2", "introduction-2", "Introduction"),
            ],
        )

    def test_render_post_with_toc(self):
        page = render_post(POST, "<h2>Alpha</h2><p>x</p><h3>Beta</h3>")
        self.assertIn('<h2 id="alpha">Alpha</h2>', page)
        self.assertIn('<a href="#alpha">Alpha</a>', page)
        self.assertIn('<a class="h3" href="#beta">Beta</a>', page)
        self.assertIn("getBoundingClientRect", page)

    def test_render_post_without_headings_has_no_toc(self):
        page = render_post(POST, "<p>just text</p>")
        self.assertNotIn("<nav", page)
        self.assertNotIn("<script", page)

    def test_update_index_is_idempotent(self):
        idx = "a\n      <!-- substack:start -->\nOLD\n      <!-- substack:end -->\nb"
        out = update_index(idx, "NEW")
        self.assertEqual(
            out, "a\n      <!-- substack:start -->\nNEW\n      <!-- substack:end -->\nb"
        )
        self.assertEqual(update_index(out, "NEW"), out)


if __name__ == "__main__":
    unittest.main()
