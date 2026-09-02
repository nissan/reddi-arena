# REASONS-LITE — Implement commit-reveal scoring

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C9 | Epic: E10 Reputation — Commit-Reveal League Table |
Phase: P3 League and Learning | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

Rivals scoring rivals invites retaliation and copying; commit-reveal is the spec's answer and the arena is a natural stress test.

**DoD checklist:**

- [ ] No score is visible before the reveal window opens
- [ ] A non-revealed commit is penalised per published rule
- [ ] A reveal not matching its commit hash is rejected

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Standing derives only from verified work, never from listings or payment alone. | phase exit gate: Season completes with reputation derived only from eligible evidence. |
| Dependencies | must be closed first | [C8] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Rivals scoring rivals invites retaliation and copying; commit-reveal is the spec's answer and the arena is a natural stress test. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Commit score hashes before any reveal
2. Enforce the reveal deadline and penalise non-reveal
3. Detect copied scores and late-reveal advantage

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

**Boundary (what this issue does NOT authorize):** Off-chain commit-reveal only in P3. On-chain projection is E15.

| Test | Type | Asserts |
|---|---|---|
| T-065 | adversarial | No score is readable before the reveal window opens |
| T-066 | contract | A non-revealed commit is penalised per the published rule |
| T-067 | contract | A reveal not matching its commit hash is rejected |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0025-c9-implement-commit-reveal-scoring.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C9 — Implement commit-reveal scoring
Epic: E10 Reputation — Commit-Reveal League Table | Dependencies (must already be closed): C8

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-065, T-066, T-067.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Off-chain commit-reveal only in P3. On-chain projection is E15.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
