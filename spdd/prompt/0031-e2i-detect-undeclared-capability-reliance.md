# REASONS-LITE — Detect undeclared-capability reliance

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: E2I | Epic: E13 Declaration-Behaviour Binding |
Phase: P1 First Blood | Lane: SL-E Trust, Safety and Anti-Cheat_


## R — Requirements / Definition of Done

The subtler cheat is not declaring a tool but relying on capacity beyond the declared envelope.

**DoD checklist:**

- [x] Declared-versus-actual usage is measured on every match
- [x] Sustained overrun is flagged with the measured delta
- [x] No automatic ban occurs without human review

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | A bot cannot do at runtime what its ADL did not declare. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [E1I], [B4] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The subtler cheat is not declaring a tool but relying on capacity beyond the declared envelope. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/, tests/ (binding, containment)

## O — Operations / Ordered Tasks

1. Compare actual context and output usage against declared requirements
2. Flag sustained overrun beyond the published tolerance
3. Route flagged matches to review rather than auto-banning

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

**Boundary (what this issue does NOT authorize):** Detection flags a discrepancy; adjudication is a separate human-reviewed step.

| Test | Type | Asserts |
|---|---|---|
| T-080 | integration | Declared-versus-actual usage is measured on every match |
| T-081 | contract | Sustained overrun is flagged with the measured delta and routed to review, not auto-ban |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0031-e2i-detect-undeclared-capability-reliance.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue E2I — Detect undeclared-capability reliance
Epic: E13 Declaration-Behaviour Binding | Dependencies (must already be closed): E1I, B4

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-080, T-081.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Detection flags a discrepancy; adjudication is a separate human-reviewed step.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-24 | Artifact staleness (DISCOVER): written before B4/E1I existed. Post-B4, every trace already carries the declared envelope and actual usage (fuelAccounting) plus every lane decision (laneEvents) — so detection became a PURE FUNCTION OVER TRACE EVIDENCE rather than a live monitor: a third party can rerun the audit from the published trace alone. O1's "context and output usage" measures via the ledger (utilization) and lane refusals; "sustained overrun" is signals in ≥ OVERRUN_TOLERANCE (3, published) matches of a series; O3 is structural — the module's only dispositions are no-action / review-required, no ban mechanism exists, and T-081 asserts that by inspecting the module surface. Undeclared-invocation signals cannot yet arise in-engine (the engine invokes only declared tools), so that path is tested by auditing real lane refusal events as trace evidence. | this row | `core/audit.py` (audit_match, flag_sustained, OVERRUN_TOLERANCE, DISPOSITIONS); suite 164→174 (T-080 ×5, T-081 ×5) |
