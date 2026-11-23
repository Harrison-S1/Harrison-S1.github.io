"""Exercise actual HTTP adapter routing using canned responses, no network."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrate import GitHub, ReviewGitHub


class ReviewHTTPTests(unittest.TestCase):
    def test_separate_authorization_headers_and_repository_endpoints(self):
        observed = []
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, limit):
                return b'{}'
        def transport(request, timeout):
            observed.append((request.full_url, request.method, request.get_header('Authorization')))
            return Response()
        with patch('orchestrate.urlopen', side_effect=transport):
            GitHub('fixture-normal').get('/pulls/42')
            ReviewGitHub('fixture-review').get('')
            ReviewGitHub('fixture-review').request('GET', '/installation/repositories?per_page=100')
            ReviewGitHub('fixture-review').write('POST', '/pulls/42/reviews', {'commit_id': 'b' * 40})
            ReviewGitHub('fixture-review').get('/pulls/42/reviews/99')
        self.assertEqual(len(observed), 5)
        self.assertEqual(observed[0][2], 'Bearer fixture-normal')
        self.assertTrue(all(row[2] == 'Bearer fixture-review' for row in observed[1:]))
        self.assertEqual(observed[3][:2], ('https://api.github.com/repos/Harrison-S1/Harrison-S1.github.io/pulls/42/reviews', 'POST'))


if __name__ == '__main__':
    unittest.main()
