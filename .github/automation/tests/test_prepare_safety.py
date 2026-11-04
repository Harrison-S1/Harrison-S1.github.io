"""LOCAL Git-object fixtures, no network, external credentials or PR execution."""
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_policy import PATH, POST, pr
import validate_content as validation
import content_policy as policy


class PrepareSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='policy-git-', dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.root), 'GIT_CONFIG_NOSYSTEM': '1',
                    'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_AUTHOR_NAME': 'Local fixture',
                    'GIT_AUTHOR_EMAIL': 'fixture@example.invalid', 'GIT_COMMITTER_NAME': 'Local fixture',
                    'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
                    'GIT_AUTHOR_DATE': '2026-11-04T08:00:00+0000',
                    'GIT_COMMITTER_DATE': '2026-11-04T08:00:00+0000'}
        self.git('-c', 'init.templateDir=', 'init', '-q')
        self.git('config', 'core.filemode', 'false')
        (self.repo / 'README.md').write_text('Trusted base fixture\n')
        self.commit()
        self.base = self.git('rev-parse', 'HEAD').decode().strip()

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.repo, env=self.env, timeout=15, stderr=subprocess.STDOUT)

    def commit(self):
        self.git('add', '--all')
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Local fixture only')

    def add_post(self):
        path = self.repo / PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(POST)

    def prepare(self, count):
        self.commit()
        head = self.git('rev-parse', 'HEAD').decode().strip()
        self.git('checkout', '-q', '--detach', self.base)
        pull = pr()
        pull['head']['sha'], pull['base']['sha'], pull['changed_files'] = head, self.base, count
        manifest = self.root / 'manifest.json'
        with patch('validate_content.git', side_effect=self.git):
            validation.prepare(pull, self.base, self.root / 'overlay', manifest, fetcher=lambda _: None)
        return json.loads(manifest.read_text())

    def test_exact_objects_overlay_passive_image_and_arithmetic(self):
        from PIL import Image
        self.add_post()
        image = self.repo / 'assets/img/posts/a-useful-example/image.png'
        image.parent.mkdir(parents=True)
        Image.new('RGB', (2, 2), 'white').save(image)
        example = self.repo / 'examples/posts/a-useful-example/test.py'
        example.parent.mkdir(parents=True)
        example.write_text('x = 3 * 4\nassert x == 12\n')
        report = self.prepare(3)
        self.assertEqual(len(report['files']), 3)
        self.assertEqual(report['head_commit_timestamp'], 1793779200)
        self.assertEqual((self.root / 'overlay' / PATH).read_bytes(), POST)
        self.assertEqual((self.root / 'overlay/README.md').read_text(), 'Trusted base fixture\n')

    def test_symlink_post_is_rejected_before_overlay(self):
        self.add_post()
        (self.repo / PATH).unlink()
        (self.repo / PATH).symlink_to('../README.md')
        with self.assertRaisesRegex(ValueError, 'symlink/executable/non-blob'):
            self.prepare(1)
        self.assertFalse((self.root / 'overlay').exists())

    def test_executable_mode_is_rejected_from_git_not_host_bits(self):
        self.add_post()
        self.git('add', '--all')
        self.git('update-index', '--chmod=+x', PATH)
        # Commit directly: another git-add would replace the synthetic mode.
        self.git('-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'Executable local fixture')
        head = self.git('rev-parse', 'HEAD').decode().strip()
        self.git('checkout', '-q', '--detach', self.base)
        pull = pr()
        pull['head']['sha'], pull['base']['sha'] = head, self.base
        with patch('validate_content.git', side_effect=self.git), self.assertRaises(ValueError):
            validation.prepare(pull, self.base, self.root / 'overlay', self.root / 'manifest', fetcher=lambda _: None)

    def test_mixed_infrastructure_change_is_manual(self):
        self.add_post()
        (self.repo / 'Gemfile').write_text('Untrusted dependency fixture\n')
        with self.assertRaisesRegex(ValueError, 'manual-review path'):
            self.prepare(2)

    def test_future_head_timestamp_is_rejected(self):
        with patch('validate_content.git', return_value=b'1793797011\n'), patch('time.time', return_value=1793797010):
            with self.assertRaisesRegex(ValueError, 'future-dated'):
                validation.commit_timestamp('b' * 40)

    def test_json_budget_and_non_data_constructs_are_manual(self):
        for data in (b'NaN', b'1.0', b'null', b'"secret fixture"', b'{"x":1,"x":2}',
                     b'[1000001]', b'[' * 14 + b'1' + b']' * 14,
                     b'[' + b'1,' * 200 + b'1]'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                policy.example('examples/posts/a-useful-example/data.json', data)


if __name__ == '__main__':
    unittest.main()
