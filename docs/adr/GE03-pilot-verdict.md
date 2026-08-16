# GE03 — Graph-engineering pilot verdict

_Status: decided. Approval: Nissan, 2026-08-16, recorded on issue #42 (decision
taken interactively in the Claude Code session that ran the pilot)._

## Context

The graph-engineering-project-template was piloted in this repo per the
programme roadmap (`reddi-agent-protocol`
`docs/ARENA-SHIP-AND-GRAPH-ENGINEERING-ROADMAP-2026-08-16.md`, Phase 2) and the
template's `MIGRATION-FROM-REDDI-ARENA.md`. Four nodes completed the full
claim → branch → PR-with-evidence → rebase-gate → merge → retrospective →
planning-flip cycle in one day:

| Node | PR | What it proved |
|---|---|---|
| GE01 (infra) | #38 | Migration is mechanical; template lint needed G3–G7 extensions |
| A4 (freeze) | #39 | DISCOVER converts stale build-nodes into verify-nodes correctly |
| A2 (corpus) | #40 | Verify-at-generation-time catches wrong assumptions mechanically; produced spec findings F-010/F-011 |
| F3 (canonicality) | #41 | Doneness-as-a-test caught a real omission (F-008 register row) on first run |

Suite grew 55 → 72 checks; the repo gained CI; five upstream filings
(lab#443–#446 plus the #389 evidence comment) were produced *by* node work.
Zero boundary violations; F1/F2 remain cancelled and lint-protected.

## Options considered

1. **Promote now** — migrate `reddiagent-lab` and `reddi-agent-protocol`
   immediately. Rejected: inside the 2026-08-31 launch window; contradicts the
   roadmap's own Phase 2 boundary and risks the launch-critical repos for
   process benefit.
2. **Adjust now, promote post-launch** — fold improvements into this repo,
   migrate the other repos after launch. **Chosen.**
3. **More cycles first** — defensible, but the four cycles already span the
   node types that matter (infra, verify/freeze, artifact-building,
   process/enforcement) and the evidence is uniform.
4. **Abandon** — no support in the evidence; every cycle was cheaper and better
   audited than its SPDD-loop equivalent.

## Decision

**Adjust now; promote post-launch.** Additionally: **merge policy is
rebase/linear, enforced** — the pilot's four merge commits were a
tooling-default accident, not a preference. Maintainer action owed: enable
"require linear history" and the rebase merge method in this repo's GitHub
settings (no tool in the pilot session could change repo settings). Until the
setting lands, node PRs merge with the rebase method explicitly.

## Adjustments applied in this repo (with this ADR)

1. Node-executor prompt: DISCOVER now must state whether the node's artifact
   is stale relative to the implementation (the A4 lesson).
2. CLAUDE.md norm: findings are filed upstream at discovery time, not batched
   (the F3 lesson).

## TEMPLATE-CANDIDATES carried to the post-launch promotion

1. Lint invariants G3–G7 (status vocabulary, done-requires-evidence,
   cancelled-dependency rule, ready-frontier consistency,
   humanGate-requires-approval).
2. Statuses first-class in the canonical graph, never derived inside
   generators.
3. Verify-declared-expectations-at-generation-time for fixture/evidence
   generators.
4. Upstream disposition register + completeness lint for any repo that
   consumes an upstream spec.
5. DISCOVER artifact-staleness check in the node-executor prompt.

## Consequences

- Post-launch (2026-09-01+), promotion runs as graph nodes **in the target
  repos** (this ADR authorizes proposing them, not executing them — each repo
  records its own decision, consistent with one-way canonicality of process).
- GE02 (native GitHub relations sync) remains on this repo's READY frontier
  and continues under the adjusted process.
- The 2026-07-26 automation pause is unaffected: everything above is
  interactive-session process, no crons, no loops, no packet/gate scripts.
