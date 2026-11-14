"""Offline independent App review contract, never live approval evidence."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_orchestrate import FakeAPI, HEAD, BASE

BOT = {'id': 353438493, 'login': 'harrison-s1-blog-reviewer[bot]', 'type': 'Bot'}
REPO = {'id': 504555593, 'full_name': 'Harrison-S1/Harrison-S1.github.io',
        'owner': {'id': 54186142, 'login': 'Harrison-S1'}}


class ReviewAPI:
    def __init__(self):
        self.repository = copy.deepcopy(REPO)
        self.review = {'id': 99, 'state': 'APPROVED', 'commit_id': HEAD, 'user': copy.deepcopy(BOT)}
        self.writes = []
        self.scope = {'total_count': 1, 'repositories': [self.repository]}

    def request(self, method, path, data=None):
        assert method == 'GET' and path == '/installation/repositories?per_page=100'
        return copy.deepcopy(self.scope)

    def get(self, path):
        if path == '':
            return copy.deepcopy(self.repository)
        assert path == '/pulls/42/reviews/99'
        return copy.deepcopy(self.review)

    def write(self, method, path, payload):
        assert method == 'POST' and path == '/pulls/42/reviews'
        self.writes.append((path, payload))
        return copy.deepcopy(self.review)


class IndependentReviewTests(unittest.TestCase):
    def call(self, normal, review):
        from orchestrate import orchestrate
        return orchestrate(normal, 7, 1, BASE, sleep=lambda _: None, review_api=review)

    def test_only_independent_api_submits_review_normal_api_merges_and_dispatches(self):
        normal, review = FakeAPI(), ReviewAPI()
        self.assertEqual(self.call(normal, review)['result'], 'merged')
        self.assertEqual(review.writes, [('/pulls/42/reviews', review.writes[0][1])])
        self.assertEqual(review.writes[0][1]['commit_id'], HEAD)
        self.assertEqual([w[0] for w in normal.writes], ['/pulls/42/merge', '/actions/workflows/pages-deploy.yml/dispatches'])

    def test_missing_or_shared_review_api_never_writes(self):
        for review in (None,):
            normal = FakeAPI()
            with self.assertRaises(ValueError):
                self.call(normal, review)
            self.assertEqual(normal.writes, [])
        normal = FakeAPI()
        with self.assertRaises(ValueError):
            self.call(normal, normal)
        self.assertEqual(normal.writes, [])

    def test_wrong_numeric_or_named_repository_rejected_before_review(self):
        for key, value in [('id', 1), ('id', '504555593'), ('full_name', 'other/repository'),
                           ('owner', {'id': 1, 'login': 'Harrison-S1'})]:
            normal, review = FakeAPI(), ReviewAPI()
            review.repository[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.call(normal, review)
            self.assertEqual(normal.writes + review.writes, [])
        for scope in ({'total_count': 2, 'repositories': [REPO, REPO]},
                      {'total_count': 1, 'repositories': [dict(REPO, id=1)]}):
            normal, review = FakeAPI(), ReviewAPI()
            review.scope = scope
            with self.assertRaises(ValueError):
                self.call(normal, review)
            self.assertEqual(normal.writes + review.writes, [])

    def test_wrong_bot_type_numeric_id_login_state_head_or_review_id_rejected(self):
        for key, value in [('id', 41898282), ('id', '353438493'), ('id', True),
                           ('login', 'github-actions[bot]'), ('login', 'spoof[bot]'), ('type', 'User')]:
            normal, review = FakeAPI(), ReviewAPI()
            review.review['user'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.call(normal, review)
            self.assertEqual(normal.writes, [])
        for key, value in [('commit_id', BASE), ('state', 'DISMISSED'), ('id', True), ('id', 0)]:
            normal, review = FakeAPI(), ReviewAPI()
            review.review[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.call(normal, review)
            self.assertEqual(normal.writes, [])

    def test_readback_must_match_exact_review_id_author_and_head(self):
        for key, value in [('id', 100), ('commit_id', BASE), ('user', dict(BOT, id=1))]:
            class BadReadback(ReviewAPI):
                def get(self, path):
                    value_read = super().get(path)
                    if path.endswith('/reviews/99'):
                        value_read[key] = value
                    return value_read
            normal, review = FakeAPI(), BadReadback()
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.call(normal, review)
            self.assertEqual(normal.writes, [])

    def test_normal_policy_still_blocks_merge(self):
        normal, review = FakeAPI(), ReviewAPI()
        normal.approved = False
        self.assertEqual(self.call(normal, review)['result'], 'manual-policy-required')
        self.assertEqual(normal.writes, [])
        self.assertEqual(len(review.writes), 1)

    def test_review_transport_rejects_merge_deploy_and_foreign_urls_before_network(self):
        from orchestrate import ReviewGitHub
        api = ReviewGitHub('fixture-not-a-credential')
        for method, path in [('PUT', '/repos/Harrison-S1/Harrison-S1.github.io/pulls/42/merge'),
                             ('POST', '/repos/Harrison-S1/Harrison-S1.github.io/actions/workflows/pages-deploy.yml/dispatches'),
                             ('POST', '/repos/other/repository/pulls/42/reviews')]:
            with self.subTest(path=path), self.assertRaises(ValueError):
                api.request(method, path, {})

    def test_mint_context_requires_pinned_installation_slug_and_distinct_tokens(self):
        from orchestrate import review_api_from_environment
        from unittest.mock import patch
        env = {'GH_TOKEN': 'fixture-normal', 'GH_REVIEW_TOKEN': 'fixture-review',
               'REVIEW_INSTALLATION_ID': '179326232', 'REVIEW_APP_SLUG': 'harrison-s1-blog-reviewer'}
        with patch.dict('os.environ', env, clear=True):
            self.assertEqual(review_api_from_environment().token, 'fixture-review')
        for key, value in [('REVIEW_INSTALLATION_ID', '1'), ('REVIEW_APP_SLUG', 'github-actions'),
                           ('GH_REVIEW_TOKEN', ''), ('GH_REVIEW_TOKEN', 'fixture-normal')]:
            with patch.dict('os.environ', dict(env, **{key: value}), clear=True):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    review_api_from_environment()

    def test_live_evidence_accepts_only_numeric_app_review_and_repository(self):
        from live_evidence import verify_evidence
        evidence = {'pr': {'merged': True, 'merge_commit_sha': 'c' * 40,
                          'head': {'sha': HEAD}, 'base': {'repo': copy.deepcopy(REPO)}},
                    'reviews': [copy.deepcopy(ReviewAPI().review)],
                    'runs': [{'path': '.github/workflows/pages-deploy.yml', 'event': 'workflow_dispatch',
                              'head_sha': 'c' * 40, 'status': 'completed', 'conclusion': 'success'}],
                    'marker': {'sha': 'c' * 40}, 'page_status': 200, 'page_text_found': True,
                    'assets': [{'status': 200, 'sha256': '1' * 64, 'source_sha256': '1' * 64}]}
        verify_evidence(evidence, 'c' * 40)
        for key, value in [('id', 1), ('login', 'github-actions[bot]'), ('type', 'User')]:
            bad = copy.deepcopy(evidence)
            bad['reviews'][0]['user'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_evidence(bad, 'c' * 40)
        bad = copy.deepcopy(evidence)
        bad['pr']['base']['repo']['id'] = 1
        with self.assertRaises(ValueError):
            verify_evidence(bad, 'c' * 40)


if __name__ == '__main__':
    unittest.main()
