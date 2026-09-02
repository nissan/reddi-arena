# REASONS-LITE — Enforce runtime binding against the weighed declaration

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: E1I | Epic: E13 Declaration-Behaviour Binding |
Phase: P1 First Blood | Lane: SL-E Trust, Safety and Anti-Cheat_


## R — Requirements / Definition of Done

This single control is what makes weight class meaningful and makes ADL a contract rather than documentation.

**DoD checklist:**

- [x] A capability absent from the weighed hash cannot execute
- [x] An escape attempt forfeits the match with recorded evidence
- [x] The bound hash on the trace matches the weigh-in certificate exactly

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | A bot cannot do at runtime what its ADL did not declare. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [B1], [A4] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

This single control is what makes weight class meaningful and makes ADL a contract rather than documentation. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/, tests/ (binding, containment)

## O — Operations / Ordered Tasks

1. Bind the runtime to the exact capability hash weighed in
2. Refuse any capability outside the bound declaration
3. Forfeit the match on an attempted escape and record the evidence

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

**Boundary (what this issue does NOT authorize):** Binding enforces the declaration. It does not evaluate whether the declaration was wise.

| Test | Type | Asserts |
|---|---|---|
| T-077 | adversarial | A capability absent from the weighed hash cannot execute |
| T-078 | integration | An escape attempt forfeits the match and records evidence |
| T-079 | determinism | The bound hash on every trace matches its weigh-in certificate |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0030-e1i-enforce-runtime-binding-against-the-weighed-decl.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue E1I — Enforce runtime binding against the weighed declaration
Epic: E13 Declaration-Behaviour Binding | Dependencies (must already be closed): B1, A4

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-077, T-078, T-079.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Binding enforces the declaration. It does not evaluate whether the declaration was wise.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-21 | Built directly on B1: ExecutionLane gains bound_hash/live_hash construction — a mismatch marks the lane escaped, emits a binding refusal event, and every subsequent invocation (including honestly-declared tools) is refused fail-closed. run_vault_match accepts draft certificates (cert_a/cert_b; self-weighs when absent), forfeits the escaping bot BEFORE any turn runs with the refusal recorded as trace evidence, voids the match as a draw when both escape, and stamps trace.boundHash per bot (auditable against weigh-in certificates). This also completes T-014's runtime half from A6 (capability hidden post-weigh cannot execute). Note: baseline suite grew 101→109 mid-node from PR #48 (waitlist endpoints, merged without a graph node — classified as maintenance, flagged in retro). | DoD checked; this row | core/lane.py binding checks; core/arena.py cert params + forfeit path + boundHash; tests +8 (T-077 ×3, T-078 ×4, T-079 ×1), suite 109→117. Executed as graph node E1I (branch node/E1I-runtime-binding). |
