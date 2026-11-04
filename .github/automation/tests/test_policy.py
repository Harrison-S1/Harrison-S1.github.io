"""Deterministic content gate regression tests. No network or merge operations."""
import base64
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def policy():
    import content_policy
    return content_policy


POST = b'''---
layout: post
title: "A useful example"
date: 2026-11-04 08:00:00 +0000
categories: [linux]
tags: [linux, testing]
---

## A meaningful heading

This is enough explanatory prose for a useful deterministic validation fixture, not a claim of technical correctness.

[Source](https://example.com/docs)

```bash
printf '%s\\n' 'never executed'
```
'''
PATH = '_posts/2026-11-04-a-useful-example.md'


def pr():
    return {'number': 42, 'state': 'open', 'draft': False,
            'user': {'login': 'Harrison-S1', 'id': 54186142},
            'base': {'ref': 'main', 'sha': 'a' * 40, 'repo': {'full_name': 'Harrison-S1/Harrison-S1.github.io'}},
            'head': {'sha': 'b' * 40, 'repo': {'full_name': 'Harrison-S1/Harrison-S1.github.io'}},
            'changed_files': 1}


class PolicyTests(unittest.TestCase):
    def test_positive_post_and_metadata(self):
        p = policy()
        p.metadata(pr())
        p.file_policy([{'filename': PATH, 'status': 'added'}])
        links = p.post(PATH, POST)
        self.assertIn('https://example.com/docs', links)

    def test_metadata_fail_closed(self):
        for keys, value in [
            (('state',), 'closed'), (('draft',), True),
            (('user', 'login'), 'mallory'), (('user', 'id'), 1),
            (('base', 'ref'), 'other'), (('head', 'repo'), None),
            (('head', 'repo', 'full_name'), 'mallory/fork'),
            (('head', 'sha'), '$(touch /tmp/no)'),
            (('changed_files',), 0), (('changed_files',), 21),
        ]:
            with self.subTest(keys=keys, value=value):
                obj = pr()
                target = obj
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = value
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    policy().metadata(obj)

    def test_mixed_paths_and_file_operations_rejected(self):
        p = policy()
        for path in ['Gemfile', '_config.yml', '.github/workflows/x.yml',
                     '_plugins/x.rb', 'examples/ansible/main.yml',
                     'assets/img/posts/demo/x.svg', 'assets/img/posts/demo/x.html',
                     '_posts/../_config.yml', '_posts/2026-11-04-Bad.md']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                p.file_policy([{'filename': PATH, 'status': 'added'},
                               {'filename': path, 'status': 'added'}])
        for status in ('removed', 'renamed', 'copied', 'changed', 'unknown'):
            with self.subTest(status=status), self.assertRaises(ValueError):
                p.file_policy([{'filename': PATH, 'status': status}])

    def test_unsafe_markdown_and_yaml_rejected(self):
        attacks = [b'` <img src="x" onerror="alert(1)"> `',
                   b'` [click](javascript:alert(1)) `', b'` [broken](/missing/) `',
                   b'{{ site.data }}', b'{% include evil %}',
                   b'{% raw %}<script>alert(1)</script>{% endraw %}',
                   b'<img src=x onerror=alert(1)>', b'&lt;script&gt;',
                   b'[click](javascript:alert%281%29)', b'[click](data:text/html,evil)',
                   b'[click](http://example.com)', b'[click](//evil.test/x)',
                   b'[click](/%2e%2e/_config.yml)', b'[click](https://u:p@example.com)',
                   b'[missing][unknown]', b'{: onclick="evil"}', b'```bash\necho nope',
                   b'<!-- unsafe -->', b'<?php nope ?>', b'\x00']
        for attack in attacks:
            with self.subTest(attack=attack), self.assertRaises((ValueError, UnicodeError)):
                policy().post(PATH, POST + b'\n' + attack + b'\n')
        for old, new in [(b'layout: post', b'layout: post\npermalink: /index.html'),
                         (b'layout: post', b'layout: post\nlayout: page'),
                         (b'title: "A useful example"', b'title: &t "A useful example"'),
                         (b'title: "A useful example"', b'title: !!str "A useful example"'),
                         (b'2026-11-04 08:00:00 +0000', b'2026-11-05 08:00:00 +0000'),
                         (b'categories: [linux]', b'categories: ["<script>"]')]:
            with self.subTest(new=new), self.assertRaises(Exception):
                policy().post(PATH, POST.replace(old, new))

    def test_raster_decode_and_limits(self):
        from PIL import Image
        import io
        buf = io.BytesIO()
        Image.new('RGB', (2, 2), 'white').save(buf, format='PNG')
        self.assertTrue(policy().image('assets/img/posts/test/test.png', buf.getvalue()))
        for path, data in [('test.jpg', buf.getvalue()), ('test.png', b'<svg/>'),
                           ('test.png', b'x' * 2_000_001), ('test.png', buf.getvalue()[:20])]:
            with self.subTest(path=path, length=len(data)), self.assertRaises(Exception):
                policy().image(path, data)
        with self.assertRaises(ValueError):
            policy().post(PATH, b'x' * 100_001)


if __name__ == '__main__':
    unittest.main()
