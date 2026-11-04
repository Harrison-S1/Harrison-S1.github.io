"""Git object mode/size and built-link checks; temporary fixtures are retained."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ValidationTests(unittest.TestCase):
    def test_actual_rendered_article_safety(self):
        from validate_content import rendered_article
        valid = '<div class="post-content"><h2 id="hi">Hi</h2><p><a href="/ok/">OK</a></p></div>'
        self.assertIn('/ok/', rendered_article(valid))
        for fragment in ['<img src="/image.png" onerror="alert(1)">',
                         '<a href="javascript:alert(1)">bad</a>', '<script>alert(1)</script>',
                         '<iframe src="https://evil.test"></iframe>', '<svg></svg>',
                         '<img srcset="javascript:alert(1)">', '<p style="color:red">x</p>']:
            with self.subTest(fragment=fragment), self.assertRaises(ValueError):
                rendered_article('<div class="post-content">' + fragment + '</div>')
        with self.assertRaises(ValueError):
            rendered_article('<p>Missing content wrapper</p>')

    def test_duplicate_post_slug_rejected(self):
        from validate_content import check_slugs
        check_slugs(['_posts/2026-11-04-example.md'], ['_posts/2026-11-04-example.md'])
        with self.assertRaises(ValueError):
            check_slugs(['_posts/2026-11-04-example.md', '_posts/2025-01-01-example.md'],
                        ['_posts/2026-11-04-example.md'])

    def test_git_entries_fail_closed(self):
        from validate_content import check_entry
        check_entry('100644', 'blob', 20, '_posts/2026-11-04-example.md')
        for mode, typ, size in [('100755', 'blob', 20), ('120000', 'blob', 20),
                                ('160000', 'commit', 20), ('100644', 'blob', 100001)]:
            with self.subTest(mode=mode, typ=typ, size=size), self.assertRaises(ValueError):
                check_entry(mode, typ, size, '_posts/2026-11-04-example.md')

    def test_built_links_and_fragments(self):
        from validate_content import check_links
        root = Path(tempfile.mkdtemp(prefix='blog-links-', dir=os.environ.get('TMPDIR')))
        (root / 'posts/demo').mkdir(parents=True)
        (root / 'posts/demo/index.html').write_text('<h2 id="example">Example</h2>')
        check_links(root, '/posts/demo/', ['#example', '/posts/demo/#example', 'https://example.com'])
        for value in ['#missing', '/missing/', '/posts/demo/#missing', '/%2e%2e/no']:
            with self.subTest(link=value), self.assertRaises(ValueError):
                check_links(root, '/posts/demo/', [value])


if __name__ == '__main__':
    unittest.main()
