# REASONS-LITE — Integrate buyer-authority-policy as the hire decision engine

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C3 | Epic: E08 Decide — Buyer Policy and the Draft Broker |
Phase: P2 Mercenary Market | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

Decide is the layer players most often skip conceptually, so the game must make it unavoidable and visible.

**DoD checklist:**

- [ ] Every hire attempt yields a recorded decision with reason codes
- [ ] A mandate attempting to widen local authority is rejected
- [ ] Exceeding the declared purse budget denies the hire

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Hiring is a bounded policy decision under budget, trust, and authority constraints, resolved before the match starts. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [C1], [A5] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Decide is the layer players most often skip conceptually, so the game must make it unavoidable and visible. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Adopt buyer-authority-policy from @reddi/agent-protocol as the decision core
2. Evaluate trust class, budget ceiling, rail, and approval posture
3. Emit a machine-readable decision with reason codes for allow and deny
4. Assert an external mandate can narrow but never widen local authority

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

**Boundary (what this issue does NOT authorize):** An allow decision permits a bounded engagement only. It never widens buyer authority beyond the operator-declared envelope.

| Test | Type | Asserts |
|---|---|---|
| T-045 | contract | Every hire attempt produces a machine-readable decision with reason codes |
| T-046 | adversarial | An external mandate attempting to widen local buyer authority is rejected |
| T-047 | unit | A hire exceeding the declared purse budget is denied |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0019-c3-integrate-buyer-authority-policy-as-the-hire-dec.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C3 — Integrate buyer-authority-policy as the hire decision engine
Epic: E08 Decide — Buyer Policy and the Draft Broker | Dependencies (must already be closed): C1, A5

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-045, T-046, T-047.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
An allow decision permits a bounded engagement only. It never widens buyer authority beyond the operator-declared envelope.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
