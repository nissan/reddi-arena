# REASONS-LITE — Render the annotated match replay

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: D3 | Epic: E12 Learning Mode — Replay Telemetry and Pit Crew |
Phase: P3 League and Learning | Lane: SL-D Player Experience_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

The replay is where a receipt and a trace become a learning experience instead of a compliance artifact.

**DoD checklist:**

- [ ] Every rendered claim maps to a specific trace event
- [ ] No replay statement is unsupported by evidence
- [ ] Disclosure rules are enforced per season configuration

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Losing a match reliably teaches the player something specific and actionable. | phase exit gate: Season completes with reputation derived only from eligible evidence. |
| Dependencies | must be closed first | [B5], [B6] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The replay is where a receipt and a trace become a learning experience instead of a compliance artifact. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: web/, cli/, tutorials/

## O — Operations / Ordered Tasks

1. Render turn-by-turn fuel burn, tool calls, and gate outcomes
2. Highlight the decisive moment that determined the result
3. Show the opponent's approach only within the season's disclosure rules

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

**Boundary (what this issue does NOT authorize):** The replay renders recorded evidence. It never reconstructs, infers, or embellishes what was not traced.

| Test | Type | Asserts |
|---|---|---|
| T-073 | contract | Every rendered replay claim maps to a specific trace event |
| T-074 | contract | Season disclosure rules are enforced in the replay renderer |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0028-d3-render-the-annotated-match-replay.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue D3 — Render the annotated match replay
Epic: E12 Learning Mode — Replay Telemetry and Pit Crew | Dependencies (must already be closed): B5, B6

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-073, T-074.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
The replay renders recorded evidence. It never reconstructs, infers, or embellishes what was not traced.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
