# REASONS-LITE — Enforce claims discipline across all public Arena surfaces

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: F4 | Epic: E16 Lab Feedback Loop and Claims Discipline |
Phase: P0 Foundry | Lane: SL-F Release Ops and Evidence_


## R — Requirements / Definition of Done

The 2026-08-01 operational correction exists because planning was being reported as implementation. A public game multiplies that risk.

**DoD checklist:**

- [ ] No public surface claims audit completion or mainnet readiness
- [ ] Every capability claim links to a passing test or a published artifact
- [ ] A closed planning issue is never rendered as a shipped capability

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Arena findings reach the lab as evidence, and no Arena surface overstates maturity. | phase exit gate: All P0 tests green; ADL fixtures validate against published schema. |
| Dependencies | must be closed first | [F3] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The 2026-08-01 operational correction exists because planning was being reported as implementation. A public game multiplies that risk. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: docs/, findings/, .github/

## O — Operations / Ordered Tasks

1. Ban the words implying audit, mainnet, or production readiness in copy
2. Require every capability claim to cite a passing test or artifact
3. Add a release-state banner reflecting actual gate status

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

**Boundary (what this issue does NOT authorize):** This issue governs what Arena says about itself. It creates no technical capability.

| Test | Type | Asserts |
|---|---|---|
| T-094 | contract | No public surface claims audit completion, mainnet readiness, or production status |
| T-095 | contract | Every capability claim links to a passing test or published artifact |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0037-f4-enforce-claims-discipline-across-all-public-aren.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue F4 — Enforce claims discipline across all public Arena surfaces
Epic: E16 Lab Feedback Loop and Claims Discipline | Dependencies (must already be closed): F3

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-094, T-095.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
This issue governs what Arena says about itself. It creates no technical capability.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
