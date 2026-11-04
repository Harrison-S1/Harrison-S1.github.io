"""Reviewed production foundation contracts; all examples are offline fixtures."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ROOT = Path(__file__).resolve().parents[3]


class FoundationTests(unittest.TestCase):
    def test_supported_pinned_foundation(self):
        self.assertEqual((ROOT / '.ruby-version').read_text().strip(), '3.4.12')
        gems = (ROOT / 'Gemfile').read_text()
        self.assertIn('"jekyll-theme-chirpy", "7.6.0"', gems)
        self.assertIn('"jekyll", "4.4.1"', gems)
        self.assertIn('2.6.9', (ROOT / 'Gemfile.lock').read_text())
        self.assertIn('CHECKSUMS\n', (ROOT / 'Gemfile.lock').read_text())


class TechnicalContentTests(unittest.TestCase):
    def test_renderer_transport_allows_unicode_and_escaping_within_body_limit(self):
        from validate_content import check_markdown
        for body in ['## Heading\n\n' + '\u6f22\u5b57' * 14000, '## Heading\n\n' + '\\' * 60000]:
            with self.subTest(utf8_bytes=len(body.encode())):
                self.assertEqual(check_markdown(body), [])
        with self.assertRaises(ValueError):
            check_markdown('x' * 100001)

    def test_chirpy_seven_content_wrapper(self):
        from validate_content import rendered_article
        self.assertEqual(rendered_article('<article><div class="content"><p>Safe</p></div></article>'), [])

    def test_renderer_and_fence_checks_are_integrated(self):
        from validate_content import check_markdown
        self.assertEqual(check_markdown('Use `x < 3`.\n\n```python\nx = 1 + 2\n```\n'), [])
        for body in ['` <img src="x" onerror="bad"> `', '` [x](javascript:alert(1)) `',
                     '```python\nif :\n```\n', '```bash\nif then\n```\n']:
            with self.subTest(body=body), self.assertRaises((ValueError, SyntaxError)):
                check_markdown(body)
        self.assertIn('/missing/', check_markdown('` [broken](/missing/) `'))

    def test_exact_kramdown_rejects_disguised_html(self):
        import subprocess
        import json
        script = ROOT / '.github/automation/render_check.rb'
        def render(body):
            return subprocess.run(['bundle', 'exec', 'ruby', str(script)],
                                  input=json.dumps({'body': body}).encode(),
                                  capture_output=True, timeout=30)
        good = render('Use `x < 3` and `{{ variable }}`.\n\n```jinja\n{% if x %}ok{% endif %}\n```\n')
        self.assertEqual(good.returncode, 0, good.stderr.decode())
        self.assertIn('&lt;', good.stdout.decode())
        for attack in ['` <img src="x" onerror="alert(1)"> `', '</div><script>bad</script>',
                       '<!-- hidden -->', '<iframe src="x"></iframe>']:
            with self.subTest(attack=attack):
                self.assertNotEqual(render(attack).returncode, 0)

    def test_literal_code_and_jinja_with_liquid_disabled(self):
        import content_policy
        from test_policy import POST, PATH
        data = POST.replace(b'layout: post', b'layout: post\nrender_with_liquid: false')
        data += b'\nUse `x < 3` and `{{ variable }}` as literal examples.\n\n```jinja\n{{ variable }}\n{% if enabled %}ok{% endif %}\n```\n'
        self.assertIn('https://example.com/docs', content_policy.post(PATH, data))


class CompanionTests(unittest.TestCase):
    def test_example_mode_and_size_limits(self):
        from validate_content import check_entry
        check_entry('100644', 'blob', 50, 'examples/posts/a-useful-example/test.py')
        with self.assertRaises(ValueError):
            check_entry('100644', 'blob', 20001, 'examples/posts/a-useful-example/test.py')

    def test_passive_examples_and_bounded_arithmetic_tests(self):
        import content_policy as p
        from test_policy import PATH
        path = 'examples/posts/a-useful-example/calculation.py'
        p.file_policy([{'filename': PATH, 'status': 'added'}, {'filename': path, 'status': 'added'}])
        self.assertEqual(p.example(path, b'x = 2 + 3\nassert x == 5\n'), {'assertions': 1})
        for code in [b'import os\n', b'open("x")\n', b'x = 2 ** 100000\n', b'while True: pass\n',
                     b'x = 4\nassert x == 5\n', b'x = "a" * 1000000\n', b'assert (1).__class__\n']:
            with self.subTest(code=code), self.assertRaises((ValueError, AssertionError)):
                p.example(path, code)
        with self.assertRaises(ValueError):
            p.file_policy([{'filename': PATH, 'status': 'added'},
                           {'filename': 'examples/posts/a-useful-example/deploy.yml', 'status': 'added'}])


if __name__ == '__main__':
    unittest.main()
