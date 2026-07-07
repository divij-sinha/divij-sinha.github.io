import unittest

from sync_substack import render_items, render_post, sanitize, slug_of, update_index

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


if __name__ == "__main__":
    unittest.main()
