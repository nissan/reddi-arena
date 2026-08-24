# REASONS-LITE — Provider abstraction across declared model providers

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: B3 | Epic: E04 Match Engine and Bounded Execution |
Phase: P1 First Blood | Lane: SL-B Arena Runtime_


## R — Requirements / Definition of Done

Provider neutrality is an ADL promise; the Arena is where it either holds or visibly breaks.

**DoD checklist:**

- [x] Undeclared fallbacks are never used
- [x] A provider missing structuredOutput reports degraded, not silent success
- [x] Cross-provider divergence is measured and published, not hidden

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Two ADL-defined bots run a complete match inside a fail-closed sandbox. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [B1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Provider neutrality is an ADL promise; the Arena is where it either holds or visibly breaks. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/arena.py, tools/simulate.py, tests/

## O — Operations / Ordered Tasks

1. Honour the declared preference order without inventing fallbacks
2. Report degraded semantics when a provider lacks a declared requirement
3. Run the same bot across at least two providers and diff behaviour

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

**Boundary (what this issue does NOT authorize):** Declaring a provider is not credential authorization. Missing credentials fail closed rather than silently falling back.

| Test | Type | Asserts |
|---|---|---|
| T-026 | contract | Undeclared fallback providers are never selected |
| T-027 | contract | A provider missing a declared requirement reports degraded rather than succeeding silently |
| T-028 | e2e | Cross-provider behavioural divergence is measured and published |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0012-b3-provider-abstraction-across-declared-model-provi.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue B3 — Provider abstraction across declared model providers
Epic: E04 Match Engine and Bounded Execution | Dependencies (must already be closed): B1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-026, T-027, T-028.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Declaring a provider is not credential authorization. Missing credentials fail closed rather than silently falling back.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-24 | Determinism + credential boundaries constrain the design: no provider SDK, network call, or credential handling anywhere, so "provider" is a caller-supplied data table (`fixtures/providers.yaml`, simulated) and selection is a pure contract check. T-028's nightly cross-provider e2e belongs to the approval-gated live lane; here divergence is measured through the one deterministic provider-sensitive channel — declared numeric requirements capped by provider capability (effective fuel) — and published via tools/provider_divergence.py → docs/PROVIDER-DIVERGENCE-REPORT.md (BALANCE-REPORT pattern). Surfaces expanded beyond core/+tests/ to fixtures/, tools/, docs/ for the fixture table and published report; no parallel node shares them. | this row | `core/providers.py` (declared_order, select_provider fail-closed with selection evidence, effective_doc, divergence_report publishing trace- and outcome-level rates); suite 141→153 (T-026 ×4, T-027 ×4, T-028 ×4) |
