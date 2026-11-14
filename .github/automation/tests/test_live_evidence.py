"""Public evidence verification; fixture data is explicitly NOT live proof."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class LiveEvidenceTests(unittest.TestCase):
    def test_success_requires_merged_review_dispatch_marker_and_public_bytes(self):
        from live_evidence import verify_evidence
        sha, head = 'c' * 40, 'b' * 40
        evidence = {
            'pr': {'merged': True, 'merge_commit_sha': sha, 'head': {'sha': head},
                   'base': {'repo': {'id': 504555593, 'full_name': 'Harrison-S1/Harrison-S1.github.io',
                                     'owner': {'id': 54186142, 'login': 'Harrison-S1'}}}},
            'reviews': [{'id': 99, 'state': 'APPROVED', 'commit_id': head,
                         'user': {'id': 353438493, 'login': 'harrison-s1-blog-reviewer[bot]', 'type': 'Bot'}}],
            'runs': [{'path': '.github/workflows/pages-deploy.yml', 'event': 'workflow_dispatch',
                      'head_sha': sha, 'conclusion': 'success', 'status': 'completed'}],
            'marker': {'sha': sha}, 'page_status': 200, 'page_text_found': True,
            'assets': [{'status': 200, 'sha256': '1' * 64, 'source_sha256': '1' * 64}],
        }
        verify_evidence(evidence, sha)
        import copy
        for key, value in [('marker', {'sha': head}), ('runs', []), ('reviews', []),
                           ('page_status', 404), ('assets', []), ('page_text_found', False)]:
            bad = copy.deepcopy(evidence)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_evidence(bad, sha)


if __name__ == '__main__':
    unittest.main()
