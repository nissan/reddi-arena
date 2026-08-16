# REASONS-LITE — Define the arena-profile extension namespace

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: A3 | Epic: E01 ADL Arena Profile and Fixture Corpus |
Phase: P0 Foundry | Lane: SL-A Spec and Conformance_


## R — Requirements / Definition of Done

Arena needs match-specific metadata (format, class, fuel cap) without polluting canonical ADL.

**DoD checklist:**

- [ ] x-arena fields validate under strict mode
- [ ] An unprefixed "arena:" key fails strict validation
- [ ] No payment, spend, or authority semantics exist in x-arena

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | A competitor bot is expressible as a schema-valid ADL v0.2 document, and a corpus of valid/invalid fixtures exists that the lab can adopt. | phase exit gate: All P0 tests green; ADL fixtures validate against published schema. |
| Dependencies | must be closed first | [A1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Arena needs match-specific metadata (format, class, fuel cap) without polluting canonical ADL. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: adl/, vendor/, tools/validate_adl.py, fixtures/

## O — Operations / Ordered Tasks

1. Specify x-arena namespace fields (format, declaredClass, fuelCap, seasonId)
2. Assert strict validation rejects unprefixed arena keys
3. Document the promotion path if the lab later adopts any field

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

**Boundary (what this issue does NOT authorize):** An x- namespace is Arena-local. It confers no canonical status and must not carry payment-like semantics.

| Test | Type | Asserts |
|---|---|---|
| T-005 | contract | x-arena namespaced fields pass strict validation |
| T-006 | adversarial | Unprefixed arena keys and payment-like semantics under x-arena are rejected |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0004-a3-define-the-arena-profile-extension-namespace.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue A3 — Define the arena-profile extension namespace
Epic: E01 ADL Arena Profile and Fixture Corpus | Dependencies (must already be closed): A1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-005, T-006.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
An x- namespace is Arena-local. It confers no canonical status and must not carry payment-like semantics.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
