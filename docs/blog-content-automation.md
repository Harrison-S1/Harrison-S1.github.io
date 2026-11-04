# Checks-only blog content automation

## Status and limits

This implementation is **not AI review** and does not assess technical truth, command safety, factual accuracy, writing quality, copyright, screenshot provenance or editorial suitability. It never runs article snippets or Ansible examples. Passing checks is not a security audit or an editorial approval.

The privileged decision job is **off by default**, even after this PR is merged. No repository settings, branch protections, CODEOWNERS, secrets, existing deployment workflow or existing PRs are changed by this implementation. Do not enable it until the separate prerequisites below have been reviewed by Sam.

### Narrow automatic-review policy

- Open, non-draft PR to `main`; same source and target repository `Harrison-S1/Harrison-S1.github.io`; author exactly `Harrison-S1` with GitHub numeric ID `54186142`. A matching display name is not enough. Forks and other authors require manual review.
- 1–20 changed files, at least one post. Only additions/modifications of `_posts/YYYY-MM-DD-lowercase-hyphenated-slug.md` and `assets/img/posts/lowercase-hyphenated-folder/lowercase-hyphenated-file.{png,jpg,jpeg,webp}`.
- Only regular nonexecutable Git blobs (`100644`). Deletions, renames (including delete+add), copies, symlinks, submodules and mode/type changes fail closed. Uppercase filenames and other image directories require manual review.
- Each post at most 100,000 bytes; each image at most 2,000,000 bytes; aggregate at most 8,000,000 bytes. Raster images are decoded, extension/magic checked, single-frame only, at most 4096 in either dimension and 12 million pixels.
- YAML front matter requires `layout: post`, title, timezone-aware date matching filename, nonempty lowercase categories and tags. Only optional `description` and boolean `toc` are accepted. Duplicate keys, aliases, anchors, tags, extra keys (including permalink, redirect, scripts and layout overrides), oversized front matter and control characters fail.
- Markdown is parsed, requires a heading and explanatory text, and checks link/image destinations. Fences must close and have a plain language identifier. Raw HTML, HTML comments, PHP-like tags, indented code, **inline backtick code**, any literal `<` (even in a fence), Kramdown attribute extensions and **all Liquid**, including inside code fences, require manual review. No include/raw/relative_url exception is silently trusted: Liquid runs before Markdown. This conservative subset intentionally rejects harmless posts as well as attacks. An independent review reproduced a CommonMark/Kramdown disagreement where spaced inline code hid active HTML and JavaScript links; source restrictions and actual rendered-output inspection close that bypass.
- Duplicate post slugs fail. The actual Jekyll/Kramdown-rendered article must have exactly one Chirpy `post-content` wrapper, only allowed passive elements/attributes, no active elements/event handlers/styles, and safe destinations. Links are checked from both parsed Markdown and actual rendered article output (including lazy-image data-src). Root-relative local links and fragments must resolve in the real Jekyll output, including changed post pages and assets. External links must be credential-free HTTPS with safe syntax. They are **not fetched**: availability and external fragments are unverified; arbitrary network link checking would create SSRF and nondeterminism. Relative `../` links, protocol-relative links, HTTP, data and javascript URLs are not accepted. Theme changes to this wrapper/attribute contract fail closed and require review.
- Workflow, configuration, Gemfile/lockfile, plugin, theme, executable, script and companion-example changes are never eligible. **PR #2 (Ansible article) is ineligible**: it includes `examples/ansible-basics/**` code, inventory, templates and dependencies. Keep its manual review path. Do not split mixed changes merely to evade this review requirement.

## Trust boundaries

`blog-content.yml` runs on read-only `pull_request`, with no secrets, no persistent checkout credentials and no shared cache. It checks out the exact **base SHA**, not the PR head. The trusted validator fetches the exact public head Git object (fixed repository URL), checks that current base is its ancestor, enumerates the complete Git diff and validates modes, byte sizes and content. It archives only the base tree, then overlays only approved post/image bytes. The PR Gemfile, plugins, scripts and config are never checked out or executed.

The full site then builds with unchanged trusted base Gemfile/lockfile, frozen deployment Bundler mode, Ruby 3.1.7, Bundler 2.3.16, Jekyll 4.2.2 and Chirpy 5.2.0. `--future` validates even future-dated posts; it does not promise publication before their date. The archived tree has no `.git`, so the existing last-modified plugin prints Git warnings and cannot prove Git-derived lastmod values. The build and rendered links still must succeed. Base code and dependencies are a trusted boundary, not made safe by accepting content only.

`blog-automation-tests.yml` is a separate read-only PR workflow: it tests proposed implementation code without write credentials and also builds the **trusted base**. It runs for all main-target PRs, providing the always-present `Trusted base / Jekyll build` check suitable for strict up-to-date protection. For non-content changes this base build is only a baseline check, not validation of proposed code; human review and appropriate additional CI remain necessary.

`blog-content-decision.yml` uses `workflow_run` from the default branch, checking out only the trusted default-branch event SHA. It installs no Python packages and downloads no PR artifacts/caches. Its write-capable job requires both explicit activation variables. Every action is pinned to a full commit SHA; runners are `ubuntu-24.04`, Python is 3.12.12, parsers are exact versions with wheel hashes. Hosted runner images and dependency package servers are not immutable hermetic environments; Ruby gems are version-locked by the existing lockfile but that old lockfile has no checksums.

Before approval, and again after approval, the orchestrator re-fetches:

1. Exact workflow ID/path, `pull_request` event, successful completed run/attempt, same repository, unique associated PR, matching current head and base SHAs, and no newer validation run.
2. Successful expected job and GitHub Actions check-suite/check-run provenance, not an arbitrary success context or uploaded report.
3. Current PR author/state/draft/base/repository, complete changed-file list, head-tree modes/sizes and count/truncation checks. Mixed code/content PRs fail even if someone spoofs a green check.
4. Current `main` equal to the validated base and trusted orchestrator checkout. All returned current head check runs must be completed/successful; pending, skipped, neutral, cancelled, timed-out and failed checks reject. Legacy status contexts must all be successful and untruncated.

The approval specifies `commit_id` and is read back by review ID, state, bot identity and SHA. GitHub policy must then report `reviewDecision=APPROVED`, `mergeStateStatus=CLEAN`, REST mergeable/clean, and strict required status-check protection containing `Trusted base / Jekyll build`. A final head/base/main read precedes a normal REST squash merge with **atomic expected head SHA**. No admin flag, direct main push, protection bypass or automatic-merge setting is used. Successful merge responses are verified by reading the PR's merged state and merge commit.

REST merge has no expected-base parameter. Re-reading alone does **not** eliminate the final base-update race: strict required up-to-date checks are a mandatory server-side prerequisite. The content workflow separately proves the base is an ancestor of the head; if main advances, strict protection must block the merge until the branch is updated/revalidated. Missing protection leaves the PR open with `manual-policy-required`. The current repository has no required status checks, so it cannot automatically merge under this design as configured today.

Job timeouts and PR-validation cancellation limit resource use. Privileged decisions are serialized and never cancel a mutation in flight. API failures, truncated lists, ambiguous associations, changed heads/bases and network uncertainty fail closed. Writes are never automatically retried. If checks are still pending, or GitHub policy/mergeability is still recalculating, rerun the successful content workflow after they settle. A failed or cancelled newer run must first be rerun successfully; do not reuse an earlier success.

## GITHUB_TOKEN, reviews and publication

Observed 2026-11-04: Actions may submit PR approvals; main requires one approving review, code-owner review for owned paths, last-push approval and stale-review dismissal. Admin enforcement is off, but this implementation never uses an administrator token. No CODEOWNERS exists at any of GitHub's three supported paths on current main; the codeowner setting does not itself assign an owner. The only listed human collaborator is the owner, Harrison-S1.

The approval setting authorizes the review API; it is **not a guarantee that a bot review satisfies protected-branch requirements**. A GITHUB_TOKEN review cannot stand in for a named human/team CODEOWNER. Last-push and ordinary approval eligibility remain GitHub's decision; the implementation does not assume an application approval counts as an eligible independent reviewer. No live bot approval/counting experiment was performed on PR #2 or this implementation PR. The safe supported behavior is: submit the checks result if enabled, then **stop unless GitHub reports all required reviews satisfied**. If it does not count the bot review, obtain an eligible independent human/CODEOWNER review. Do not weaken protections, add a PAT or grant a bypass to make it merge. If no eligible reviewer exists, automatic merge remains unavailable. A human approval can be followed by rerunning content checks; bot-triggered review events are not used as a recursion mechanism.

GITHUB_TOKEN generally suppresses downstream workflow triggers for events it creates. Current exceptions include explicit workflow/repository dispatch and PR opened/synchronize/reopened events, which can create approval-required workflow runs; that newer PR exception does not make merge/push deployment recursive. A GITHUB_TOKEN merge **does not trigger the existing push/main `Automatic build` deployment**, and token-created commits also do not trigger a GitHub Pages build. Current Pages publishes the `gh-pages` branch (`build_type: legacy`). Existing `pages-deploy.yml` is unchanged. **Merged is not published.**

This PR intentionally does not silently add dispatch/deploy privileges or change production deployment. Before enabling, Sam must either approve and verify a separate least-privilege deployment handoff (for example, a carefully designed successful-decision/deployment workflow that builds the verified merged main SHA and publishes through the normal Pages policy), or explicitly accept a documented human publish procedure. Do not assume adding `workflow_run` to the old deployment is safe or sufficient. Its existing push-only design, mutable action tags, Ruby 2.7 and credential handling need a separate reviewed upgrade.

## Activation steps — separate explicit authorization required

1. Sam reviews and merges this **implementation PR himself**, using normal policy. This development task does not merge it. Default-branch `workflow_run` automation is not active while it exists only in a PR.
2. Leave both activation variables absent. Run a disposable, explicitly authorized eligible content PR to observe read-only checks and successful frozen full build on the default-branch scripts. No live bot approval or merge is claimed by the implementation tests.
3. Upgrade/test the legacy Ruby/Jekyll/theme/native-gem stack under a separate reviewed PR before production auto-merge: Ruby 3.1 is end-of-life, and the inherited 2022 dependency lock is not represented as vulnerability-free. The pinned legacy runtime demonstrates compatibility, not a current security support guarantee. Update pins/hashes deliberately and retest both workflows; never unfreeze dependencies to hide a failure.
4. With separate settings authorization, configure main to require `Trusted base / Jekyll build` from GitHub Actions and **Require branches to be up to date before merging**. Keep existing approval/codeowner/last-push/stale-dismissal policies. This task makes no such settings changes. Do not require the path-filtered content job globally: that would block legitimate manual infrastructure PRs whose content workflow does not run.
5. Establish eligible independent review if GitHub does not count the application review. If named CODEOWNERS are added in future, those owners must approve affected files. Confirm `reviewDecision=APPROVED` normally; no bypass and no new credentials.
6. Resolve/test publication as above. Only after explicit Sam approval, set repository Actions variable `BLOG_CONTENT_DEPLOYMENT_READY=acknowledged`, documenting whether publication is automatic or human-operated. The variable is an acknowledgement, not a deploy test.
7. Only then, with explicit Sam approval, set `BLOG_CONTENT_AUTOMERGE=enabled`. This authorizes future eligible PR approvals/normal-policy merge attempts. Automatic merge still refuses missing strict checks or unmet reviews. Repository `allow_auto_merge` can remain false: the implementation uses the normal merge endpoint, not GitHub's separately enabled auto-merge feature.
8. Observe one separately authorized eligible PR end-to-end, verify exact run/head/base/review/merge and actual deployment. This implementation's offline tests deliberately do not exercise live mutations. To stop future decisions, remove/change `BLOG_CONTENT_AUTOMERGE`; cancel any queued decision and inspect a running mutation before assuming it stopped. No branch deletion or settings cleanup is automatic.

## Verification and maintenance

Run from repository root with an isolated Python environment:

```sh
python -m pip install --require-hashes --only-binary=:all: -r .github/automation/requirements.txt
python -m unittest discover -s .github/automation/tests -v
```

Tests cover eligible content, untrusted authors/forks/drafts/targets, mixed paths, unsafe operations/modes/sizes, YAML and Liquid/HTML attacks, unsafe and unresolved links, raster decoding, duplicate slugs, rendered local links/fragments, stale runs/attempts/heads, failed/cancelled/skipped/pending checks, pagination/API errors, policy-blocked and rejected merges, and exact review/head payloads. API tests use a canned transport/FakeAPI; their positive merge is **not a real GitHub merge**. Workflow invariant tests assert full-SHA pins, read-only PR permissions, no direct shell-expression injection, nonpersistent credentials and disabled/default-branch-only privileged execution.

Local development also used actionlint 1.7.12 and zizmor 1.32.0 on the three new workflows. Zizmor's `workflow_run` dangerous-trigger finding is explicitly acknowledged with a localized suppression and the trust-boundary explanation; it is not proof that this trigger is inherently safe. No baseline findings in the unchanged deployment are silently fixed or represented as new-workflow findings. Real frozen base and trusted-base-plus-validated-fixture full Jekyll builds and local page/image/anchor checks were performed; fixture metadata was explicitly synthetic and never submitted to GitHub. Logs and exact remote CI status belong in the implementation handoff, not fabricated test output here.

### Primary GitHub documentation consulted

Retrieved during implementation on 2026-11-04 (documentation is current at retrieval):

- [GITHUB_TOKEN authentication and least privilege](https://docs.github.com/en/actions/reference/authentication-in-a-workflow)
- [Events: pull_request, pull_request_target, workflow_run trust and default-branch behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [Triggering workflows: GITHUB_TOKEN recursion restrictions](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow)
- [GITHUB_TOKEN concepts and GitHub Pages restriction](https://docs.github.com/en/actions/concepts/security/github_token)
- [Protected branches: eligible reviews, last push, strict checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [CODEOWNERS locations, base-branch ownership and writer eligibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Merge endpoint, expected head SHA, conflict/policy responses](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request)

Some retrievals initially hit an extractor rate limit; primary article-body endpoints were used instead. Live repository REST/GraphQL reads established actual settings; they were not inferred from documentation examples.
