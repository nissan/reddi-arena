# REASONS-LITE — Validate reference ADL documents against the published v0.2 schema

_Status: done | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: A1 | Epic: E01 ADL Arena Profile and Fixture Corpus |
Phase: P0 Foundry | Lane: SL-A Spec and Conformance_


## R — Requirements / Definition of Done

The reference bots were drafted from prose, not from the schema. Until validated they are hypotheses, not artifacts.

**DoD checklist:**

- [x] Both reference ADL documents validate with zero schema errors
- [x] The pinned schema hash is recorded and checked in CI
- [x] Every drift correction has a one-line changelog entry citing the schema path

**Done evidence:** tools/validate_adl.py — both reference documents 0 errors against pinned schema 679a5c3e...; 15 drift corrections and 5 findings logged in docs/FINDINGS.md; F-001 charge-intent gap reproduced as a schema-valid negative fixture.

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | A competitor bot is expressible as a schema-valid ADL v0.2 document, and a corpus of valid/invalid fixtures exists that the lab can adopt. | phase exit gate: All P0 tests green; ADL fixtures validate against published schema. |
| Dependencies | must be closed first | none |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

The reference bots were drafted from prose, not from the schema. Until validated they are hypotheses, not artifacts. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: adl/, vendor/, tools/validate_adl.py, fixtures/

## O — Operations / Ordered Tasks

1. Fetch specs/ADL-v0.2.schema.json from the published downloads or lab repo
2. Pin schema by sha256 into the repo as a vendored fixture
3. Run both reference ADLs through a Draft 2020-12 validator
4. Correct every field-name and enum drift found; log each drift as a finding
5. File drift findings upstream to the lab as implementation reports

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

**Boundary (what this issue does NOT authorize):** Validation proves document shape only. It authorizes no execution.

| Test | Type | Asserts |
|---|---|---|
| T-001 | contract | Both reference ADLs validate against the pinned v0.2 schema with zero errors |
| T-002 | determinism | Vendored schema sha256 matches the pinned upstream value; CI fails on drift |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0002-a1-validate-reference-adl-documents-against-the-pub.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue A1 — Validate reference ADL documents against the published v0.2 schema
Epic: E01 ADL Arena Profile and Fixture Corpus | Dependencies (must already be closed): none

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-001, T-002.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Validation proves document shape only. It authorizes no execution.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (done) | initial | n/a |
