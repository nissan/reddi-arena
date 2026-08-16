# REASONS-LITE — Integrate offchain-reputation-preview and enforce eligibility rules

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C8 | Epic: E10 Reputation — Commit-Reveal League Table |
Phase: P3 League and Learning | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

The spec is explicit that reputation must not mutate when policy failed or evidence is missing. This is the cleanest thing an analyst can audit.

**DoD checklist:**

- [ ] A match failing policy produces zero reputation change
- [ ] A match with a missing evidence ref produces zero reputation change
- [ ] Every rating change is traceable to a specific eligible receipt

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Standing derives only from verified work, never from listings or payment alone. | phase exit gate: Season completes with reputation derived only from eligible evidence. |
| Dependencies | must be closed first | [C6], [C7] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The spec is explicit that reputation must not mutate when policy failed or evidence is missing. This is the cleanest thing an analyst can audit. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Adopt offchain-reputation-preview as the eligibility evaluator
2. Gate mutation on policy pass, evidence present, attestation pass, payment proof verified
3. Assert every ineligible path leaves standing unchanged
4. Expose the eligibility verdict alongside every rating change

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

**Boundary (what this issue does NOT authorize):** Reputation is a derived signal within one season. It is not portable identity and carries no external warranty.

| Test | Type | Asserts |
|---|---|---|
| T-062 | contract | A match failing policy produces zero reputation change |
| T-063 | contract | A match with a missing evidence reference produces zero reputation change |
| T-064 | integration | Every rating change traces to exactly one eligible receipt |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0024-c8-integrate-offchain-reputation-preview-and-enforc.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C8 — Integrate offchain-reputation-preview and enforce eligibility rules
Epic: E10 Reputation — Commit-Reveal League Table | Dependencies (must already be closed): C6, C7

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-062, T-063, T-064.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Reputation is a derived signal within one season. It is not portable identity and carries no external warranty.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
