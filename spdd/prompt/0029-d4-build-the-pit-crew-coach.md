# REASONS-LITE — Build the pit-crew coach

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: D4 | Epic: E12 Learning Mode — Replay Telemetry and Pit Crew |
Phase: P3 League and Learning | Lane: SL-D Player Experience_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

One concrete fix per loss is the difference between churn and mastery.

**DoD checklist:**

- [ ] Each loss yields at most one concrete, evidence-grounded suggestion
- [ ] Every suggestion cites a spec section or a trace event
- [ ] Insufficient evidence produces an honest "cannot determine" message

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Losing a match reliably teaches the player something specific and actionable. | phase exit gate: Season completes with reputation derived only from eligible evidence. |
| Dependencies | must be closed first | [D3] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

One concrete fix per loss is the difference between churn and mastery. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: web/, cli/, tutorials/

## O — Operations / Ordered Tasks

1. Derive a single highest-leverage suggestion from the failure mode
2. Cite the governing spec section for each suggestion
3. Suppress coaching when evidence is insufficient rather than guessing

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

**Boundary (what this issue does NOT authorize):** Coaching is advisory. It never edits a player's bot and never guarantees an outcome.

| Test | Type | Asserts |
|---|---|---|
| T-075 | contract | Each loss yields at most one concrete evidence-grounded suggestion |
| T-076 | contract | Insufficient evidence yields an honest cannot-determine message, not a guess |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0029-d4-build-the-pit-crew-coach.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue D4 — Build the pit-crew coach
Epic: E12 Learning Mode — Replay Telemetry and Pit Crew | Dependencies (must already be closed): D3

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-075, T-076.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Coaching is advisory. It never edits a player's bot and never guarantees an outcome.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
