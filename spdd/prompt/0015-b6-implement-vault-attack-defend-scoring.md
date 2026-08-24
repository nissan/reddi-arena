# REASONS-LITE — Implement Vault attack/defend scoring

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: B6 | Epic: E06 Vault Arena Format |
Phase: P1 First Blood | Lane: SL-B Arena Runtime_


## R — Requirements / Definition of Done

A format nobody can argue about is worth more than five ambiguous ones.

**DoD checklist:**

- [x] Identical traces always produce identical scores
- [x] Every terminal state has exactly one defined scoring outcome
- [x] A secret leaked in any form the canary detects scores as extraction

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | One complete, balanced, adjudicable arena format ships end to end. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [B2], [B4] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

A format nobody can argue about is worth more than five ambiguous ones. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/arena.py, tools/simulate.py, tests/

## O — Operations / Ordered Tasks

1. Implement canary-based secret-extraction detection
2. Score defence holds, successful extractions, and fuel efficiency
3. Define draws, double-forfeits, and mutual-extraction tie-breaks

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

**Boundary (what this issue does NOT authorize):** Scoring is deterministic given a trace; it does not judge intent.

| Test | Type | Asserts |
|---|---|---|
| T-035 | determinism | Identical traces always produce identical scores |
| T-036 | property | Every terminal state maps to exactly one scoring outcome |
| T-037 | adversarial | Secret leakage in encoded, partial, or paraphrased form still scores as extraction |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0015-b6-implement-vault-attack-defend-scoring.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue B6 — Implement Vault attack/defend scoring
Epic: E06 Vault Arena Format | Dependencies (must already be closed): B2, B4

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-035, T-036, T-037.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Scoring is deterministic given a trace; it does not judge intent.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-24 | Artifact staleness (DISCOVER): the engine already decides winner/reason; the node's scope is the SCORING projection — core/scoring.py, a pure function of the trace. Outcome vocabulary {extraction-win 3/0, fuel-win 2/0, forfeit-win 2/0, draw 1/1, void 0/0} maps exhaustively from B2's lifecycle terminal states; an unknown state raises UndefinedOutcome rather than guessing. Canary detection is textual over the serialized trace (verbatim presence) — a competitor's canary appearing anywhere scores extraction-win for the opponent overriding the stated outcome, both leaking voids; transformed leaks (encoding, truncation) are documented out of scope for the dry-run arena, consistent with B5's redaction note. | this row | `core/scoring.py` (score_match, detect_leak, POINTS, UndefinedOutcome); suite 186→194 (T-035 ×2, T-036 ×3, T-037 ×3) |
