# REASONS-LITE — Specify and freeze the AU weight formula v0.1

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: A4 | Epic: E02 Deterministic Weigh-In and Capability Hash |
Phase: P0 Foundry | Lane: SL-A Spec and Conformance_


## R — Requirements / Definition of Done

If weight is not deterministic and independently recomputable, the whole competitive frame collapses.

**DoD checklist:**

- [x] Same document yields identical AU and hash across runs, machines, and key order
- [x] Certificate records weightsVersion so old results stay interpretable
- [x] Reordering YAML keys does not change the hash

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Weight class is a reproducible pure function of a validated ADL document. | phase exit gate: All P0 tests green; ADL fixtures validate against published schema. |
| Dependencies | must be closed first | [A1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

If weight is not deterministic and independently recomputable, the whole competitive frame collapses. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: adl/, vendor/, tools/validate_adl.py, fixtures/

## O — Operations / Ordered Tasks

1. Publish the AU table and class bands as a versioned spec document
2. Implement the calculator as a pure function with no IO, clock, or randomness
3. Emit a capability hash over the canonicalised certificate
4. Version the formula so historical certificates remain interpretable

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

**Boundary (what this issue does NOT authorize):** A weight certificate authorizes nothing; it is an eligibility input only.

| Test | Type | Asserts |
|---|---|---|
| T-007 | determinism | Identical AU and capability hash across repeated runs |
| T-008 | property | YAML key reordering and whitespace changes never alter the capability hash |
| T-009 | unit | Reference bot weighs exactly 62 AU; mercenary exactly 91 AU |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0005-a4-specify-and-freeze-the-au-weight-formula-v0-1.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue A4 — Specify and freeze the AU weight formula v0.1
Epic: E02 Deterministic Weigh-In and Capability Hash | Dependencies (must already be closed): A1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-007, T-008, T-009.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
A weight certificate authorizes nothing; it is an eligibility input only.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-16 | O-tasks 1–4 were already implemented (docs/WEIGHT-CLASS-v0.1.md, tools/weigh_in.py: pure `weigh()`, `capabilityHash`, `weightsVersion=arena-weights-v0.1`) but unfrozen and untested against T-007/8/9. Node work = the freeze itself + the doneness tests, not new formula code. | DoD checked; this row | tests/test_arena.py: 8 new checks (T-007 ×2, T-008 ×2, T-009 ×2, freeze assertions ×2), suite 55→63; spec status draft→frozen with v0.2 change path. Executed as graph node A4 (branch node/A4-freeze-au-weight-formula) under the GE01 pilot. |
