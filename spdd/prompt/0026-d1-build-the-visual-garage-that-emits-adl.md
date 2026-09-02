# REASONS-LITE — Build the visual garage that emits ADL

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: D1 | Epic: E11 Garage and Progressive Disclosure |
Phase: P2 Mercenary Market | Lane: SL-D Player Experience_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

The garage is the on-ramp; if it emits anything other than canonical ADL, the whole proof is undermined.

**DoD checklist:**

- [ ] Every reachable garage state emits a schema-valid document
- [ ] Weight updates live and matches the CLI calculator exactly
- [ ] Errors name the offending field and link to the governing spec section

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | A newcomer assembles a valid bot without reading the spec; an expert hand- writes ADL. Both produce the same artifact. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [A1], [A4] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The garage is the on-ramp; if it emits anything other than canonical ADL, the whole proof is undermined. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: web/, cli/, tutorials/

## O — Operations / Ordered Tasks

1. Emit schema-valid ADL from every UI state
2. Show live AU weight and class as the player builds
3. Surface validation errors in plain language with a spec link

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

**Boundary (what this issue does NOT authorize):** The garage authors documents. It never executes or publishes them.

| Test | Type | Asserts |
|---|---|---|
| T-068 | property | Every reachable garage state emits a schema-valid ADL document |
| T-069 | integration | Garage-displayed AU matches the CLI calculator exactly |
| T-070 | contract | Validation errors name the offending field and link a spec section |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0026-d1-build-the-visual-garage-that-emits-adl.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue D1 — Build the visual garage that emits ADL
Epic: E11 Garage and Progressive Disclosure | Dependencies (must already be closed): A1, A4

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-068, T-069, T-070.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
The garage authors documents. It never executes or publishes them.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
