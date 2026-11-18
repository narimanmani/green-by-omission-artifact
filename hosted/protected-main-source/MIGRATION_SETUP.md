# SP2027 reviewed-fixture migration

Status: proposed and unmerged. Checkpoint 1 is `1d63949857934672de5c13f543174b4dbf0fd7ce`.
Do not describe this as protected-main experiment evidence until every hosted proof below is captured.

## Study scope and execution boundary

This is a fixed, reviewed source-fixture study, not arbitrary candidate Python isolation.
The sole accepted application change is the exact PR #8 Requests fixture from
`c0176fc99f87826cad9081ff2da2963709478f57`, SHA-256
`0d73a268f74ffd673056d818fae5ee42eab45758ccc81fa041cbe326b887771f`.

Protected-base `reviewed_fixture.json` describes its three literal changes.
The trusted validator constructs the fixture from the unchanged baseline, checks both
digests, then requires one direct-parent commit modifying only the regular 100644
`cases/requests_crlf_header/requests/utils.py` blob to those exact bytes.
Unknown source, extra paths, mode changes, policy changes and additional commits fail
before pytest. Only constructed protected-base fixture bytes are executed. Nothing
is imported from the PR worktree.

Observer JSON is a measurement of this reviewed fixture, not independent attestation
for arbitrary malicious code. A future arbitrary-source study requires a different,
genuinely isolated execution/evidence design.

## Administrator-held workflow provenance

The following two **active GitHub Actions execution policies** are required.
They are administrative repository settings, not candidate-controlled YAML.
Create and verify both through Settings → Actions → Policies:

1. **SP2027 owner-only other workflows**: include all workflows; exclude exactly
   `.github/workflows/validation.yml`; Restrict actors to owner `anonymous-owner` only.
2. **SP2027 trusted gate event**: include exactly
   `.github/workflows/validation.yml`; Restrict events to `pull_request_target` only.

Do not grant `anonymous-contributor` policy bypass, Admin, owner or token access.
The combination prevents that collaborator from executing a modified/new alternate
workflow to publish a counterfeit `testmon-required`, and prevents branch-owned
`push`, `pull_request`, review or dispatch versions of `validation.yml` from running.

The trusted gate is loaded from the protected default branch. It requires a private
same-repository PR targeting current `main` and requires the PR base SHA to equal
the workflow's default-branch SHA. It reads candidate Git objects for comparison
only. This is not a `pull_request_target` execution of unreviewed PR source.

The selection job has read-only contents/actions permissions. The separate fresh
status reporter has only statuses:write and pull-requests:read; it performs no
checkout, artifact ingestion or test execution. It publishes the static required
context `testmon-required` to the captured PR **head** SHA only if the current PR
still has that head and base. A job check attached to the default-branch SHA is
not used as a substitute for head validation.

The separate `main-cache.yml` runs only for an owner push to protected main.
The consumer requires a successful owner push run of that exact workflow at the
exact base SHA, then verifies cache metadata and database digest. Main merges for
this experiment must be performed by the owner; otherwise no new cache is produced
and subsequent selection fails closed.

Existing owner-triggered research workflows remain available. The collaborator
can trigger only the trusted default-branch gate. Do not assume an optional
dependency lockfile policy solves workflow provenance: it covers action dependencies,
not arbitrary workflow steps.

## Review, migration and recovery

- `anonymous-contributor` already has accepted nonadmin collaborator access. No new
  invitation or promotion is needed. A review under that account proves a distinct
  GitHub permission identity, not independent human review if both accounts share
  an operator.
- Obtain a fresh review of the exact final migration commit, including the fixture,
  gate, reporter, tests and both administrative policies. Do not dismiss the existing
  changes request or mark security discussions resolved merely because a patch exists.
- Preserve required PRs, one approval, code-owner review, stale-approval dismissal,
  conversation resolution, strict up-to-date `testmon-required` from GitHub Actions,
  no administrator bypass, and no force pushes/deletions.
- This migration changes more than the permitted application path and cannot pass
  the old gate. It needs a documented, explicitly authorized, one-time administrative
  process after vetting. Never introduce an `if PR number == 9` self-bypass, fabricate
  success, silently weaken the gate or merge an experiment.
- Record the reviewed commit, old/new settings, administrative actor, reason,
  exact merge SHA, restored protections and policy IDs. Restore strict protection
  immediately after any specifically approved administrative exception.
- Never force-push or delete checkpoint history. Recover with an audited approved
  revert, retaining Checkpoint 1 as the reference.

## Hosted acceptance evidence required before the actual experiment

1. Verify both administrative policies are active and reject collaborator-triggered
   alternate workflows and non-target events. Use harmless policy probes; do not
   mistake blocked execution for a successful test run.
2. After the vetted migration, verify owner main-push `trusted-main-cache` succeeds
   and publishes `testmon-cache-<merged-main-SHA>`.
3. Verify actual run event, actor, `workflow_ref`, workflow SHA, base/head and
   report provenance. Confirm GitHub recognizes the exact-head status as originating
   from GitHub Actions and enforces it. Required check names alone are not provenance.
4. Only then create the real `anonymous-contributor` experiment PR from updated main:
   one commit, one application-source file, exact reviewed fixture bytes.
5. Capture one real passing `test_valid_header_passes` call under selection;
   full and AST diagnostics must run all three unchanged tests and fail the
   header-injection security test. Infrastructure failures are not that outcome.
6. Capture the merge block requiring owner `anonymous-owner` code-owner approval.
   CODEOWNERS must exist on the protected base; enabling the setting alone is not
   owner coverage. Do not approve or merge the experiment PR. Close it after collecting
   its evidence.

A local replay does not establish any hosted enforcement result.
Keep this repository, source fixtures and raw evidence private.

