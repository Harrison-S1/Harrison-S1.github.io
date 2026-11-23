"""Explicit trusted Pages handoff. No PR checkout and no publication claim on dispatch."""
import time
import content_policy as policy

WORKFLOW = '.github/workflows/pages-deploy.yml'


def dispatch(api, merged_sha, sleep=time.sleep):
    policy.require(policy.SHA.fullmatch(merged_sha), 'invalid merged SHA')
    policy.require(api.get('/git/ref/heads/main')['object']['sha'] == merged_sha,
                   'main advanced before dispatch; no old release deployed')
    workflow = api.get('/actions/workflows/pages-deploy.yml')
    policy.require(workflow['path'] == WORKFLOW and workflow['state'] == 'active', 'wrong Pages workflow')
    path = f'/actions/workflows/{workflow["id"]}/runs?event=workflow_dispatch&head_sha={merged_sha}'
    before = {run['id'] for run in api.pages(path, 'workflow_runs')}
    # Explicit workflow_dispatch is not suppressed by GITHUB_TOKEN event rules.
    api.write('POST', '/actions/workflows/pages-deploy.yml/dispatches',
              {'ref': 'main', 'inputs': {'expected_sha': merged_sha}})
    for _ in range(12):
        runs = api.pages(path, 'workflow_runs')
        matches = [r for r in runs if r['id'] not in before and r['workflow_id'] == workflow['id'] and
                   r['head_sha'] == merged_sha and r['path'] == WORKFLOW and
                   r['event'] == 'workflow_dispatch' and r['display_title'] == 'Publish ' + merged_sha]
        policy.require(len(matches) <= 1, 'ambiguous Pages dispatch readback')
        if matches:
            return {'run_id': matches[0]['id'], 'url': matches[0]['html_url'], 'sha': merged_sha,
                    'status': 'dispatch-observed-not-publication-proof'}
        sleep(5)
    raise ValueError('Pages dispatch not observed; inspect remote before explicit recovery dispatch')
