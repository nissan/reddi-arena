# REASONS-LITE — Implement the turn loop and match lifecycle

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: B2 | Epic: E04 Match Engine and Bounded Execution |
Phase: P1 First Blood | Lane: SL-B Arena Runtime_


## R — Requirements / Definition of Done

Deterministic lifecycle is the precondition for replayable evidence.

**DoD checklist:**

- [x] Every match terminates in a defined terminal state
- [x] A crashed or hung competitor forfeits rather than hanging the match
- [x] Illegal state transitions are impossible, not merely discouraged

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Two ADL-defined bots run a complete match inside a fail-closed sandbox. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [B1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Deterministic lifecycle is the precondition for replayable evidence. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/arena.py, tools/simulate.py, tests/

## O — Operations / Ordered Tasks

1. Define match states and legal transitions
2. Enforce turn limits and per-turn timeouts from the declared harness
3. Handle competitor crash, timeout, and malformed output as defined outcomes

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

**Boundary (what this issue does NOT authorize):** Lifecycle events are evidence, not adjudication.

| Test | Type | Asserts |
|---|---|---|
| T-023 | property | Every match reaches exactly one defined terminal state |
| T-024 | integration | Crashed or hung competitors forfeit without hanging the match |
| T-025 | property | Illegal lifecycle transitions are unreachable |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0011-b2-implement-the-turn-loop-and-match-lifecycle.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue B2 — Implement the turn loop and match lifecycle
Epic: E04 Match Engine and Bounded Execution | Dependencies (must already be closed): B1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-023, T-024, T-025.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Lifecycle events are evidence, not adjudication.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-23 | Artifact staleness (DISCOVER): written before the engine existed. The turn loop, turn limit, and fuel model (O1/O2's substrate) already shipped with the playable preview; the deterministic engine cannot literally crash or hang, so O3's fault classes map to their deterministic analogues: a declaration the engine cannot read (crash) and one outside ARENA-PROFILE-v0.1's declared 0-100 strategy domain (runaway/hang). Node scope became: make the implicit lifecycle explicit and structurally closed. | this row | `core/lifecycle.py` (states/LEGAL/`advance()` raising `IllegalTransition`; terminal states absorbing); `core/arena.py` walks scheduled→weighing→binding→(in-progress→)terminal, fault-checked `_read_strategy`/`_read_fuel` resolve faults as pre-turn forfeit/void at binding, trace gains hash-covered `lifecycle`; suite 125→138 (T-023 ×3, T-024 ×5, T-025 ×5) |
