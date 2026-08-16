# REASONS-LITE — Round-trip fidelity between visual and raw editing

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: D2 | Epic: E11 Garage and Progressive Disclosure |
Phase: P2 Mercenary Market | Lane: SL-D Player Experience_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

Experts will not adopt a tool that mangles their handwritten documents.

**DoD checklist:**

- [ ] Import then export is semantically lossless
- [ ] Any UI-unsupported field is reported, never silently dropped
- [ ] Comments and ordering loss is disclosed to the player

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | A newcomer assembles a valid bot without reading the spec; an expert hand- writes ADL. Both produce the same artifact. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [D1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Experts will not adopt a tool that mangles their handwritten documents. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: web/, cli/, tutorials/

## O — Operations / Ordered Tasks

1. Import a handwritten ADL into the visual editor without semantic loss
2. Export and diff to confirm no silent field drops
3. Report unsupported-in-UI semantics explicitly rather than discarding

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

**Boundary (what this issue does NOT authorize):** Round-tripping preserves semantics; it does not validate intent.

| Test | Type | Asserts |
|---|---|---|
| T-071 | property | Import then export is semantically lossless |
| T-072 | contract | UI-unsupported fields are reported explicitly, never silently dropped |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0027-d2-round-trip-fidelity-between-visual-and-raw-editi.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue D2 — Round-trip fidelity between visual and raw editing
Epic: E11 Garage and Progressive Disclosure | Dependencies (must already be closed): D1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-071, T-072.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Round-tripping preserves semantics; it does not validate intent.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
