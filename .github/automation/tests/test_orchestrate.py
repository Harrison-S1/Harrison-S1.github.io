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
        '/branches/main/protection': {
            'required_pull_request_reviews': {'required_approving_review_count': 1,
                'dismiss_stale_reviews': True, 'require_code_owner_reviews': True, 'require_last_push_approval': True},
            'required_status_checks': {'strict': True, 'checks': [{'context': 'Site / frozen build', 'app_id': 15368}]},
            'allow_force_pushes': {'enabled': False}, 'allow_deletions': {'enabled': False}},
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
        self.protection = self.data['/branches/main/protection']

    def get(self, path):
        if path == '/actions/workflows/pages-deploy.yml':
            return {'id': 77, 'path': '.github/workflows/pages-deploy.yml', 'state': 'active'}
        if path.startswith('/actions/workflows/77/runs'):
            if not any(w[0].endswith('/dispatches') for w in self.writes):
                return []
            return [{'id': 100, 'workflow_id': 77, 'head_sha': 'c' * 40,
                     'path': '.github/workflows/pages-deploy.yml', 'event': 'workflow_dispatch',
                     'display_title': 'Publish ' + 'c' * 40, 'html_url': 'https://example.com/run/100'}]
        if path == '/git/ref/heads/main' and any(w[0].endswith('/merge') for w in self.writes):
            return {'object': {'sha': 'c' * 40}}
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
                    'requiresApprovingReviews': True,
                    'requiredApprovingReviewCount': self.protection['required_pull_request_reviews']['required_approving_review_count'],
                    'dismissesStaleReviews': self.protection['required_pull_request_reviews']['dismiss_stale_reviews'],
                    'requiresCodeOwnerReviews': self.protection['required_pull_request_reviews']['require_code_owner_reviews'],
                    'requireLastPushApproval': self.protection['required_pull_request_reviews']['require_last_push_approval'],
                    'allowsForcePushes': False, 'allowsDeletions': False,
                    'requiredStatusChecks': [{'context': 'Site / frozen build',
                        'app': {'databaseId': self.protection['required_status_checks']['checks'][0]['app_id']}}],
                    'requiresStrictStatusChecks': self.strict, 'requiresStatusChecks': self.strict,
                    'requiredStatusCheckContexts': ['Site / frozen build']}}}


class OrchestrationTests(unittest.TestCase):
    def test_wait_for_other_checks_before_decision(self):
        from orchestrate import await_checks
        class Pending(FakeAPI):
            def __init__(self):
                super().__init__()
                self.calls = 0
            def pages(self, path, key=None):
                if path.endswith('/check-runs'):
                    self.calls += 1
                    return [{'status': 'in_progress' if self.calls < 3 else 'completed', 'conclusion': 'success'}]
                return super().pages(path, key)
        api = Pending()
        pauses = []
        await_checks(api, HEAD, sleep=pauses.append)
        self.assertEqual(api.calls, 3)
        self.assertEqual(pauses, [5, 5])
        self.assertEqual(api.writes, [])

    def test_privilege_policy_changes_never_approve(self):
        for key, value in [('dismiss_stale_reviews', False), ('require_code_owner_reviews', False),
                           ('require_last_push_approval', False), ('required_approving_review_count', 0)]:
            api = FakeAPI()
            api.data['/branches/main/protection']['required_pull_request_reviews'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.call(api)
            self.assertEqual(api.writes, [])
        api = FakeAPI()
        api.data['/branches/main/protection']['required_status_checks']['checks'][0]['app_id'] = 1
        with self.assertRaises(ValueError):
            self.call(api)
        self.assertEqual(api.writes, [])

    def call(self, api):
        from orchestrate import orchestrate
        return orchestrate(api, 7, 1, BASE, sleep=lambda _: None)

    def test_positive_exact_sha_and_policy_merge(self):
        api = FakeAPI()
        self.assertEqual(self.call(api)['result'], 'merged')
        self.assertEqual(api.writes[0][1]['commit_id'], HEAD)
        self.assertEqual(api.writes[1][1], {'sha': HEAD, 'merge_method': 'squash'})

    def test_verified_merge_dispatches_pinned_pages_handoff(self):
        api = FakeAPI()
        result = self.call(api)
        self.assertEqual(result['pages']['run_id'], 100)
        self.assertEqual(api.writes[2][1], {'ref': 'main', 'inputs': {'expected_sha': 'c' * 40}})

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
