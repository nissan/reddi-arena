# REASONS-LITE — Integrate discovery-source into the specialist listing surface

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: C1 | Epic: E07 Discover — Mercenary Market |
Phase: P2 Mercenary Market | Lane: SL-C RAP Economy_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

Discovery is where players first meet RAP's "relevance is not trust" rule.

**DoD checklist:**

- [ ] A listing cannot claim a capability absent from its ADL
- [ ] Provenance is displayed for every listing
- [ ] Discovery never triggers invocation or publication as a side effect

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Specialists advertise bounded capability with traceable provenance. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [A1], [A4] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Discovery is where players first meet RAP's "relevance is not trust" rule. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)

## O — Operations / Ordered Tasks

1. Adopt discovery-source and ranking-explainability rather than reimplementing
2. Render the relevance_only_not_trust vocabulary directly from the package
3. Derive listings from validated ADL, never from free-text claims
4. Record and display the provenance of every listing
5. Show reputation state including "insufficient evidence"

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

**Boundary (what this issue does NOT authorize):** A listing is a claim, not verified truth. Discovery grants no invocation permission and no publication.

| Test | Type | Asserts |
|---|---|---|
| T-040 | contract | A listing cannot advertise a capability absent from its ADL |
| T-041 | contract | Provenance is present and displayed for every listing |
| T-042 | adversarial | No discovery call triggers invocation or publication as a side effect |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0017-c1-integrate-discovery-source-into-the-specialist-l.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue C1 — Integrate discovery-source into the specialist listing surface
Epic: E07 Discover — Mercenary Market | Dependencies (must already be closed): A1, A4

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-040, T-041, T-042.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
A listing is a claim, not verified truth. Discovery grants no invocation permission and no publication.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
