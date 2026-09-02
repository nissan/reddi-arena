# REASONS-LITE — Implement dry-run escrow for purse and fees

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C5 | Epic: E09 Prove — Escrow, Receipts and Attestation |
Phase: P2 Mercenary Market | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

The purse teaches the single most important RAP lesson: payment success is not work success.

**DoD checklist:**

- [ ] Transport success alone never releases escrow
- [ ] A failed required gate routes to refund or dispute, never payout
- [ ] Selecting any non-dry-run rail is refused
- [ ] Escrow accounting balances to zero across every terminal state

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Purse and fees move only on the allowed success path, and every movement is bound to evidence. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [C3] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The purse teaches the single most important RAP lesson: payment success is not work success. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Lock both purses and any hire fees at match start
2. Release only on completion.status=pass with required gates passed
3. Implement refund, timeout, and dispute paths
4. Assert no live rail can be selected even if declared

## N — Norms

- GitHub issues are the project spine; every work loop anchors on one issue
  (Loop Protocol, reddiagent-lab docs/LOOP-PROTOCOL.md).
- This artifact must be updated in the same PR if implementation materially
  diverges (SPDD sync rule).
- ADL semantics flow one way from reddiagent-lab; Arena files findings upstream
  and never forks the spec.
- Everything runs on the x402-dry-run rail with ARENA-CREDIT prizes; no wallet,
  no live rail, no real value. Devnet writes need explicit operator approval.
- No new *_packet/*_gate/*_handoff/*_signoff scripts (2026-07-26 pause).
- Claims discipline: no public surface may state more maturity than a passing
  test or published artifact supports.

## S — Safeguards / Acceptance

**Boundary (what this issue does NOT authorize):** Rail is pinned to x402-dry-run. livePaymentAccess is false. No wallet, facilitator, custody, or real value exists anywhere in this issue.

| Test | Type | Asserts |
|---|---|---|
| T-051 | contract | Transport success alone never releases escrow |
| T-052 | contract | A failed required gate routes to refund or dispute, never to payout |
| T-053 | adversarial | Selecting any rail other than x402-dry-run is refused |
| T-054 | property | Escrow accounting balances to zero across every terminal state |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0021-c5-implement-dry-run-escrow-for-purse-and-fees.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C5 — Implement dry-run escrow for purse and fees
Epic: E09 Prove — Escrow, Receipts and Attestation | Dependencies (must already be closed): C3

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-051, T-052, T-053, T-054.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Rail is pinned to x402-dry-run. livePaymentAccess is false. No wallet, facilitator, custody, or real value exists anywhere in this issue.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
