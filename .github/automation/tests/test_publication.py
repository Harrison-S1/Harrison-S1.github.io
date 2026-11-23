"""Offline native Pages handoff tests. These are NOT live deployment evidence."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
SHA = 'c' * 40
WORKFLOW = '.github/workflows/pages-deploy.yml'


class PagesAPI:
    def __init__(self):
        self.writes = []
        self.main = SHA
    def get(self, path):
        if path == '/git/ref/heads/main':
            return {'object': {'sha': self.main}}
        if path == '/actions/workflows/pages-deploy.yml':
            return {'id': 77, 'path': WORKFLOW, 'state': 'active'}
        raise AssertionError(path)
    def pages(self, path, key=None):
        if not self.writes:
            return []
        return [{'id': 100, 'workflow_id': 77, 'head_sha': SHA, 'path': WORKFLOW,
                 'event': 'workflow_dispatch', 'display_title': 'Publish ' + SHA,
                 'html_url': 'https://github.com/Harrison-S1/Harrison-S1.github.io/actions/runs/100'}]
    def write(self, method, path, payload):
        self.writes.append((method, path, payload))
        return None


class PublicationTests(unittest.TestCase):
    def test_pages_gate_ref_sha_and_main_binding(self):
        from pages_guard import verify
        api = PagesAPI()
        verify(api, SHA, SHA, 'refs/heads/main', 'workflow_dispatch')
        for expected, actual, ref, event in [(SHA, 'd' * 40, 'refs/heads/main', 'workflow_dispatch'),
                                             (SHA, SHA, 'refs/heads/evil', 'workflow_dispatch'),
                                             (SHA, SHA, 'refs/heads/main', 'pull_request'),
                                             ('main', SHA, 'refs/heads/main', 'workflow_dispatch')]:
            with self.subTest(ref=ref, actual=actual), self.assertRaises(ValueError):
                verify(api, expected, actual, ref, event)
        api.main = 'd' * 40
        with self.assertRaises(ValueError):
            verify(api, SHA, SHA, 'refs/heads/main', 'push')

    def test_exact_merged_sha_dispatch_is_read_back(self):
        from publication import dispatch
        api = PagesAPI()
        result = dispatch(api, SHA, sleep=lambda _: None)
        self.assertEqual(result['run_id'], 100)
        self.assertEqual(api.writes, [('POST', '/actions/workflows/pages-deploy.yml/dispatches',
                                      {'ref': 'main', 'inputs': {'expected_sha': SHA}})])
        api = PagesAPI()
        api.main = 'd' * 40
        with self.assertRaises(ValueError):
            dispatch(api, SHA, sleep=lambda _: None)
        self.assertEqual(api.writes, [])


if __name__ == '__main__':
    unittest.main()
