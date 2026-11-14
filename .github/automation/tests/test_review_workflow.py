"""Fail-closed workflow credential and activation contract; source-only checks."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[3]


class ReviewWorkflowTests(unittest.TestCase):
    def test_fixed_app_scoped_mint_split_tokens_and_existing_activation_gates(self):
        doc = yaml.safe_load((ROOT / '.github/workflows/blog-content-decision.yml').read_text())
        self.assertEqual(doc['permissions'], {})
        job = doc['jobs']['decide']
        gate = job['if']
        for expected in ("github.repository == 'Harrison-S1/Harrison-S1.github.io'",
                         "vars.BLOG_CONTENT_AUTOMERGE == 'enabled'",
                         "vars.BLOG_CONTENT_DEPLOYMENT_READY == 'acknowledged'",
                         "github.event.workflow_run.conclusion == 'success'"):
            self.assertIn(expected, gate)
        steps = job['steps']
        mint = next(s for s in steps if s.get('id') == 'review-token')
        self.assertEqual(mint['uses'], 'actions/create-github-app-token@fee1f7d63c2ff003460e3d139729b119787bc349')
        self.assertEqual(mint['with'], {'app-id': '5645498',
                         'private-key': '${{ secrets.BLOG_REVIEW_APP_PRIVATE_KEY }}',
                         'owner': 'Harrison-S1', 'repositories': 'Harrison-S1.github.io',
                         'permission-pull-requests': 'write', 'permission-metadata': 'read'})
        run = next(s for s in steps if s.get('run') == 'python .github/automation/orchestrate.py')
        self.assertEqual(run['env']['GH_TOKEN'], '${{ secrets.GITHUB_TOKEN }}')
        self.assertEqual(run['env']['GH_REVIEW_TOKEN'], '${{ steps.review-token.outputs.token }}')
        self.assertEqual(run['env']['REVIEW_INSTALLATION_ID'], '${{ steps.review-token.outputs.installation-id }}')
        self.assertEqual(run['env']['REVIEW_APP_SLUG'], '${{ steps.review-token.outputs.app-slug }}')
        checkout = steps[0]
        self.assertEqual(checkout['with']['ref'], '${{ github.sha }}')
        self.assertIs(checkout['with']['persist-credentials'], False)
        self.assertEqual(job['permissions'], {'contents': 'write', 'pull-requests': 'write',
                         'actions': 'write', 'checks': 'read', 'statuses': 'read'})


if __name__ == '__main__':
    unittest.main()
