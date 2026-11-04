"""Real HTTP adapter exercised with canned transport responses; no live writes."""
import json
from email.message import Message
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orchestrate import GitHub


class Response:
    def __init__(self, value):
        self.data = json.dumps(value).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.data[:limit]


class AdapterTests(unittest.TestCase):
    def test_no_content_dispatch_response(self):
        response = Response(None)
        response.data = b''
        with patch('orchestrate.urlopen', return_value=response):
            self.assertIsNone(GitHub('test-placeholder').write(
                'POST', '/actions/workflows/pages-deploy.yml/dispatches', {'ref': 'main'}))

    def test_exact_method_url_sha_payload(self):
        with patch('orchestrate.urlopen', return_value=Response({'merged': False})) as transport:
            result = GitHub('test-placeholder').write('PUT', '/pulls/42/merge', {'sha': 'b' * 40, 'merge_method': 'squash'})
        req = transport.call_args.args[0]
        self.assertEqual(req.method, 'PUT')
        self.assertEqual(req.full_url, 'https://api.github.com/repos/Harrison-S1/Harrison-S1.github.io/pulls/42/merge')
        self.assertEqual(json.loads(req.data)['sha'], 'b' * 40)
        self.assertFalse(result['merged'])

    def test_api_errors_are_not_retried_or_swallowed(self):
        for status in (403, 409, 422, 500):
            with self.subTest(status=status):
                error = HTTPError('https://api.github.com', status, 'error', Message(), None)
                with patch('orchestrate.urlopen', side_effect=error) as transport:
                    with self.assertRaises(HTTPError):
                        GitHub('test-placeholder').write('POST', '/pulls/42/reviews', {'event': 'APPROVE'})
                    self.assertEqual(transport.call_count, 1)
                error.close()

    def test_pagination_complete_and_truncated(self):
        api = GitHub('test-placeholder')
        with patch.object(api, 'get', side_effect=[{'total_count': 101, 'jobs': [{}] * 100},
                                                  {'total_count': 101, 'jobs': [{}]}]):
            self.assertEqual(len(api.pages('/jobs', 'jobs')), 101)
        with patch.object(api, 'get', return_value={'total_count': 2, 'jobs': [{}]}):
            with self.assertRaises(ValueError):
                api.pages('/jobs', 'jobs')

    def test_graphql_errors_fail_closed(self):
        api = GitHub('test-placeholder')
        with patch.object(api, 'request', return_value={'errors': [{'message': 'not authorized'}]}):
            with self.assertRaises(ValueError):
                api.review_state(42)


if __name__ == '__main__':
    unittest.main()
