# REASONS-LITE — Abuse, harm and content handling for player-authored bots

_Status: parked | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: E4I | Epic: E14 Injection Containment and Arena Safety |
Phase: P2 Mercenary Market | Lane: SL-E Trust, Safety and Anti-Cheat_


> **PARKED** behind the 2026-08-31 launch (docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision.

## R — Requirements / Definition of Done

Player-authored agents are user-generated content and will eventually include harmful material.

**DoD checklist:**

- [ ] Prohibited-behaviour policy is published before the first season
- [ ] Every moderation action is logged with reviewer and reason
- [ ] An appeal path exists and is documented

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | Adversarial content between competitors stays inside the match and cannot reach the platform, the judge, or another player. | phase exit gate: Every paid engagement produces a valid receipt bound to evidence. |
| Dependencies | must be closed first | [E3I] |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

Player-authored agents are user-generated content and will eventually include harmful material. The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: core/, tests/ (binding, containment)

## O — Operations / Ordered Tasks

1. Define prohibited bot behaviours and publish them before the season
2. Implement report, review, and appeal paths
3. Ensure moderation actions are logged and reversible

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

**Boundary (what this issue does NOT authorize):** Moderation covers Arena-hosted play. It makes no claim about what players run privately.

| Test | Type | Asserts |
|---|---|---|
| T-085 | contract | Prohibited-behaviour policy is published before season open |
| T-086 | contract | Every moderation action is logged with reviewer and reason and is reversible |

## Claude Code prompt

```text
You are working in nissan/reddi-arena. Read CLAUDE.md first, then read spdd/prompt/0033-e4i-abuse-harm-and-content-handling-for-player-autho.md
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue E4I — Abuse, harm and content handling for player-authored bots
Epic: E14 Injection Containment and Arena Safety | Dependencies (must already be closed): E3I

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: T-085, T-086.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
Moderation covers Arena-hosted play. It makes no claim about what players run privately.
```

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml (parked) | initial | n/a |
