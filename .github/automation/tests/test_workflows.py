"""Workflow trust-boundary regression checks; actionlint supplies Actions schema validation."""
from pathlib import Path
import re
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[2] / 'workflows'


class WorkflowTests(unittest.TestCase):
    def load(self, name):
        return yaml.load((ROOT / name).read_text(), Loader=yaml.BaseLoader)

    def test_pins_timeouts_permissions_and_no_injected_shell(self):
        for file in ('blog-content.yml', 'blog-content-decision.yml', 'blog-automation-tests.yml', 'pages-deploy.yml'):
            workflow = self.load(file)
            self.assertIn('permissions', workflow)
            self.assertIn('concurrency', workflow)
            for job in workflow['jobs'].values():
                self.assertIn('timeout-minutes', job)
                self.assertEqual(job['runs-on'], 'ubuntu-24.04')
                for step in job['steps']:
                    if 'uses' in step:
                        self.assertRegex(step['uses'], r'^[\w-]+/[\w-]+@[0-9a-f]{40}$')
                        self.assertNotIn('cache@', step['uses'])
                        if file != 'pages-deploy.yml':
                            self.assertNotIn('artifact@', step['uses'])
                    self.assertNotIn('${{', step.get('run', ''))
                    if step.get('uses', '').startswith('actions/checkout@'):
                        self.assertEqual(step['with']['persist-credentials'], 'false')

    def test_no_privilege_in_pr_workflows(self):
        for file in ('blog-content.yml', 'blog-automation-tests.yml'):
            workflow = self.load(file)
            self.assertIn('pull_request', workflow['on'])
            self.assertNotIn('pull_request_target', workflow['on'])
            self.assertEqual(workflow['permissions'], {'contents': 'read'})
            self.assertNotIn('secrets.', (ROOT / file).read_text())
        content = self.load('blog-content.yml')
        checkout = content['jobs']['validate']['steps'][0]
        self.assertEqual(checkout['with']['ref'], '${{ github.event.pull_request.base.sha }}')

    def test_privileged_path_is_off_and_default_branch_only(self):
        workflow = self.load('blog-content-decision.yml')
        self.assertIn('workflow_run', workflow['on'])
        self.assertEqual(workflow['on']['workflow_run']['types'], ['completed'])
        job = workflow['jobs']['decide']
        self.assertIn("vars.BLOG_CONTENT_AUTOMERGE == 'enabled'", job['if'])
        self.assertIn("vars.BLOG_CONTENT_DEPLOYMENT_READY == 'acknowledged'", job['if'])
        self.assertEqual(job['steps'][0]['with']['ref'], '${{ github.sha }}')
        for step in job['steps']:
            self.assertNotIn('pip install', step.get('run', ''))
        self.assertEqual(job['permissions'], {'contents': 'write', 'pull-requests': 'write',
                                            'actions': 'write', 'checks': 'read', 'statuses': 'read'})

    def test_modern_always_present_required_build_and_pages(self):
        tests = self.load('blog-automation-tests.yml')
        self.assertNotIn('paths', tests['on']['pull_request'])
        self.assertTrue(any(j['name'] == 'Site / frozen build' for j in tests['jobs'].values()))
        content = (ROOT / 'blog-content.yml').read_text()
        self.assertIn('validate_content.py render', content)
        self.assertIn('examples/posts/**', content)
        for file in ('blog-content.yml', 'blog-automation-tests.yml', 'pages-deploy.yml'):
            text = (ROOT / file).read_text()
            self.assertIn("ruby-version: '3.4.12'", text)
            self.assertIn("bundler: '2.6.9'", text)
        pages = self.load('pages-deploy.yml')
        self.assertIn('expected_sha', pages['on']['workflow_dispatch']['inputs'])
        self.assertEqual(pages['permissions'], {})
        self.assertEqual(pages['jobs']['build']['permissions'], {'contents': 'read'})
        self.assertEqual(pages['jobs']['deploy']['needs'], 'build')
        self.assertEqual(pages['jobs']['deploy']['permissions'],
                         {'contents': 'read', 'pages': 'write', 'id-token': 'write'})
        self.assertIn('pages_guard.py', str(pages['jobs']['build']['steps']))
        self.assertIn('pages_guard.py', str(pages['jobs']['deploy']['steps']))


if __name__ == '__main__':
    unittest.main()
