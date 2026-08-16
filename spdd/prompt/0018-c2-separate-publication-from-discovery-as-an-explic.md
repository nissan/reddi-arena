# REASONS-LITE — Separate publication from discovery as an explicit gate

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C2 | Epic: E07 Discover — Mercenary Market |
Phase: P2 Mercenary Market | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

The spec is emphatic that publication must never happen accidentally.

**DoD checklist:**

- [ ] No code path publishes without explicit approval
- [ ] Publication events record the approver
- [ ] Export of a listing does not publish it

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Specialists advertise bounded capability with traceable provenance. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [C1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The spec is emphatic that publication must never happen accidentally. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Make publication an explicit operator-approved action
2. Assert no import/export path can publish
3. Log every publication with approver identity

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

**Boundary (what this issue does NOT authorize):** Import, mapping, and export must never publish a live listing.

| Test | Type | Asserts |
|---|---|---|
| T-043 | adversarial | No import, mapping, or export path can publish a live listing |
| T-044 | contract | Every publication event records an explicit approver identity |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0018-c2-separate-publication-from-discovery-as-an-explic.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C2 — Separate publication from discovery as an explicit gate
Epic: E07 Discover — Mercenary Market | Dependencies (must already be closed): C1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-043, T-044.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Import, mapping, and export must never publish a live listing.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
