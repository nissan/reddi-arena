# REASONS-LITE — Implement coupled weight for hired specialists

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: A5 | Epic: E02 Deterministic Weigh-In and Capability Hash |
Phase: P0 Foundry | Lane: SL-A Spec and Conformance_


## R — Requirements / Definition of Done

The class-bump-on-hire tradeoff is the core strategic mechanic and must be computed identically by every implementation.

**DoD checklist:**

- [x] Hiring a specialist increases fielded AU and can change fielded class
- [x] A hire that would exceed the entered class is rejected at draft, not mid-match
- [x] Transitive hire depth beyond the cap is refused with a stated reason

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Weight class is a reproducible pure function of a validated ADL document. | phase exit gate: All P0 tests green; ADL fixtures validate against published schema. |
| Dependencies | must be closed first | [A4] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The class-bump-on-hire tradeoff is the core strategic mechanic and must be computed identically by every implementation. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: adl/, vendor/, tools/validate_adl.py, fixtures/

## O — Operations / Ordered Tasks

1. Apply the coupling factor and per-engagement overhead
2. Recompute fielded class and flag classBumped
3. Handle transitive hires (a specialist that itself hires) with a depth cap

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

**Boundary (what this issue does NOT authorize):** Computing coupled weight does not engage a specialist or move value.

| Test | Type | Asserts |
|---|---|---|
| T-010 | unit | Hiring the reference mercenary moves the reference bot 62 to 127 AU, Antweight to Beetleweight |
| T-011 | integration | A hire breaching the entered class is refused at draft with the AU delta stated |
| T-012 | property | Transitive hire depth beyond the cap is refused; no unbounded recursion |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0006-a5-implement-coupled-weight-for-hired-specialists.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue A5 — Implement coupled weight for hired specialists
Epic: E02 Deterministic Weigh-In and Capability Hash | Dependencies (must already be closed): A4

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-010, T-011, T-012.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Computing coupled weight does not engage a specialist or move value.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-17 | DISCOVER staleness: mostly built. Coupled weight (ceil(0.6·AU)+10), class-bump computation, and draft refusal with AU delta all existed and were partially tested. The genuine gap was T-012: no transitive-hire-depth concept anywhere. Added HIRE_DEPTH_CAP=1 + evaluate_hire_chain (cap checked before any weighing — O(1) refusal for chains of any length) as a DRAFT rule, deliberately outside the frozen AU formula; spec gains a "Hire depth (draft rule)" section noting that raising the cap is a v0.2 formula-spec question (coupled weight would need a composition rule). | DoD checked; this row | core/arena.py: evaluate_hire_chain + HIRE_DEPTH_CAP; docs/WEIGHT-CLASS-v0.1.md draft-rule section; tests +6 (T-010 ×2, T-011, T-012 ×3), suite 77→83. Executed as graph node A5 (branch node/A5-coupled-weight). |
