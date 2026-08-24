# REASONS-LITE — Emit conformance-aligned trace events with redaction

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: B5 | Epic: E05 Fuel Metering and Trace Emission |
Phase: P1 First Blood | Lane: SL-B Arena Runtime_


## R — Requirements / Definition of Done

The trace is the evidence substrate for receipts, learning mode, and disputes.

**DoD checklist:**

- [x] Every match emits a complete, ordered, replayable event stream
- [x] Redaction rules from the ADL are applied, not defaults
- [x] No credential or canary value appears anywhere in a stored trace

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Tokens are a scarce in-match resource and every match yields a complete trace. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [B2] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The trace is the evidence substrate for receipts, learning mode, and disputes. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/arena.py, tools/simulate.py, tests/

## O — Operations / Ordered Tasks

1. Emit the declared observability event set for every match
2. Apply declared redaction to prompt and output payloads
3. Assert no secret, key, or canary value can reach the trace

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

**Boundary (what this issue does NOT authorize):** A trace records what happened. It does not by itself establish task success or reputation eligibility.

| Test | Type | Asserts |
|---|---|---|
| T-032 | contract | Every match emits a complete ordered replayable event stream |
| T-033 | contract | ADL-declared redaction rules are applied rather than engine defaults |
| T-034 | adversarial | No credential or canary value appears in any stored trace |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0014-b5-emit-conformance-aligned-trace-events-with-redac.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue B5 — Emit conformance-aligned trace events with redaction
Epic: E05 Fuel Metering and Trace Emission | Dependencies (must already be closed): B2

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-032, T-033, T-034.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
A trace records what happened. It does not by itself establish task success or reputation eligibility.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-24 | Artifact staleness (DISCOVER): the trace itself (hash-covered, with lifecycle/laneEvents/fuelAccounting) predates this node; what was missing was the DECLARED vocabulary. Emission is a pure projection of the trace into the ADL-declared observability event set (core/emit.py), with an explicit completeness accounting — a fast match where the loser never invoked a tool honestly reports tool.called missing rather than pretending. task.completed/task.failed are treated as alternatives (both declared required, exactly one occurs per completion) — worth a spec finding if this recurs upstream. No real secrets flow through the deterministic engine, so the redaction guarantee is: any payload routed through the emitter is redacted per the document's OWN declared rules (engine has no default list), two-level (declared fields masked wherever nested, then every value seen under a declared field scrubbed from all strings), and a document with no declared rules gets its payload withheld entirely — fail closed. tools/simulate.py untouched. | this row | `core/emit.py` (emit_events, redact_payload, declared_redaction, stream_contains); suite 174→186 (T-032 ×5, T-033 ×4, T-034 ×3) |
