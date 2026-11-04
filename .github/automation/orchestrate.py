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
REQUIRED_JOB = 'Site / frozen build'
REQUIRED_JOBS = (REQUIRED_JOB, 'Automation / offline adversarial tests')
BUILD_WORKFLOW = '.github/workflows/blog-automation-tests.yml'
ACTIONS_APP = 15368


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
            return json.loads(raw) if raw else None

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
                requiresApprovingReviews requiredApprovingReviewCount dismissesStaleReviews
                requiresCodeOwnerReviews requireLastPushApproval allowsForcePushes allowsDeletions
                requiredStatusChecks { context app { databaseId } }
              } }
            }
          }
        }'''
        response = self.request('POST', '/graphql', {'query': query, 'variables': {'number': number}})
        policy.require(not response.get('errors'), 'GraphQL policy query failed')
        return response['data']['repository']['pullRequest']


def verify_run_checks(api, run, workflow_path, names, pr, checks):
    """Bind each unique successful head check to a current workflow attempt/job.

    A matching label or Actions slug alone is not a provenance assertion. No
    check artifact/output or contributor-supplied URL is consumed or executed.
    """
    head, base = pr['head']['sha'], pr['base']['sha']
    policy.require(run['path'] == workflow_path and run['event'] == 'pull_request' and
                   run['head_sha'] == head and run['status'] == 'completed' and
                   run['conclusion'] == 'success', 'required workflow unsuccessful/stale')
    policy.require(run['repository']['full_name'] == policy.REPO and
                   run['head_repository']['full_name'] == policy.REPO, 'foreign required workflow')
    associations = run['pull_requests']
    policy.require(len(associations) == 1 and associations[0]['number'] == pr['number'] and
                   associations[0]['head']['sha'] == head and associations[0]['base']['sha'] == base,
                   'required workflow PR/head/base association changed')
    suite = api.get(f'/check-suites/{run["check_suite_id"]}')
    policy.require(suite['id'] == run['check_suite_id'] and suite['head_sha'] == head and
                   suite['app']['id'] == ACTIONS_APP and suite['app']['slug'] == 'github-actions',
                   'numeric check suite provenance')
    jobs = api.pages(f'/actions/runs/{run["id"]}/jobs', 'jobs')
    policy.require(len(jobs) == len(names), 'unexpected required workflow jobs')
    for name in names:
        named = [c for c in checks if c['name'] == name]
        matching_jobs = [j for j in jobs if j['name'] == name]
        policy.require(len(named) == len(matching_jobs) == 1, 'missing/ambiguous required check/job: ' + name)
        check, job = named[0], matching_jobs[0]
        policy.require(check['head_sha'] == head and check['status'] == 'completed' and
                       check['conclusion'] == 'success' and check['app']['id'] == ACTIONS_APP and
                       check['app']['slug'] == 'github-actions' and
                       check['check_suite']['id'] == run['check_suite_id'], 'required check provenance: ' + name)
        expected_url = 'https://api.github.com/repos/' + policy.REPO + '/check-runs/' + str(check['id'])
        policy.require(job['run_id'] == run['id'] and job['run_attempt'] == run['run_attempt'] and
                       job['head_sha'] == head and
                       job['status'] == 'completed' and job['conclusion'] == 'success' and
                       job['check_run_url'] == expected_url, 'required job/check association: ' + name)


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
    policy.require(suite['head_sha'] == head and suite['app']['slug'] == 'github-actions' and
                   suite['app']['id'] == ACTIONS_APP, 'check suite provenance')
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
        limit = policy.MAX_POST if policy.POST.fullmatch(item['filename']) else (
            policy.MAX_EXAMPLE if policy.EXAMPLE.fullmatch(item['filename']) else policy.MAX_IMAGE)
        policy.require(0 < size <= limit, 'blob limit')
        total += size
    policy.require(total <= policy.MAX_TOTAL, 'total byte limit')
    checks = api.pages(f'/commits/{head}/check-runs', 'check_runs')
    policy.require(checks and all(c['status'] == 'completed' and c['conclusion'] == 'success' for c in checks),
                   'pending/failed/cancelled/skipped head check')
    verify_run_checks(api, run, WORKFLOW, (JOB,), pr, checks)
    build_workflow = api.get('/actions/workflows/blog-automation-tests.yml')
    policy.require(build_workflow['path'] == BUILD_WORKFLOW and build_workflow['state'] == 'active',
                   'required build workflow changed/disabled')
    builds = api.pages(f'/actions/workflows/{build_workflow["id"]}/runs?event=pull_request&head_sha={head}',
                      'workflow_runs')
    policy.require(builds, 'required workflow run missing')
    latest_build_id = max(r['id'] for r in builds)
    build = api.get(f'/actions/runs/{latest_build_id}')
    policy.require(build['id'] == latest_build_id and build['workflow_id'] == build_workflow['id'],
                   'required workflow identity')
    verify_run_checks(api, build, BUILD_WORKFLOW, REQUIRED_JOBS, pr, checks)
    statuses = api.get(f'/commits/{head}/status')
    policy.require(len(statuses['statuses']) == statuses['total_count'] and
                   all(s['state'] == 'success' for s in statuses['statuses']), 'failed/pending/truncated status contexts')
    state = api.review_state(number)
    verify_protection(state)
    policy.require(state['headRefOid'] == head and state['baseRefOid'] == base, 'inspection policy SHA changed')
    pr['_gate_protection'] = state['baseRef']['branchProtectionRule']
    return pr


def verify_protection(state):
    """Run on every full inspection, including after approval; no admin REST scope."""
    protection = (state.get('baseRef') or {}).get('branchProtectionRule') or {}
    policy.require(protection.get('requiresApprovingReviews') is True and
                   protection.get('requiredApprovingReviewCount', 0) >= 1 and
                   all(protection.get(k) is True for k in
                       ('dismissesStaleReviews', 'requiresCodeOwnerReviews', 'requireLastPushApproval')) and
                   protection.get('allowsForcePushes') is False and protection.get('allowsDeletions') is False,
                   'review/security protection changed; manual intervention required')
    policy.require(protection.get('requiresStatusChecks') is True and
                   protection.get('requiresStrictStatusChecks') is True and
                   all(name in protection.get('requiredStatusCheckContexts', []) for name in REQUIRED_JOBS),
                   'strict required checks missing; no automated approval')
    for name in REQUIRED_JOBS:
        matches = [c for c in protection.get('requiredStatusChecks', []) if c['context'] == name]
        policy.require(len(matches) == 1 and (matches[0].get('app') or {}).get('databaseId') == ACTIONS_APP,
                       'required check source not GitHub Actions: ' + name)


def await_checks(api, head, sleep=None):
    """Content validation may finish before CodeQL/build. Bounded wait, fail closed."""
    import time
    sleep = sleep or time.sleep
    policy.require(policy.SHA.fullmatch(head), 'invalid check head')
    for _ in range(48):
        checks = api.pages(f'/commits/{head}/check-runs', 'check_runs')
        statuses = api.get(f'/commits/{head}/status')
        policy.require(checks and all(c['conclusion'] == 'success' for c in checks if c['status'] == 'completed'),
                       'missing/failed completed check')
        policy.require(all(s['state'] in ('success', 'pending') for s in statuses['statuses']), 'failed status context')
        if all(c['status'] == 'completed' for c in checks) and all(s['state'] == 'success' for s in statuses['statuses']):
            return
        sleep(5)
    raise ValueError('head checks did not complete within bounded wait')


def orchestrate(api, run_id, attempt, trusted_base, sleep=None):
    policy.require(policy.SHA.fullmatch(trusted_base), 'invalid trusted checkout SHA')
    await_checks(api, api.get(f'/actions/runs/{run_id}')['head_sha'], sleep=sleep)
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
    policy.require(fresh['_gate_protection'] == pr['_gate_protection'], 'branch policy changed during approval')
    state = api.review_state(number)
    verify_protection(state)
    policy.require(state['baseRef']['branchProtectionRule'] == pr['_gate_protection'],
                   'branch policy changed before merge')
    policy.require(state['headRefOid'] == head and state['baseRefOid'] == trusted_base, 'policy SHA changed')
    # GitHub REST merge has an atomic head guard, but NO atomic expected-base guard.
    # Strict required checks close that race server-side. Missing protection => manual.
    rule = (state.get('baseRef') or {}).get('branchProtectionRule') or {}
    strict = (rule.get('requiresStatusChecks') is True and rule.get('requiresStrictStatusChecks') is True and
              all(name in rule.get('requiredStatusCheckContexts', []) for name in REQUIRED_JOBS))
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
    from publication import dispatch
    pages = dispatch(api, result['sha'])
    return {'result': 'merged', 'pr': number, 'head': head, 'merge_commit': result['sha'],
            'pages': pages, 'publication': 'Dispatch observed; deployment and public bytes must be verified separately.'}


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
