# The independent review gate

A reusable playbook for the review step that sits between "author says done"
and "merge". Codified from the 2026-08-24 retro-audit remediation, where it
caught real defects on the exact boundary each PR existed to close. Referenced
by `10-node-executor.md`; enforced by `policies.requireIndependentReview` in
`planning/graph.yaml`.

**Status: pilot-local.** Promotion of this template to `reddi-agent-protocol`
and `reddiagent-lab` is gated behind the 2026-08-31 lab launch per the GE03
ADR. Do not copy it upstream before then.

## The rule

No PR is reported ready for merge until an **independent reviewer** — a fresh
context that did not write the change — has examined the **full diff** and its
findings have been resolved. Author verification (suite + lints + CI green) does
**not** satisfy the gate; it is the precondition for entering it.

"Independent" means a different reasoning context than the author: a review
subagent, a second session, or a second person. The point is a reviewer with no
stake in the implementation being correct and no memory of why a shortcut
"seemed fine" — the blindness that a self-review structurally cannot cover.

GitHub's own required-approval enforcement is **not** usable while every PR is
authored by the operator's own account (GitHub forbids self-approval), so the
gate is **process-enforced**: it lives in this playbook and the node loop, not
in branch protection, until a second reviewing identity exists.

## The loop

1. **Implement** on the node/fix branch; verify locally (named tests, `-O`,
   lints, balance sweep where relevant). Green is required to proceed, not to
   finish.
2. **Open the PR** with the evidence: what changed, why, and the verification
   output.
3. **Dispatch the independent review** over `git diff main...HEAD`. Brief the
   reviewer adversarially — give it the security/behaviour contract the change
   is meant to hold and ask it to **try to break it**: construct the input that
   defeats the fix, the edge that crashes, the boundary the diff crosses.
4. **Resolve every finding.** Each is either fixed on the branch or explicitly
   rebutted with reasoning. A blocker or major fix earns **another** review
   round — prior rounds in this wave repeatedly found new defects in the fix
   itself.
5. **Post the outcome** on the PR thread (what the review found, what changed)
   so the record shows review preceded merge.
6. **Rebase + re-verify**, then merge (rebase/linear). Merge only on a standing
   APPROVE.

## What the reviewer is charged with

- **Correctness & edge cases** — the failure input, not the happy path. Non-
  dict, unhashable, empty, huge, `NaN`/`inf`, mis-cased, non-ASCII, duplicate.
- **The exact boundary the PR claims to seal** — does the fix actually close
  *every* variant of the hole, or just the one named in the finding?
- **Fail-open vs fail-closed** — on a containment boundary, does an unknown or
  malformed input degrade to the safe state, or slip through?
- **Determinism / outcome-neutrality** — for an engine change, does the diff
  move any well-formed result? Prove it against the balance sweep, don't assert
  it.
- **Test adequacy** — would each new test actually **fail** if the fix were
  reverted? A test that passes both ways guards nothing.
- **Scope & project boundaries** — does the diff respect the repo's hard rules
  (dry-run only, one-way canonicality, claims discipline, determinism)?

## Why it earns its place — evidence from the remediation wave

Across ten remediation PRs, the gate found defects the author's green suite did
not, twice on the highest-stakes changes:

- **#67 (BLOCKER)** — the first binding-hash fix bound the egress and policy
  surface but not the per-policy `maxInvocations` cap. A weigh-tight /
  field-loose swap on the cap still slipped past the hash. Caught and closed
  before merge — the fix's own blind spot on the boundary it existed to seal.
- **#70 (MAJOR)** — an unvalidated entered class mapped a mistyped name to a
  ceiling of zero, forfeiting the employer with a trace **indistinguishable
  from a genuine breach** — a silent wrong result, worse than a crash. The gate
  turned it into a loud, distinct error.

Both would have shipped green. Beyond these, most rounds surfaced minors
(fail-open guards, over-scrub, doc/claim overstatements) that were folded in as
fast-follows. The cost — one review pass per PR — bought a remediation wave that
moved **zero** well-formed matches and left no known hole on the audited
surface.

## Anti-patterns

- Treating a green suite as the gate. It is the ticket in, not the verdict.
- One review round on a blocker fix. Re-review after any non-trivial change.
- A reviewer briefed only on the happy path. Hand it the contract and ask it to
  break it.
- Tests written to pass. Confirm they fail on revert.
- Silently applying reviewer suggestions without recording the outcome on the
  thread — the record must show review preceded merge.
