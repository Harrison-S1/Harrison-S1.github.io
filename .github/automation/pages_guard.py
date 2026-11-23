"""Fail closed before Pages build AND again immediately before deployment."""
import json
import os
from pathlib import Path
import content_policy as policy
from orchestrate import GitHub


def verify(api, expected, checkout, ref, event):
    policy.require(policy.SHA.fullmatch(expected) and expected == checkout, 'Pages expected/checkout SHA mismatch')
    policy.require(ref == 'refs/heads/main' and event in ('push', 'workflow_dispatch'), 'Pages must run on main')
    policy.require(api.get('/git/ref/heads/main')['object']['sha'] == expected,
                   'main advanced; refuse stale deployment')


if __name__ == '__main__':
    verify(GitHub(os.environ['GH_TOKEN']), os.environ['EXPECTED_SHA'], os.environ['GITHUB_SHA'],
           os.environ['GITHUB_REF'], os.environ['GITHUB_EVENT_NAME'])
    print(json.dumps({'verified_sha': os.environ['EXPECTED_SHA'], 'ref': 'main'}))
