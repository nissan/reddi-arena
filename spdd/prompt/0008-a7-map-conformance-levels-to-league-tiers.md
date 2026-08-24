# REASONS-LITE — Map conformance levels to league tiers

_Status: ready | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: A7 | Epic: E03 Conformance-to-League Mapping |
Phase: P1 First Blood | Lane: SL-A Spec and Conformance_


## R — Requirements / Definition of Done

This is the teaching mechanism — players learn the spec by ranking up, not by reading it.

**DoD checklist:**

- [x] A Level-1 document cannot enter a Title fight or carry a purse
- [x] requestedLevel above achieved level is rejected with the failing requirement named
- [x] The tier verdict is recorded in the weigh-in certificate

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | ADL conformance levels gate league entry, so players climb the spec ladder by playing. | phase exit gate: 100 consecutive local matches with complete traces and zero policy escapes. |
| Dependencies | must be closed first | [A1], [A4] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

This is the teaching mechanism — players learn the spec by ranking up, not by reading it. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: adl/, vendor/, tools/validate_adl.py, fixtures/

## O — Operations / Ordered Tasks

1. Bind five tiers: L0 garage entry, L1 Rookie, L2 Open, L3 Title, L4 Pro/Hosted
2. Enforce that purses and hiring require L3, because L1/L2 forbid the payment extension
3. Inspect declared rails separately: achieved L3 does not imply dry-run only (F-006)
4. Run the conformance checker at registration and store the verdict
5. Reject documents whose requestedLevel exceeds their achieved level

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

**Boundary (what this issue does NOT authorize):** Reaching a tier grants match eligibility only. It never grants provider, network, wallet, or rail access.

| Test | Type | Asserts |
|---|---|---|
| T-015 | contract | A Level-1 document is refused entry to a Title fight |
| T-016 | contract | requestedLevel above achieved level is rejected naming the failing requirement |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0008-a7-map-conformance-levels-to-league-tiers.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue A7 — Map conformance levels to league tiers
Epic: E03 Conformance-to-League Mapping | Dependencies (must already be closed): A1, A4

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-015, T-016.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Reaching a tier grants match eligibility only. It never grants provider, network, wallet, or rail access.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (ready) | initial | n/a |
| 2026-08-24 | DISCOVER: LEAGUE_TIERS (rookie L1 / open L2 / title L3, purse+hiring Title-only) existed in core/arena.py but nothing computed an ACHIEVED level or recorded a verdict; the cli defers to a lab conformance bundle that is not vendored. One-way canonicality constrains the design: assess_level() in tools/weigh_in.py is an explicitly ARENA-LOCAL structural eligibility ladder (L1 basics, L2 full policy coverage + observability events, L3 redaction+retention+evidenceRefs), not canonical certification — the lab checker remains the authority. tier_verdict() rejects requestedLevel > achieved with the failing rung named, grants eligibility up to the achieved level, and is embedded in the certificate BEFORE the capability hash so the verdict is hash-covered and unswappable. TIER_LEVELS mirrors LEAGUE_TIERS with a suite check asserting sync. First node run under the independent-review gate (policy commit e730e70). | this row | tools/weigh_in.py (+assess_level, tier_verdict, TIER_LEVELS, cert field); suite 198→205 (A7 sync ×1, T-015 ×3, T-016 ×3) |
| 2026-08-24 | Independent review (REQUEST-CHANGES) reshaped the node before merge. Blocker: the first ladder contradicted the lab checker's recorded verdicts — it assessed the lab-certified-L3 mercenary at 2 and REJECTED it (locking the mercenary market out of every tier) because L3 keyed on conformance.evidenceRefs while the mercenary's evidence lives on observability events; filed as F-012 (reddiagent-lab#450). Redesign: L3 evidence accepts either declaration site; verdict fields renamed to arena vocabulary (arenaAssessedLevel/effectiveLevel, never achievedLevel); eligibility anchors to min(requestedLevel, arenaAssessedLevel) — reproducing both lab verdicts (DEF 1, MERC 3), fixing the purse-above-request hole (a Level-1-declaring doc can never carry a purse), and turning over-request rejection into fall-back-to-assessed rather than total lockout. requestedLevel beyond the ladder assesses at the ladder max; unreadable requestedLevel fails closed without an exception. The vacuous hash-coverage test was replaced with a retention-removal probe (same AU breakdown, different verdict, different hash). Rebutted (kept): duplicate requestedConformanceLevel cert field is pre-existing certificate shape, retained. | this row | tools/weigh_in.py redesign; suite 205→207 (A7 ×2, T-015 ×3, T-016 ×4); docs/FINDINGS.md F-012 |
