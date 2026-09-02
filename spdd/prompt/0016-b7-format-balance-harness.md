# REASONS-LITE — Format balance harness

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: B7 | Epic: E06 Vault Arena Format |
Phase: P1 First Blood | Lane: SL-B Arena Runtime_


## R — Requirements / Definition of Done

Without a balance harness, the first dominant strategy ends the format's competitive life.

**DoD checklist:**

- [x] Attacker/defender win split falls within the published tolerance band
- [x] No single archetype exceeds the published dominance threshold
- [x] The balance report is published before the season opens

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | One complete, balanced, adjudicable arena format ships end to end. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [B6] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Without a balance harness, the first dominant strategy ends the format's competitive life. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/arena.py, tools/simulate.py, tests/

## O — Operations / Ordered Tasks

1. Run round-robin baselines across archetype bots
2. Measure first-mover advantage and attack/defence win asymmetry
3. Publish the balance report with the season rules

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

**Boundary (what this issue does NOT authorize):** Balance findings inform format v0.2; they do not retroactively alter results.

| Test | Type | Asserts |
|---|---|---|
| T-038 | e2e | Attacker/defender win split stays inside the published tolerance band |
| T-039 | e2e | No archetype exceeds the published dominance threshold |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read AGENTS.md first, then read spdd/prompt/0016-b7-format-balance-harness.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue B7 — Format balance harness
Epic: E06 Vault Arena Format | Dependencies (must already be closed): B6

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-038, T-039.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Balance findings inform format v0.2; they do not retroactively alter results.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-24 | Artifact staleness (DISCOVER): most of the harness predates the node — tools/simulate.py (round-robin, mirror-position bias, power-up impact, published BANDS, non-zero exit on drift) and the suite's balance-regression section shipped with the preview; docs/BALANCE-REPORT.md is already published. Verify-and-formalize scope: the one missing O2 measure — explicit attack/defence win asymmetry — added as attack_defence_split() with published band (0.35, 0.65) wired into the harness verdict; T-038/T-039 landed as labeled suite checks (split in band; dominance + report-published); the P1 exit-gate evidence (100 consecutive matches, complete terminal traces, zero policy escapes) measured here because the balance harness is the e2e surface. 200-seed run: split 59.9%, verdict BALANCED; report republished with the asymmetry section. | this row | tools/simulate.py (+attack_defence_split, +band, verdict wiring, report line); docs/BALANCE-REPORT.md (+asymmetry section); suite 194→198 (T-038 ×1, T-039 ×2, P1 exit gate ×1) |
