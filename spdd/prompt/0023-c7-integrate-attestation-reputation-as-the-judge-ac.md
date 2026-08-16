# REASONS-LITE — Integrate attestation-reputation as the judge actor

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C7 | Epic: E09 Prove — Escrow, Receipts and Attestation |
Phase: P2 Mercenary Market | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

RAP already names a paid judge actor; the arena referee is that actor.

**DoD checklist:**

- [ ] Attestation state is present on every receipt
- [ ] A failed attestation blocks payout even when transport succeeded
- [ ] Judge unavailability produces a defined outcome, not an indefinite hang

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Purse and fees move only on the allowed success path, and every movement is bound to evidence. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [C6] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

RAP already names a paid judge actor; the arena referee is that actor. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Adopt attestation-reputation and hosted-attestation-claim from the package
2. Define the judge as an ADL-declared agent with its own eval gates
3. Record attestation state on every receipt
4. Detect and handle judge unavailability and judge disagreement

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

**Boundary (what this issue does NOT authorize):** An attestation is one evidence input. It cannot substitute for required eval gates or for payment proof.

| Test | Type | Asserts |
|---|---|---|
| T-059 | contract | Attestation state is present on every emitted receipt |
| T-060 | contract | A failed attestation blocks payout even when transport succeeded |
| T-061 | integration | Judge unavailability produces a defined outcome without indefinite hang |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0023-c7-integrate-attestation-reputation-as-the-judge-ac.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C7 — Integrate attestation-reputation as the judge actor
Epic: E09 Prove — Escrow, Receipts and Attestation | Dependencies (must already be closed): C6

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-059, T-060, T-061.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
An attestation is one evidence input. It cannot substitute for required eval gates or for payment proof.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
