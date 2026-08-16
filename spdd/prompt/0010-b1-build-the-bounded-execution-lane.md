# REASONS-LITE — Build the bounded execution lane

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: B1 | Epic: E04 Match Engine and Bounded Execution |
Phase: P1 First Blood | Lane: SL-B Arena Runtime_


## R — Requirements / Definition of Done

Execution is the one place the declaration becomes action, so it is the one place fail-closed must be provably enforced.

**DoD checklist:**

- [ ] A tool absent from the ADL cannot be invoked
- [ ] A tool present but lacking a matching policyRef cannot be invoked
- [ ] Network egress with an empty allowlist is refused and logged
- [ ] Every refusal emits an event with subject, resource, action, and reason

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Two ADL-defined bots run a complete match inside a fail-closed sandbox. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [A1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Execution is the one place the declaration becomes action, so it is the one place fail-closed must be provably enforced. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/arena.py, tools/simulate.py, tests/

## O — Operations / Ordered Tasks

1. Implement a runtime binder that refuses any undeclared capability
2. Default network egress to deny; require explicit allowlist entries
3. Refuse persistent/external memory backends unless separately approved
4. Emit a structured refusal event for every blocked attempt

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

**Boundary (what this issue does NOT authorize):** The lane is the ONLY component permitted to execute, and only for declared, policy-matched, locally-bound capabilities.

| Test | Type | Asserts |
|---|---|---|
| T-019 | adversarial | An undeclared tool cannot be invoked at runtime |
| T-020 | adversarial | A declared tool lacking a matching policyRef cannot be invoked |
| T-021 | integration | Egress with an empty allowlist is refused and logged |
| T-022 | contract | Every refusal emits an event carrying subject, resource, action and reason |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0010-b1-build-the-bounded-execution-lane.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue B1 — Build the bounded execution lane
Epic: E04 Match Engine and Bounded Execution | Dependencies (must already be closed): A1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-019, T-020, T-021, T-022.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
The lane is the ONLY component permitted to execute, and only for declared, policy-matched, locally-bound capabilities.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
