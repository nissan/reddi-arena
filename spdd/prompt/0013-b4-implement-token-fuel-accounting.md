# REASONS-LITE — Implement token fuel accounting

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: B4 | Epic: E05 Fuel Metering and Trace Emission |
Phase: P1 First Blood | Lane: SL-B Arena Runtime_


## R — Requirements / Definition of Done

Efficiency becomes a skill only if fuel is metered and enforced.

**DoD checklist:**

- [x] Exceeding the declared fuel cap fails the budget gate
- [x] Fuel exhaustion produces a defined outcome, never an exception
- [x] Accounting reconciles exactly with the emitted trace

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Tokens are a scarce in-match resource and every match yields a complete trace. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [B2] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Efficiency becomes a skill only if fuel is metered and enforced. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/arena.py, tools/simulate.py, tests/

## O — Operations / Ordered Tasks

1. Meter prompt and completion tokens per turn against the declared cap
2. Enforce the budget-check eval gate at the declared threshold
3. Define sputter behaviour when fuel is exhausted mid-turn

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

**Boundary (what this issue does NOT authorize):** Fuel accounting is deterministic bookkeeping, not billing.

| Test | Type | Asserts |
|---|---|---|
| T-029 | unit | Exceeding the declared fuel cap fails the budget-check gate |
| T-030 | integration | Fuel exhaustion mid-turn produces the defined sputter outcome, never an exception |
| T-031 | property | Fuel accounting reconciles exactly with the emitted trace for every match |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0013-b4-implement-token-fuel-accounting.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue B4 — Implement token fuel accounting
Epic: E05 Fuel Metering and Trace Emission | Dependencies (must already be closed): B2

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-029, T-030, T-031.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Fuel accounting is deterministic bookkeeping, not billing.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-24 | Artifact staleness (DISCOVER): the flat 60-token turn cost, contextWindow-derived cap, and sputter path already shipped with the preview; B2 made sputter a lifecycle forfeit. Node scope: make the bookkeeping first-class without changing outcomes — the 60-token turn is now itemized (prompt 40 + completion 20) through a meter that is the only component charging fuel; O1's "prompt and completion tokens" are deterministic reference values, not provider meters (determinism boundary; B3's effective-fuel channel supplies provider caps). O2's budget gate runs pre-turn at the DECLARED thresholds (completion vs maxOutputTokens, full turn vs cap) and fails as a defined forfeit/void. O3's mid-turn sputter is now reachable and defined: prompt charged, completion never happens, partial turn in the ledger. Balance unchanged (same trigger points; suite's balance-regression section green, no BALANCE-REPORT regen). tools/simulate.py untouched — nothing there reads fuel internals. | this row | `core/fuel.py` (FuelMeter, budget_gate, cost constants); `core/arena.py` charges only via meters, gate branch at binding, trace gains hash-covered `fuelAccounting`; suite 153→164 (T-029 ×5, T-030 ×4, T-031 ×2) |
