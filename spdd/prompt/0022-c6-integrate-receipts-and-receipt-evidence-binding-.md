# REASONS-LITE — Integrate receipts and receipt-evidence-binding per match and engagement

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C6 | Epic: E09 Prove — Escrow, Receipts and Attestation |
Phase: P2 Mercenary Market | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

The receipt is the artifact an external analyst can actually check.

**DoD checklist:**

- [ ] Every completed match and engagement emits a schema-valid receipt
- [ ] A receipt with a missing paymentProofRef fails validation
- [ ] No receipt ever contains credential material
- [ ] evidenceRef resolves to a retrievable trace

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Purse and fees move only on the allowed success path, and every movement is bound to evidence. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [C5], [B5] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The receipt is the artifact an external analyst can actually check. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Adopt receipts and receipt-evidence-binding rather than reimplementing
2. Populate the full v1 envelope including request/response hashes
3. Bind evidenceRef to the stored match trace
4. Fail closed on missing proof refs, malformed fields, or credential leakage

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

**Boundary (what this issue does NOT authorize):** A receipt records that policy, payment reference, and evidence reference existed. It does not prove settlement finality or provider quality.

| Test | Type | Asserts |
|---|---|---|
| T-055 | contract | Every completed match and engagement emits a schema-valid reddi.receipt.v1 |
| T-056 | contract | A receipt missing paymentProofRef fails validation closed |
| T-057 | adversarial | No receipt contains credential or wallet material |
| T-058 | integration | evidenceRef on every receipt resolves to a retrievable trace |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0022-c6-integrate-receipts-and-receipt-evidence-binding-.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C6 — Integrate receipts and receipt-evidence-binding per match and engagement
Epic: E09 Prove — Escrow, Receipts and Attestation | Dependencies (must already be closed): C5, B5

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-055, T-056, T-057, T-058.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
A receipt records that policy, payment reference, and evidence reference existed. It does not prove settlement finality or provider quality.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
