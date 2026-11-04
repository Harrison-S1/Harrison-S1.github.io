"""LOCAL FIXTURES ONLY: never approval/merge/deployment proof on GitHub."""
import copy
import unittest
from test_orchestrate import FakeAPI, BASE, HEAD
from test_policy import PATH
import content_policy as policy
from orchestrate import inspect, orchestrate

REQUIRED = ['Site / frozen build', 'Automation / offline adversarial tests']


class CompleteAPI(FakeAPI):
    def __init__(self):
        super().__init__()
        run = self.data['/actions/runs/7']
        run['check_suite_id'] = 8
        jobs = self.data['/actions/runs/7/jobs']
        jobs[0].update(id=71, run_id=7, run_attempt=1, head_sha=HEAD,
                       check_run_url='https://api.github.com/repos/' + policy.REPO + '/check-runs/81')
        suite = self.data['/check-suites/8']
        suite.update(id=8, app={'id': 15368, 'slug': 'github-actions'})
        checks = self.data['/commits/' + HEAD + '/check-runs']
        checks[:] = checks[:1]
        checks[0].update(id=81, head_sha=HEAD, app={'id': 15368, 'slug': 'github-actions'})
        build = copy.deepcopy(run)
        build.update(id=9, workflow_id=13, path='.github/workflows/blog-automation-tests.yml', check_suite_id=10)
        self.data['/actions/workflows/blog-automation-tests.yml'] = {
            'id': 13, 'path': build['path'], 'state': 'active'}
        self.data['/actions/workflows/13/runs?event=pull_request&head_sha=' + HEAD] = [build]
        self.data['/actions/runs/9'] = build
        self.data['/check-suites/10'] = {'id': 10, 'head_sha': HEAD,
                                       'app': {'id': 15368, 'slug': 'github-actions'}}
        self.data['/actions/runs/9/jobs'] = []
        for index, name in enumerate(REQUIRED, 82):
            checks.append({'id': index, 'name': name, 'head_sha': HEAD, 'status': 'completed',
                           'conclusion': 'success', 'app': {'id': 15368, 'slug': 'github-actions'},
                           'check_suite': {'id': 10}})
            self.data['/actions/runs/9/jobs'].append({
                'id': index + 100, 'run_id': 9, 'run_attempt': 1, 'head_sha': HEAD, 'name': name,
                'status': 'completed', 'conclusion': 'success',
                'check_run_url': 'https://api.github.com/repos/' + policy.REPO + '/check-runs/' + str(index)})

    def review_state(self, number):
        state = super().review_state(number)
        rule = state['baseRef']['branchProtectionRule']
        rule['requiredStatusCheckContexts'] = REQUIRED[:]
        rule['requiredStatusChecks'] = [{'context': name, 'app': {'databaseId': 15368}} for name in REQUIRED]
        return state


class EligibilityTests(unittest.TestCase):
    def test_complete_verified_fixture_merges_with_atomic_head(self):
        api = CompleteAPI()
        self.assertEqual(orchestrate(api, 7, 1, BASE)['result'], 'merged')
        self.assertEqual(api.writes[1][1], {'sha': HEAD, 'merge_method': 'squash'})

    def test_missing_required_success_never_approves(self):
        api = CompleteAPI()
        api.data['/commits/' + HEAD + '/check-runs'].pop()
        with self.assertRaises(ValueError):
            orchestrate(api, 7, 1, BASE)
        self.assertEqual(api.writes, [])

    def test_provenance_and_run_association(self):
        mutations = [
            ('/check-suites/8', 'app', {'id': 1, 'slug': 'github-actions'}),
            ('/actions/runs/9', 'head_sha', 'd' * 40),
            ('/actions/runs/9', 'path', '.github/workflows/impostor.yml'),
            ('/actions/runs/9', 'event', 'push'),
            ('/actions/runs/9', 'conclusion', 'failure'),
        ]
        for path, key, value in mutations:
            with self.subTest(path=path, key=key):
                api = CompleteAPI()
                api.data[path][key] = value
                with self.assertRaises(ValueError):
                    orchestrate(api, 7, 1, BASE)
                self.assertEqual(api.writes, [])
        for key, value in [('head_sha', 'd' * 40), ('app', {'id': 1, 'slug': 'github-actions'}),
                           ('id', 999), ('check_suite', {'id': 999})]:
            with self.subTest(check_key=key):
                api = CompleteAPI()
                api.data['/commits/' + HEAD + '/check-runs'][1][key] = value
                with self.assertRaises(ValueError):
                    inspect(api, 7, 1, BASE)

    def test_job_must_belong_to_exact_run_attempt(self):
        api = CompleteAPI()
        api.data['/actions/runs/9/jobs'][0]['run_attempt'] = 2
        with self.assertRaises(ValueError):
            inspect(api, 7, 1, BASE)

    def test_duplicate_named_check_is_ambiguous(self):
        api = CompleteAPI()
        checks = api.data['/commits/' + HEAD + '/check-runs']
        checks.append(copy.deepcopy(checks[1]))
        with self.assertRaises(ValueError):
            inspect(api, 7, 1, BASE)

    def test_missing_second_required_policy_check(self):
        class Missing(CompleteAPI):
            def review_state(self, number):
                state = super().review_state(number)
                state['baseRef']['branchProtectionRule']['requiredStatusChecks'].pop()
                return state
        with self.assertRaises(ValueError):
            inspect(Missing(), 7, 1, BASE)

    def test_base_and_policy_races_after_review_never_merge(self):
        for attack in ('base', 'protection', 'api'):
            class Race(CompleteAPI):
                def review_state(self, number):
                    state = super().review_state(number)
                    if self.writes and attack == 'protection':
                        state['baseRef']['branchProtectionRule']['requireLastPushApproval'] = False
                    return state
                def get(self, path):
                    if self.writes and path == '/git/ref/heads/main':
                        if attack == 'api':
                            raise OSError('local fixture API outage')
                        if attack == 'base':
                            return {'object': {'sha': 'd' * 40}}
                    return super().get(path)
            api = Race()
            with self.subTest(attack=attack), self.assertRaises((ValueError, OSError)):
                orchestrate(api, 7, 1, BASE)
            self.assertEqual(len(api.writes), 1)

    def test_review_count_reduction_is_policy_drift(self):
        class Race(CompleteAPI):
            def review_state(self, number):
                state = super().review_state(number)
                state['baseRef']['branchProtectionRule']['requiredApprovingReviewCount'] = 1 if self.writes else 2
                return state
        api = Race()
        with self.assertRaises(ValueError):
            orchestrate(api, 7, 1, BASE)
        self.assertEqual(len(api.writes), 1)

    def test_exact_head_timestamp_is_validated_and_read_as_data(self):
        from unittest.mock import patch
        from validate_content import commit_timestamp
        with patch('validate_content.git', return_value=b'1793797010\n') as read:
            self.assertEqual(commit_timestamp(HEAD), 1793797010)
            read.assert_called_once_with('show', '-s', '--format=%ct', HEAD)
        for value in (b'0\n', b'-1\n', b'nope\n', b'1\n2\n'):
            with patch('validate_content.git', return_value=value), self.assertRaises(ValueError):
                commit_timestamp(HEAD)

    def test_infrastructure_disguised_as_examples_is_manual(self):
        for suffix, data in [('json', b'{"Resources":{"Role":{"Type":"AWS::IAM::Role"}}}'),
                             ('json', b'{"dependencies":{"evil":"latest"}}'),
                             ('json', b'{"token":"secret fixture"}'),
                             ('j2', b'apiVersion: v1\nkind: Secret'),
                             ('txt', b'export AWS_SECRET_ACCESS_KEY=fixture')]:
            path = 'examples/posts/a-useful-example/data.' + suffix
            with self.subTest(suffix=suffix, data=data), self.assertRaises(ValueError):
                policy.file_policy([{'filename': PATH, 'status': 'added'}, {'filename': path, 'status': 'added'}])
                policy.example(path, data)

    def test_existing_pr2_remains_explicitly_manual(self):
        pull = __import__('test_policy').pr()
        pull['number'] = 2
        with self.assertRaisesRegex(ValueError, 'manual'):
            policy.metadata(pull)

    def test_numeric_json_and_bounded_arithmetic_examples(self):
        self.assertEqual(policy.example('examples/posts/a-useful-example/data.json', b'[1, 2, true]'), {'assertions': 0})
        self.assertEqual(policy.example('examples/posts/a-useful-example/test.py', b'x = 3 * 4\nassert x == 12'), {'assertions': 1})


if __name__ == '__main__':
    unittest.main()
