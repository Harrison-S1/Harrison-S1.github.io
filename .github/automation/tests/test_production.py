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


class ReproducibleBuildTests(unittest.TestCase):
    def test_frozen_build_is_byte_reproducible(self):
        import hashlib
        import os
        import subprocess
        import tempfile
        import time
        # Retain evidence in the runner temp directory; never clean source fixtures.
        target = Path(tempfile.mkdtemp(prefix='jekyll-reproducibility-'))
        env = dict(os.environ, JEKYLL_ENV='production', SOURCE_DATE_EPOCH='1793790000')
        manifests = []
        for name in ('first', 'second'):
            destination = target / name
            result = subprocess.run(['bundle', 'exec', 'jekyll', 'build', '--trace',
                                     '--destination', str(destination)], cwd=ROOT, env=env,
                                    capture_output=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            manifests.append({str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in destination.rglob('*') if p.is_file()})
            time.sleep(1.1)
        self.assertTrue(manifests[0])
        self.assertEqual(manifests[0], manifests[1], str(target))
        self.assertFalse(any(p.endswith('.css.map') for p in manifests[0]))

    def test_invalid_reproducible_epoch_fails_closed(self):
        import os
        import subprocess
        import tempfile
        target = Path(tempfile.mkdtemp(prefix='jekyll-invalid-epoch-'))
        for epoch in ('', 'not-a-timestamp', '0', '253402300800'):
            with self.subTest(epoch=epoch):
                result = subprocess.run(['bundle', 'exec', 'jekyll', 'build',
                                         '--destination', str(target / ('case-' + epoch))],
                                        cwd=ROOT, env=dict(os.environ, SOURCE_DATE_EPOCH=epoch),
                                        capture_output=True, timeout=120)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Invalid SOURCE_DATE_EPOCH', result.stderr.decode())

    def test_modern_theme_shell_assets_exist(self):
        import os
        import subprocess
        import tempfile
        from html.parser import HTMLParser
        from urllib.parse import urlsplit
        target = Path(tempfile.mkdtemp(prefix='jekyll-shell-assets-'))
        result = subprocess.run(['bundle', 'exec', 'jekyll', 'build', '--destination', str(target)],
                                cwd=ROOT, env=dict(os.environ, JEKYLL_ENV='production'),
                                capture_output=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        class Assets(HTMLParser):
            paths = set()
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if tag == 'script':
                    url = values.get('src', '')
                elif tag == 'link' and values.get('rel') in (
                        'icon', 'shortcut icon', 'apple-touch-icon', 'manifest', 'stylesheet'):
                    url = values.get('href', '')
                else:
                    return
                parsed = urlsplit(url)
                if not parsed.netloc and parsed.path.startswith('/'):
                    self.paths.add(parsed.path.lstrip('/'))
        assets = Assets()
        assets.feed((target / 'index.html').read_text())
        self.assertTrue(assets.paths)
        self.assertEqual([p for p in sorted(assets.paths) if not (target / p).is_file()], [])


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
