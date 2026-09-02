# REASONS-LITE — Establish the one-way canonicality workflow

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: F3 | Epic: E16 Lab Feedback Loop and Claims Discipline |
Phase: P0 Foundry | Lane: SL-F Release Ops and Evidence_


## R — Requirements / Definition of Done

The binding rule is that spec flows down and findings flow up. A proof project is exactly where that discipline erodes first.

**DoD checklist:**

- [x] CI fails if a vendored ADL schema diverges from the pinned upstream hash
- [x] Every finding has an upstream reference and a disposition
- [x] No Arena document redefines an ADL semantic

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Arena findings reach the lab as evidence, and no Arena surface overstates maturity. | phase exit gate: All P0 tests green; ADL fixtures validate against published schema. |
| Dependencies | must be closed first | [A1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The binding rule is that spec flows down and findings flow up. A proof project is exactly where that discipline erodes first. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: docs/, findings/, .github/

## O — Operations / Ordered Tasks

1. Route every finding through the public feedback intake
2. Forbid Arena-local ADL forks in CI
3. Track which findings the lab accepted, rejected, or deferred

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

**Boundary (what this issue does NOT authorize):** Arena may propose. Only the lab may make an ADL semantic canonical.

| Test | Type | Asserts |
|---|---|---|
| T-092 | determinism | CI fails if the vendored ADL schema diverges from the pinned upstream hash |
| T-093 | contract | No Arena document redefines an ADL semantic; every finding has an upstream reference |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0036-f3-establish-the-one-way-canonicality-workflow.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue F3 — Establish the one-way canonicality workflow
Epic: E16 Lab Feedback Loop and Claims Discipline | Dependencies (must already be closed): A1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-092, T-093.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Arena may propose. Only the lab may make an ADL semantic canonical.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-16 | Workflow was already being exercised (F-007/F-002/F-001 filed earlier today) but was undocumented and unenforced. This node formalizes it: disposition register in docs/FINDINGS.md covering all eleven findings (F-003, F-005, F-010, F-011 newly filed as lab#445/#446/#443/#444; F-008 recorded as duplicate of lab v0.3 candidate #3), T-092 hash-drift check asserted in-suite, T-093 register-completeness + no-ADL-fork lint, and a real CI gate (.github/workflows/tests.yml) running all three verification commands on push/PR. T-093 immediately caught a real omission during implementation: F-008 had no register row. | DoD checked; this row | tests/test_arena.py +4 checks (suite 68→72); .github/workflows/tests.yml added. Executed as graph node F3 (branch node/F3-one-way-canonicality) under the GE01 pilot. |
