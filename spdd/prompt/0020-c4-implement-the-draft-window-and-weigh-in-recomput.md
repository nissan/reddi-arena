# REASONS-LITE — Implement the draft window and weigh-in recomputation

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C4 | Epic: E08 Decide — Buyer Policy and the Draft Broker |
Phase: P2 Mercenary Market | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

The hire-versus-class tradeoff is the strategic heart of the game and must resolve deterministically before combat.

**DoD checklist:**

- [ ] Fielded weight is recomputed and shown before the hire is committed
- [ ] A class-breaching hire is refused before the match, never mid-match
- [ ] The draft window closes deterministically and cannot be reopened

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Hiring is a bounded policy decision under budget, trust, and authority constraints, resolved before the match starts. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [C3], [A5] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The hire-versus-class tradeoff is the strategic heart of the game and must resolve deterministically before combat. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Open a bounded draft window with a hard close
2. Recompute fielded weight on every hire and re-check class eligibility
3. Refuse hires that would breach the entered class, with the AU delta shown

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

**Boundary (what this issue does NOT authorize):** Draft outcomes bind eligibility only; no work or payment occurs at draft.

| Test | Type | Asserts |
|---|---|---|
| T-048 | integration | Fielded weight is recomputed and surfaced before a hire commits |
| T-049 | property | No hire can take effect after the draft window closes |
| T-050 | adversarial | The draft window cannot be reopened by any request path |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0020-c4-implement-the-draft-window-and-weigh-in-recomput.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C4 — Implement the draft window and weigh-in recomputation
Epic: E08 Decide — Buyer Policy and the Draft Broker | Dependencies (must already be closed): C3, A5

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-048, T-049, T-050.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Draft outcomes bind eligibility only; no work or payment occurs at draft.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
