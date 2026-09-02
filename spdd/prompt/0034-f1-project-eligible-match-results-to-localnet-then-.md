# REASONS-LITE — Project eligible match results to localnet then devnet

_Status: struck | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: F1 | Epic: E15 Devnet Projection and External Tester Packet |
Phase: P4 Devnet Proof | Lane: SL-F Release Ops and Evidence_


> **STRUCK — do not run.** Violates the 2026-07-26 automation pause; retained for the record only (docs/REVISED-RECOMMENDATION.md).

## R — Requirements / Definition of Done

Real players generating real evidence is a better tester gate than recruiting people to run conformance suites.

**DoD checklist:**

- [ ] Localnet rehearsal passes before devnet is touched
- [ ] No personal or rich metadata appears on chain
- [ ] Every projection reconciles to exactly one off-chain receipt

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Arena play generates the bounded devnet evidence the protocol repo still owes on the release ladder. | phase exit gate: Bounded devnet evidence accepted by lab release-readiness review. |
| Dependencies | must be closed first | [C6], [C9] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Real players generating real evidence is a better tester gate than recruiting people to run conformance suites. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: docs/, findings/, .github/

## O — Operations / Ordered Tasks

1. Rehearse on localnet before any devnet write
2. Project only hashes and references, never rich metadata
3. Reconcile on-chain projections against off-chain receipts

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

**Boundary (what this issue does NOT authorize):** Devnet proof is not mainnet readiness. Rich metadata stays off-chain; only hashes and references project.

| Test | Type | Asserts |
|---|---|---|
| T-087 | integration | Localnet rehearsal passes before any devnet write is attempted |
| T-088 | adversarial | No rich or personal metadata is written on chain; hashes and refs only |
| T-089 | integration | Every on-chain projection reconciles to exactly one off-chain receipt |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0034-f1-project-eligible-match-results-to-localnet-then-.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue F1 — Project eligible match results to localnet then devnet
Epic: E15 Devnet Projection and External Tester Packet | Dependencies (must already be closed): C6, C9

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-087, T-088, T-089.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Devnet proof is not mainnet readiness. Rich metadata stays off-chain; only hashes and references project.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (struck) | initial | n/a |
