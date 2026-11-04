"""Offline orchestration contract tests: the only writes are captured FakeAPI calls."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_policy import PATH, pr

BASE = 'a' * 40
HEAD = 'b' * 40
PREFIX = '/repos/Harrison-S1/Harrison-S1.github.io'


def fixture():
    pull = pr()
    pull['mergeable'] = True
    pull['mergeable_state'] = 'clean'
    run = {'id': 7, 'run_attempt': 1, 'workflow_id': 12, 'path': '.github/workflows/blog-content.yml',
           'event': 'pull_request', 'status': 'completed', 'conclusion': 'success',
           'head_sha': HEAD, 'repository': {'full_name': 'Harrison-S1/Harrison-S1.github.io'},
           'head_repository': {'full_name': 'Harrison-S1/Harrison-S1.github.io'},
           'pull_requests': [{'number': 42, 'head': {'sha': HEAD}, 'base': {'sha': BASE}}],
           'check_suite_id': 8}
    return {
        '/actions/runs/7': run,
        '/actions/workflows/blog-content.yml': {'id': 12, 'path': run['path'], 'state': 'active'},
        '/actions/workflows/12/runs?event=pull_request&head_sha=' + HEAD: [run],
        '/actions/runs/7/jobs': [{'name': 'Blog content / validate', 'conclusion': 'success', 'status': 'completed'}],
        '/check-suites/8': {'head_sha': HEAD, 'app': {'slug': 'github-actions'}},
        '/pulls/42': pull,
        '/pulls/42/reviews/99': {'id': 99, 'state': 'APPROVED', 'commit_id': HEAD,
                                 'user': {'login': 'github-actions[bot]'}},
        '/pulls/42/files': [{'filename': PATH, 'status': 'added'}],
        '/git/trees/' + HEAD + '?recursive=1': {'truncated': False, 'tree': [
            {'path': PATH, 'mode': '100644', 'type': 'blob', 'size': 500}]},
        '/git/ref/heads/main': {'object': {'sha': BASE}},
        '/commits/' + HEAD + '/check-runs': [{'name': 'Blog content / validate', 'status': 'completed',
                                             'conclusion': 'success', 'check_suite': {'id': 8},
                                             'app': {'slug': 'github-actions'}}],
        '/commits/' + HEAD + '/status': {'total_count': 0, 'statuses': []},
    }


class FakeAPI:
    def __init__(self):
        self.data = fixture()
        self.writes = []
        self.approved = True
        self.strict = True
        self.stale_after_review = False
        self.merge_result = {'merged': True, 'sha': 'c' * 40}

    def get(self, path):
        if path == '/pulls/42' and any(w[0].endswith('/merge') for w in self.writes):
            obj = copy.deepcopy(self.data[path])
            obj.update(merged=True, merge_commit_sha='c' * 40)
            return obj
        return copy.deepcopy(self.data[path])

    def pages(self, path, key=None):
        return self.get(path)

    def write(self, method, path, payload):
        self.writes.append((path, payload))
        if path.endswith('/reviews'):
            if self.stale_after_review:
                self.data['/pulls/42']['head']['sha'] = 'd' * 40
            return {'id': 99, 'state': 'APPROVED', 'commit_id': HEAD}
        return self.merge_result

    def review_state(self, number):
        return {'reviewDecision': 'APPROVED' if self.approved else 'REVIEW_REQUIRED',
                'mergeStateStatus': 'CLEAN' if self.approved else 'BLOCKED',
                'headRefOid': HEAD, 'baseRefOid': BASE,
                'baseRef': {'branchProtectionRule': {
                    'requiresStrictStatusChecks': self.strict, 'requiresStatusChecks': self.strict,
                    'requiredStatusCheckContexts': ['Trusted base / Jekyll build']}}}


class OrchestrationTests(unittest.TestCase):
    def call(self, api):
        from orchestrate import orchestrate
        return orchestrate(api, 7, 1, BASE)

    def test_positive_exact_sha_and_policy_merge(self):
        api = FakeAPI()
        self.assertEqual(self.call(api)['result'], 'merged')
        self.assertEqual(api.writes[0][1]['commit_id'], HEAD)
        self.assertEqual(api.writes[1][1], {'sha': HEAD, 'merge_method': 'squash'})

    def test_normal_policy_block_does_not_merge(self):
        api = FakeAPI()
        api.approved = False
        self.assertEqual(self.call(api)['result'], 'manual-policy-required')
        self.assertEqual(len(api.writes), 1)

    def test_unconfirmed_review_cannot_merge(self):
        api = FakeAPI()
        api.data['/pulls/42/reviews/99']['state'] = 'DISMISSED'
        with self.assertRaises(ValueError):
            self.call(api)
        self.assertEqual(len(api.writes), 1)

    def test_missing_strict_required_checks_cannot_merge(self):
        api = FakeAPI()
        api.strict = False
        self.assertEqual(self.call(api)['result'], 'manual-policy-required')
        self.assertEqual(len(api.writes), 1)

    def test_unsafe_or_stale_results_never_approve(self):
        mutations = [
            ('/actions/runs/7', 'conclusion', 'failure'),
            ('/actions/runs/7', 'conclusion', 'cancelled'),
            ('/actions/runs/7', 'event', 'push'),
            ('/actions/runs/7', 'workflow_id', 999),
            ('/actions/runs/7', 'head_sha', 'd' * 40),
            ('/actions/runs/7', 'run_attempt', 2),
            ('/actions/runs/7', 'path', '.github/workflows/evil.yml'),
            ('/pulls/42', 'draft', True),
            ('/pulls/42', 'changed_files', 2),
            ('/check-suites/8', 'app', {'slug': 'evil-app'}),
            ('/git/trees/' + HEAD + '?recursive=1', 'truncated', True),
        ]
        for path, key, value in mutations:
            api = FakeAPI()
            api.data[path][key] = value
            with self.subTest(path=path, key=key), self.assertRaises((ValueError, KeyError)):
                self.call(api)
            self.assertEqual(api.writes, [])
        for field, value in [('status', 'in_progress'), ('conclusion', 'failure'),
                             ('conclusion', 'cancelled'), ('conclusion', 'skipped')]:
            api = FakeAPI()
            api.data['/commits/' + HEAD + '/check-runs'][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.call(api)
            self.assertEqual(api.writes, [])

    def test_mixed_paths_symlinks_and_newer_run_rejected(self):
        for mode in ('120000', '100755', '160000'):
            api = FakeAPI()
            api.data['/git/trees/' + HEAD + '?recursive=1']['tree'][0]['mode'] = mode
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.call(api)
            self.assertEqual(api.writes, [])
        api = FakeAPI()
        api.data['/pulls/42/files'][0]['filename'] = '.github/workflows/evil.yml'
        with self.assertRaises(ValueError):
            self.call(api)
        self.assertEqual(api.writes, [])
        api = FakeAPI()
        newer = copy.deepcopy(api.data['/actions/runs/7'])
        newer['id'] = 9
        api.data['/actions/workflows/12/runs?event=pull_request&head_sha=' + HEAD].append(newer)
        with self.assertRaises(ValueError):
            self.call(api)
        self.assertEqual(api.writes, [])

    def test_race_after_approval_never_merges(self):
        api = FakeAPI()
        api.stale_after_review = True
        with self.assertRaises(ValueError):
            self.call(api)
        self.assertEqual(len(api.writes), 1)

    def test_merge_rejection_not_reported_as_success(self):
        api = FakeAPI()
        api.merge_result = {'merged': False, 'message': 'policy rejected'}
        with self.assertRaises(ValueError):
            self.call(api)


if __name__ == '__main__':
    unittest.main()
