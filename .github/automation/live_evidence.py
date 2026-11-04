"""Read-only live evidence collection; never approve/merge/dispatch or alter settings.
Run only after a controlled PR and deployment. A green offline fixture is NOT proof.
"""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.request import urlopen
import content_policy as policy


def verify_evidence(evidence, sha):
    policy.require(policy.SHA.fullmatch(sha), 'invalid expected SHA')
    pr = evidence['pr']
    policy.require(pr['merged'] is True and pr['merge_commit_sha'] == sha, 'exact merged SHA not verified')
    policy.require(any(r['state'] == 'APPROVED' and r['commit_id'] == pr['head']['sha'] and
                       r['user']['login'] == 'github-actions[bot]' for r in evidence['reviews']),
                   'no exact-head workflow-bot approval observed')
    policy.require(any(r['path'] == '.github/workflows/pages-deploy.yml' and
                       r['event'] == 'workflow_dispatch' and r['head_sha'] == sha and
                       r['status'] == 'completed' and r['conclusion'] == 'success' for r in evidence['runs']),
                   'successful exact-SHA native Pages dispatch not observed')
    policy.require(evidence['marker']['sha'] == sha and evidence['page_status'] == 200 and evidence['page_text_found'],
                   'public page/marker mismatch')
    policy.require(evidence['assets'] and all(a['status'] == 200 and a['sha256'] == a['source_sha256']
                                             for a in evidence['assets']), 'public asset byte mismatch/missing assets')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pr', required=True, type=int)
    parser.add_argument('--expected-sha', required=True)
    parser.add_argument('--page', required=True)
    parser.add_argument('--text', required=True, help='Unique visible/source marker in the controlled post')
    parser.add_argument('--asset', required=True, action='append')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    policy.require(policy.SHA.fullmatch(args.expected_sha) and args.pr > 0, 'invalid PR/SHA')
    policy.require(not args.output.exists(), 'evidence output already exists; keep prior evidence')
    for path in [args.page, *args.asset]:
        policy.link(path)
        policy.require(path.startswith('/') and not path.startswith('//'), 'only fixed-site root paths')
    def api(path):
        return json.loads(subprocess.check_output(['gh', 'api', 'repos/' + policy.REPO + path], timeout=60))
    def public(path):
        url = 'https://harrison-s1.github.io' + path
        with urlopen(url, timeout=30) as response:
            policy.require(response.geturl().startswith('https://harrison-s1.github.io/'), 'unexpected public redirect')
            data = response.read(8_000_001)
            policy.require(len(data) <= 8_000_000, 'public response size budget')
            return response.status, data
    status, page = public(args.page)
    marker_status, marker = public('/build-info.json')
    policy.require(marker_status == 200, 'missing public deployment marker')
    evidence = {'collected_at': datetime.now(timezone.utc).isoformat(), 'live_not_fixture': True,
                'pr': api(f'/pulls/{args.pr}'),
                'reviews': api(f'/pulls/{args.pr}/reviews?per_page=100'),
                'runs': api('/actions/workflows/pages-deploy.yml/runs?event=workflow_dispatch&head_sha=' + args.expected_sha + '&per_page=100')['workflow_runs'],
                'marker': json.loads(marker), 'page_status': status,
                'page_text_found': args.text.encode() in page,
                'page_sha256': hashlib.sha256(page).hexdigest(), 'assets': []}
    for path in args.asset:
        metadata = api('/contents' + path + '?ref=' + args.expected_sha)
        blob = api('/git/blobs/' + metadata['sha'])
        source = base64.b64decode(blob['content'], validate=False)
        asset_status, body = public(path)
        evidence['assets'].append({'path': path, 'status': asset_status,
                                   'sha256': hashlib.sha256(body).hexdigest(),
                                   'source_sha256': hashlib.sha256(source).hexdigest()})
    # Always retain actual observations, even when verification fails.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2))
    verify_evidence(evidence, args.expected_sha)
    print('Verified live exact-SHA merge/review/Pages/public page and asset bytes: ' + str(args.output))
