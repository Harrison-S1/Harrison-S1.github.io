# Production blog automation: reviewed bootstrap and activation

## Status: implementation staging, NOT production completion

This bootstrap builds on the off-by-default PR3 foundation. It needs a legitimate
independent **infrastructure review** and normal-policy merge before activation.
Do not merge PR3 unchanged as a substitute. No workflow approves its own changes.
No administrator bypass, force push, branch deletion, broad PAT or invented
review identity is supported. Sam approved implementation and controlled scoped
repository operations; this document does not remove any review prerequisite.

The existing `gh` identity and infrastructure PR author are both `Harrison-S1`.
GitHub rejected that OAuth identity's actual self-approval on PR3. This proves a
bootstrap-review constraint, **not** that workflow `GITHUB_TOKEN` reviews cannot
satisfy normal policy. Workflow-token eligibility remains an actual live test
required AFTER bootstrap; do not claim a GitHub App is necessary without that
result. If no eligible independent reviewer exists, stop for Sam's decision.

## Foundation

- Ubuntu24.04 runner; Ruby **3.4.12** (normally maintained3.4 branch),
  Bundler **2.6.9**, Jekyll **4.4.1**, Chirpy **7.6.0**.
- Exact Gemfile pins and regenerated `Gemfile.lock`, including gem checksums.
  CI/content/Pages use frozen installs with the same toolchain, no gem caches.
- SHA-pinned actions, Python3.12.12 and hash-locked binary Python parsers.
- Existing content/URLs retained; canonical URL set and existing analytics ID
  migrated to Chirpy7 schema. `docs/` is not published. No dependency lock is a
  guarantee against every vulnerability; review future updates manually.
- The inherited lastmod plugin cannot infer Git history from an archived content
  overlay and emits Git warnings there. Real main checkout has history. Validation
  does not certify historical lastmod timestamps.

## Routine eligibility and meaningful validation

Only open, non-draft, same-repository `main` PRs authored by numeric GitHub identity
`Harrison-S1`/`54186142`. Both head and current base are bound to exact40-hex SHAs.
Base must be an ancestor of head. Every changed file is checked; no partial diff.

Allow additions/modifications of at most20 regular non-executable `100644` blobs:

- `_posts/YYYY-MM-DD-lowercase-slug.md`: max100,000 bytes; at least one post;
  safe restricted YAML, date/timezone matching filename, meaningful heading/prose,
  no duplicate slug, overrides, YAML tags/aliases/anchors/duplicate keys.
- `assets/img/posts/lowercase-folder/lowercase-file.{png,jpg,jpeg,webp}`:
  max2MB, decoded matching-format single-frame raster, max4096 per dimension and
  12million pixels. Aggregate changes max8MB. No SVG/HTML/script assets.
- `examples/posts/<matching-post-slug>/<lowercase-file>.{py,json,txt,j2}`:
  max20,000 bytes; must accompany that post. No front matter, HTML or NUL.
  JSON is parsed; txt/Jinja are **inert bytes**, never template-rendered.
  Python companions support only bounded integer assignment/arithmetic/comparison
  and explicit true assertions: max200 AST nodes, depth12, magnitude1million.
  No eval/exec/compile, imports, calls, attributes, indexing, loops, powers,
  strings, network, filesystem or process operations exist in this interpreter.
  This is a deliberately small test language, NOT arbitrary Python execution.
  General Python, shell companions, Ansible, Terraform, workflows, inventory,
  dependencies and infrastructure-changing examples stay manual.

Inline/fenced code and Jinja examples are supported. Posts containing literal
`{{`/`{%` MUST set `render_with_liquid: false`; opting into Liquid is forbidden.
Jekyll honors that native field before Markdown, preserving examples literally.
No include/raw/other active Liquid exception. Raw HTML, Kramdown source attribute
extensions and indented code stay manual.

CommonMark is an early parser, NOT the security renderer. Before Jekyll the exact
locked **Kramdown GFM AST** rejects raw HTML/comment/PI/raw nodes, closing the
previous inline-code renderer disagreement. Its complete HTML fragment is also
inspected. Python fences use AST syntax parsing; shell fences use `bash -n` with
clean environment and timeout; JSON/YAML fences are parsed only. Other languages
are displayed passively, not represented as syntax-validated or executed.

Then a full real production Jekyll build runs against an archive of ONLY the
trusted base infrastructure plus validated changed bytes. Actual Chirpy article
HTML has one exact `content` wrapper, passive allowed elements/attributes and
safe URLs. Actual rendered and parsed source links must resolve locally, including
anchors/images/examples. External HTTPS is syntax-only, never fetched (SSRF).
Future-dated posts not yet rendered fail the published-page expectation instead
of silently being represented as published. These checks do NOT assess factual
accuracy, editorial quality, copyright, screenshots or real-world command safety.
PR2's existing Ansible implementation remains manual and is not auto-published.

## Privileged boundary and normal policy

`blog-content.yml`: read-only PR job, exact base checkout, credentials not
persisted, no secrets/caches/PR scripts. Bounded examples are interpreted as data
in this read-only job, not run as contributor programs. The complete build must
succeed before `Blog content / validate` succeeds.

`blog-automation-tests.yml`: read-only proposed-code tests and **always-present**
`Site / frozen build` on every main-target PR. Its proposed infrastructure is
still subject to independent manual review. Unlike PR3, the proposed modern site
is actually built, not just the old trusted base.

`blog-content-decision.yml`: serialized default-branch `workflow_run`, disabled
unless BOTH activation variables match. No artifacts/caches or PR checkout;
stdlib-only Python in the write-capable job. `actions: write` is required solely
for the explicit Pages dispatch after verified merge. It waits at most4minutes
for other head checks, then revalidates before AND after approval:

1. Expected workflow ID/path, successful current run/attempt, PR association,
   job/check suite from GitHub Actions, exact head/base and latest validation run.
2. Current PR identity/state/files/modes/sizes; current main equals validated base
   and trusted orchestrator checkout. API errors/truncation/ambiguity fail closed.
3. Every returned check/status successful. Reviews remain required (>=1), stale
   dismissal, CODEOWNER and last-push approval enabled; no force/deletion policy.
   Required `Site / frozen build` is pinned to GitHub Actions App ID15368.
4. Exact-head review is read back by ID/state/SHA/`github-actions[bot]` identity.
   A bot review is NOT assumed to satisfy eligibility. Only GitHub's normal
   `APPROVED`/`CLEAN` and mergeable/clean plus **strict up-to-date** required build
   permit the exact-head-guarded squash merge. REST has no atomic expected-base
   field; strict checks are the mandatory server-side base-race guard.
5. Merge is read back. Explicitly dispatch native Pages on `main` with the exact
   verified merge SHA and observe its new matching run. Writes are not retried.
   Dispatch success is NOT deployment/publication proof. A gap after merge stops
   with the old site intact; inspect the remote before explicit recovery.

Existing required reviews, CODEOWNERS, stale/last-push policies are never weakened.
If the bot approval does not count, return `manual-policy-required`, keep the PR
open and report the precise identity/reviewer prerequisite. Do not solve it with
an administrator token or self-approving workflow changes. Mergeability may take
GitHub time to recalculate: fail closed and rerun successful content checks after
it settles; there is no claim of an infinitely retrying approval loop.

## Native Pages handoff

`pages-deploy.yml` replaces the legacy gh-pages push script with native artifact
publishing. Legacy branch/history is retained. Runs only on main push/explicit
main dispatch and only after deployment acknowledgement. Both build and deploy
check `expected_sha == github.sha == current main`, rejecting stale queued work.
Build has contents-read only. Deploy depends on successful build and has only
contents-read, pages-write and OIDC-write, with `github-pages` environment.
Only this run's official uploaded artifact is used; no PR artifacts are trusted.
An environment **main-only branch policy** is mandatory setup, not merely a
workflow `if` (another branch could otherwise modify its own workflow).
Failed builds never reach deployment and leave the last successful site serving.
The generated public `/build-info.json` identifies exact SHA and Pages run ID.

## Ordered activation runbook (approved scope, blocked on bootstrap review)

1. Obtain eligible independent review of this **new modernized bootstrap PR**,
   at its final head, with normal branch policy satisfied. Sam cannot approve
   his own PR using another token for the same identity. Do NOT merge obsolete
   PR3, use admin override, weaken reviews or create credentials. After review,
   re-read reviews/checks/head/base and perform only normal-policy merge.
2. Leave both variables absent. Save exact current protection/Pages/environment
   JSON. Configure strict up-to-date required checks using the **status-check
   subresource only**, preserving all existing contexts and review policy:

   `Site / frozen build` and `Automation / offline adversarial tests`, both
   GitHub Actions App ID15368; strict=true. Read back exact protection and verify
   review count/codeowner/last-push/stale fields unchanged. Do not require the
   path-filtered content job globally, which would strand manual infra changes.
3. Restrict existing `github-pages` environment to custom branch policy `main`
   (type `branch`, not tag). Preserve current reviewers, wait timers and other
   protection rules; if any introduces a human gate, report it rather than
   removing it. Current observed environment has no rules, but re-read first.
   Set Pages build type to `workflow`, preserving HTTPS/domain configuration.
   Verify exact readbacks; never delete the gh-pages branch.
4. Set `BLOG_CONTENT_DEPLOYMENT_READY=acknowledged` and verify. Explicitly
   dispatch `pages-deploy.yml` with `ref=main`, `expected_sha=<current exact main>`.
   Observe successful native deploy, public marker and representative old pages,
   CSS/JS/images. No automerge yet; preserve existing site if build fails.
5. Set `BLOG_CONTENT_AUTOMERGE=enabled` only after foundation is actually live.
   Create a clearly labelled controlled routine technical test PR with native
   Liquid opt-out, inline/fenced/Jinja code, passive PNG and bounded arithmetic
   companion under its matching slug. No deletion. Record exact base/head.
6. Observe real workflow GITHUB_TOKEN review and read GitHub's review decision.
   If eligibility is unmet, stop with exact evidence; Sam must arrange legitimate
   independent review or explicitly authorize/setup an independent scoped identity.
   An App is conditional, not assumed necessary. No native profile changes.
7. When normal policy permits, verify real merge, explicit dispatch/run/jobs,
   exact merged SHA, successful native deploy and public marker/page/assets.
   Use the read-only evidence collector below. A PR or green offline tests alone
   does not satisfy production acceptance.
8. Exercise a separate controlled negative (wrong bounded assertion or unsafe
   content), prove failed check/no approval-merge/no new deployment and unchanged
   published marker/assets. Correct that same PR without deletion; rerun and
   verify recovery through review/merge/deploy/public bytes. Retain all evidence.

No setting-write command here is an instruction to activate before review. When
applying approved settings, use `gh api`, explicit typed JSON payloads and exact
readbacks. Preserve existing required contexts; never PUT an incomplete replacement
branch-protection object. If a prerequisite fails, automation remains off.

## Reproduce checks and collect live evidence

```sh
bundle install                       # BUNDLE_FROZEN=true, pinned Ruby/Bundler
python -m pip install --require-hashes --only-binary=:all: -r .github/automation/requirements.txt
python -m unittest discover -s .github/automation/tests -v
bundle exec jekyll build --trace --destination <new-output-directory>
```

The suite's FakeAPI/canned transport successes are **offline fixtures**. Real
local Git-object success, failed assertion, symlink rejection and corrected
recovery builds are also local fixtures, not remote review/deploy proof.
Actionlint and zizmor check workflow schema/trust boundaries; suppressed findings
remain disclosed. Hosted images/package servers are not hermetic trust boundaries.

After an actual controlled success/recovery, collect read-only evidence:

```sh
python .github/automation/live_evidence.py --pr <actual-pr-number> \
  --expected-sha <actual-merged-sha> --page /posts/<controlled-slug>/ \
  --text '<unique-controlled-post-marker>' \
  --asset /assets/img/posts/<controlled-slug>/check.png \
  --asset /examples/posts/<controlled-slug>/check.py \
  --output <new-evidence-json-path>
```

It uses the existing gh account for read-only APIs and fixed-site public HTTP,
checking merge, exact-head bot approval, successful matching dispatched Pages run,
public SHA marker, page text and exact asset SHA256 against merged Git blobs.
Also retain protection/activation/environment readbacks and actual job URLs.
No credentials are written into evidence. Never label these checks successful
before executing them against real PR/deployment/public responses.

Emergency stop: set `BLOG_CONTENT_AUTOMERGE=disabled` (do not delete variables),
read back, inspect any mutation already in flight. To stop publication, set
`BLOG_CONTENT_DEPLOYMENT_READY=disabled`; it does not cancel an already running
job. No automatic rollback/deletion of published content. For a post-merge
handoff failure, first inspect current main and existing runs, then explicitly
dispatch the fixed workflow for that same current main SHA; older SHAs are
rejected. Reverting source requires a separately reviewed normal-policy PR.

## Primary technical references

- https://www.ruby-lang.org/en/downloads/branches/
- https://jekyllrb.com/docs/liquid/options/
- https://chirpy.cotes.page/posts/getting-started/
- https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- https://docs.github.com/en/rest/branches/branch-protection
- https://docs.github.com/en/rest/deployments/environments
