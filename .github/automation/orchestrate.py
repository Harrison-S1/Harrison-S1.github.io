"""Trusted default-branch orchestrator. No PR checkout, artifacts, caches or shell.

All network methods are injectable; tests never send review or merge requests.
"""
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import content_policy as policy

WORKFLOW = '.github/workflows/blog-content.yml'
JOB = 'Blog content / validate'
REQUIRED_JOB = 'Trusted base / Jekyll build'


class GitHub:
    def __init__(self, token):
        self.token = token

    def request(self, method, url, data=None):
        req = Request('https://api.github.com' + url, method=method,
                      data=None if data is None else json.dumps(data).encode(),
                      headers={'Authorization': 'Bearer ' + self.token,
                               'Accept': 'application/vnd.github+json',
                               'X-GitHub-Api-Version': '2022-11-28',
                               'Content-Type': 'application/json',
                               'User-Agent': 'checks-only-blog-gate'})
        # Never retry writes: ambiguous network results require human inspection.
        with urlopen(req, timeout=30) as response:
            raw = response.read(8_000_001)
            policy.require(len(raw) <= 8_000_000, 'API response limit')
            return json.loads(raw)

    def get(self, path):
        return self.request('GET', '/repos/' + policy.REPO + path)

    def write(self, method, path, payload):
        return self.request(method, '/repos/' + policy.REPO + path, payload)

    def pages(self, path, key=None):
        result = []
        for page in range(1, 11):
            obj = self.get(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
            rows = obj[key] if key else obj
            policy.require(isinstance(rows, list), 'invalid paginated response')
            result.extend(rows)
            if len(rows) < 100:
                if key and 'total_count' in obj:
                    policy.require(obj['total_count'] == len(result), 'API pagination count mismatch')
                return result
        raise ValueError('API pagination limit')

    def review_state(self, number):
        query = '''query($number:Int!) {
          repository(owner:"Harrison-S1", name:"Harrison-S1.github.io") {
            pullRequest(number:$number) {
              reviewDecision mergeStateStatus headRefOid baseRefOid
              baseRef { branchProtectionRule {
                requiresStrictStatusChecks requiresStatusChecks requiredStatusCheckContexts
              } }
            }
          }
        }'''
        response = self.request('POST', '/graphql', {'query': query, 'variables': {'number': number}})
        policy.require(not response.get('errors'), 'GraphQL policy query failed')
        return response['data']['repository']['pullRequest']


def inspect(api, run_id, attempt, trusted_base):
    run = api.get(f'/actions/runs/{run_id}')
    workflow = api.get('/actions/workflows/blog-content.yml')
    policy.require(workflow['path'] == WORKFLOW and workflow['state'] == 'active', 'wrong/disabled workflow')
    policy.require(run['workflow_id'] == workflow['id'] and run['path'] == WORKFLOW, 'workflow provenance')
    policy.require(run['id'] == run_id and run['run_attempt'] == attempt, 'stale run attempt')
    policy.require(run['event'] == 'pull_request' and run['status'] == 'completed' and
                   run['conclusion'] == 'success', 'unsuccessful/non-PR validation')
    policy.require(run['repository']['full_name'] == policy.REPO and
                   run['head_repository']['full_name'] == policy.REPO, 'foreign run/repository')
    policy.require(len(run['pull_requests']) == 1, 'ambiguous PR association')
    number = run['pull_requests'][0]['number']
    policy.require(type(number) is int and number > 0, 'invalid PR number')
    pr = api.get(f'/pulls/{number}')
    policy.metadata(pr)
    head, base = pr['head']['sha'], pr['base']['sha']
    policy.require(run['head_sha'] == head and run['pull_requests'][0]['head']['sha'] == head and
                   run['pull_requests'][0]['base']['sha'] == base, 'stale head/base association')
    policy.require(api.get('/git/ref/heads/main')['object']['sha'] == base == trusted_base,
                   'main changed; fresh validation required')
    latest = api.pages(f'/actions/workflows/{workflow["id"]}/runs?event=pull_request&head_sha={head}', 'workflow_runs')
    policy.require(latest and max(r['id'] for r in latest) == run_id, 'newer validation run exists')
    jobs = api.pages(f'/actions/runs/{run_id}/jobs', 'jobs')
    policy.require(len(jobs) == 1 and jobs[0]['name'] == JOB and jobs[0]['status'] == 'completed' and
                   jobs[0]['conclusion'] == 'success', 'validation job missing/skipped/failed')
    suite = api.get(f'/check-suites/{run["check_suite_id"]}')
    policy.require(suite['head_sha'] == head and suite['app']['slug'] == 'github-actions', 'check suite provenance')
    files = api.pages(f'/pulls/{number}/files')
    policy.file_policy(files)
    policy.require(len(files) == pr['changed_files'], 'API changed-file mismatch')
    tree = api.get(f'/git/trees/{head}?recursive=1')
    policy.require(tree['truncated'] is False, 'truncated head tree')
    entries = {e['path']: e for e in tree['tree']}
    total = 0
    for item in files:
        entry = entries[item['filename']]
        policy.require(entry['mode'] == '100644' and entry['type'] == 'blob', 'unsafe head file mode')
        size = entry['size']
        limit = policy.MAX_POST if policy.POST.fullmatch(item['filename']) else policy.MAX_IMAGE
        policy.require(0 < size <= limit, 'blob limit')
        total += size
    policy.require(total <= policy.MAX_TOTAL, 'total byte limit')
    checks = api.pages(f'/commits/{head}/check-runs', 'check_runs')
    policy.require(checks and all(c['status'] == 'completed' and c['conclusion'] == 'success' for c in checks),
                   'pending/failed/cancelled/skipped head check')
    policy.require(any(c['name'] == JOB and c['check_suite']['id'] == run['check_suite_id'] and
                       c['app']['slug'] == 'github-actions' for c in checks), 'validation check provenance')
    statuses = api.get(f'/commits/{head}/status')
    policy.require(len(statuses['statuses']) == statuses['total_count'] and
                   all(s['state'] == 'success' for s in statuses['statuses']), 'failed/pending/truncated status contexts')
    return pr


def orchestrate(api, run_id, attempt, trusted_base):
    policy.require(policy.SHA.fullmatch(trusted_base), 'invalid trusted checkout SHA')
    pr = inspect(api, run_id, attempt, trusted_base)
    number, head = pr['number'], pr['head']['sha']
    review = api.write('POST', f'/pulls/{number}/reviews', {
        'commit_id': head, 'event': 'APPROVE',
        'body': 'Checks-only content gate passed for this exact head: content allowlist, metadata, '
                'Markdown/raster/local links and frozen Jekyll build. Not AI review; technical correctness, '
                'editorial quality and external link availability are NOT guaranteed. '
                'This bot approval does not replace required human/CODEOWNER/last-push approval.'})
    policy.require(review['state'] == 'APPROVED' and review['commit_id'] == head, 'approval not confirmed')
    policy.require(type(review['id']) is int and review['id'] > 0, 'invalid review ID')
    observed_review = api.get(f'/pulls/{number}/reviews/{review["id"]}')
    policy.require(observed_review['id'] == review['id'] and observed_review['state'] == 'APPROVED' and
                   observed_review['commit_id'] == head and
                   observed_review['user']['login'] == 'github-actions[bot]', 'review read-back failed')
    # Re-read all metadata, paths, modes, checks, provenance and main AFTER approval.
    fresh = inspect(api, run_id, attempt, trusted_base)
    policy.require(fresh['head']['sha'] == head, 'head changed during approval')
    state = api.review_state(number)
    policy.require(state['headRefOid'] == head and state['baseRefOid'] == trusted_base, 'policy SHA changed')
    # GitHub REST merge has an atomic head guard, but NO atomic expected-base guard.
    # Strict required checks close that race server-side. Missing protection => manual.
    rule = (state.get('baseRef') or {}).get('branchProtectionRule') or {}
    strict = (rule.get('requiresStatusChecks') is True and rule.get('requiresStrictStatusChecks') is True and
              REQUIRED_JOB in rule.get('requiredStatusCheckContexts', []))
    if not (state['reviewDecision'] == 'APPROVED' and state['mergeStateStatus'] == 'CLEAN' and
            fresh.get('mergeable') is True and fresh.get('mergeable_state') == 'clean' and strict):
        return {'result': 'manual-policy-required', 'pr': number, 'head': head,
                'reason': 'GitHub reviews/merge policy or strict required base build not satisfied; no merge attempted.'}
    # Final read immediately before atomic-head guarded normal-policy merge.
    final = api.get(f'/pulls/{number}')
    policy.metadata(final)
    policy.require(final['head']['sha'] == head and final['base']['sha'] == trusted_base and
                   api.get('/git/ref/heads/main')['object']['sha'] == trusted_base, 'last-minute SHA change')
    result = api.write('PUT', f'/pulls/{number}/merge', {'sha': head, 'merge_method': 'squash'})
    policy.require(result.get('merged') is True, 'merge rejected by GitHub policy')
    observed = api.get(f'/pulls/{number}')
    policy.require(observed.get('merged') is True and observed['merge_commit_sha'] == result['sha'],
                   'merge not verified by read-back')
    return {'result': 'merged', 'pr': number, 'head': head, 'merge_commit': result['sha'],
            'publication': 'NOT verified; GITHUB_TOKEN push does not trigger existing deploy workflow.'}


def main():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    policy.require(os.environ['GITHUB_EVENT_NAME'] == 'workflow_run' and
                   event['repository']['full_name'] == policy.REPO, 'unexpected event')
    run = event['workflow_run']
    api = GitHub(os.environ['GH_TOKEN'])
    result = orchestrate(api, run['id'], run['run_attempt'], os.environ['TRUSTED_BASE'])
    print(json.dumps(result, sort_keys=True))
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
        summary.write('Checks-only automation result:\n\n```json\n' + json.dumps(result, indent=2) + '\n```\n')


if __name__ == '__main__':
    main()
