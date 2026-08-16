# REASONS-LITE — Build the Arena negative-fixture corpus

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: A2 | Epic: E01 ADL Arena Profile and Fixture Corpus |
Phase: P0 Foundry | Lane: SL-A Spec and Conformance_


## R — Requirements / Definition of Done

Invalid documents must fail for the stated reason, not incidentally.

**DoD checklist:**

- [x] Every negative fixture fails validation (21 schema-invalid, each with a
      declared path+message diagnostic; 3 documented-gap fixtures are
      schema-valid **by design** and are rejected by the Arena-local lint or
      the conformance checker — see Sync Log)
- [x] Every negative fixture asserts a specific diagnostic, not a generic failure
- [x] Zero negative fixtures pass silently

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | A competitor bot is expressible as a schema-valid ADL v0.2 document, and a corpus of valid/invalid fixtures exists that the lab can adopt. | phase exit gate: All P0 tests green; ADL fixtures validate against published schema. |
| Dependencies | must be closed first | [A1] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Invalid documents must fail for the stated reason, not incidentally. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: adl/, vendor/, tools/validate_adl.py, fixtures/

## O — Operations / Ordered Tasks

1. Author >= 20 invalid fixtures, one per intended failure mode
2. Cover bare-string instructions, missing policyRef on a risky tool, duplicate tool/function IDs, sourceRef prefix mismatch, unprefixed extension namespace
3. Assert each fixture fails with the expected diagnostic code, not merely "invalid"

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

**Boundary (what this issue does NOT authorize):** Fixtures are review artifacts; they do not define new ADL semantics.

| Test | Type | Asserts |
|---|---|---|
| T-003 | contract | Every negative fixture fails validation |
| T-004 | contract | Each negative fixture produces its expected diagnostic code, not a generic error |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0003-a2-build-the-arena-negative-fixture-corpus.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue A2 — Build the Arena negative-fixture corpus
Epic: E01 ADL Arena Profile and Fixture Corpus | Dependencies (must already be closed): A1

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-003, T-004.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Fixtures are review artifacts; they do not define new ADL semantics.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-16 | Corpus is generated (tools/gen_negative_fixtures.py), not hand-authored: each fixture is the reference defender with ONE targeted break, and the generator verifies every declared diagnostic against the pinned schema at generation time, refusing to write a corpus that misbehaves. Building it surfaced two NEW schema gaps the O-tasks implied were failures but are not: duplicate tool ids (F-010) and unknown tool keys / sideEffect typo (F-011) — both schema-valid, both now caught by an Arena-local lint in validate_adl.py and logged in docs/FINDINGS.md. "Zero fixtures pass silently" is honored via the manifest contract: schema-valid gap fixtures must be flagged and lint-rejected, or the validator exits nonzero. | DoD checked; this row | fixtures/negative/: 24 fixtures + manifest.yaml; validate_adl.py manifest-driven T-003/T-004 + arena_lint; tests/test_arena.py +5 checks (suite 63→68). Executed as graph node A2 (branch node/A2-negative-fixture-corpus) under the GE01 pilot. |
