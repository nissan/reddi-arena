# REASONS-LITE — Guard the known v0.2 charge-intent conformance gap

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: A8 | Epic: E03 Conformance-to-League Mapping |
Phase: P1 First Blood | Lane: SL-A Spec and Conformance_


## R — Requirements / Definition of Done

The lab records that charge intents can escape intended Level-3 enforcement. Arena must not inherit that hole.

**DoD checklist:**

- [ ] An under-constrained charge intent is refused at draft with a stated reason
- [ ] The guard is documented as compensating, not as a spec fix
- [ ] An upstream issue exists with a minimal reproduction

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | ADL conformance levels gate league entry, so players climb the spec ladder by playing. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [A7] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The lab records that charge intents can escape intended Level-3 enforcement. Arena must not inherit that hole. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: adl/, vendor/, tools/validate_adl.py, fixtures/

## O — Operations / Ordered Tasks

1. Enumerate intent shapes that escape Level-3 enforcement
2. Add an Arena-side pre-draft check refusing under-constrained charge intents
3. File the reproduction upstream as a v0.3 candidate

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

**Boundary (what this issue does NOT authorize):** The guard is Arena-local compensating control. It does not fix the spec and must not be described as fixing it.

| Test | Type | Asserts |
|---|---|---|
| T-017 | adversarial | An under-constrained charge intent is refused at pre-draft check |
| T-018 | contract | The charge-intent guard is documented as compensating, never as a spec fix |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0009-a8-guard-the-known-v0-2-charge-intent-conformance-g.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue A8 — Guard the known v0.2 charge-intent conformance gap
Epic: E03 Conformance-to-League Mapping | Dependencies (must already be closed): A7

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-017, T-018.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
The guard is Arena-local compensating control. It does not fix the spec and must not be described as fixing it.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
