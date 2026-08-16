# Node Executor Prompt

> **Arena adaptations (GE01).** This prompt is vendored from the
> graph-engineering-project-template. In this repo:
>
> - The canonical graph is `planning/graph.yaml`; lint with
>   `python3 tools/graph_lint.py` (invariants G1–G7, prints the READY frontier).
> - Every migrated node keeps a binding REASONS-LITE artifact in `spdd/prompt/`
>   (see `spdd/INDEX.md` for the node ↔ issue-number map). Read it in full
>   before implementing; update its Sync Log in the same PR if you diverge.
> - Required verification for every node:
>   `python3 tests/test_arena.py` (55+ checks), `python3 tools/validate_adl.py`,
>   `python3 tools/graph_lint.py`.
> - Hard boundaries from CLAUDE.md apply above everything here: dry-run rail
>   only, one-way spec canonicality, claims discipline, determinism, and the
>   2026-07-26 automation pause — this workflow is process run inside
>   interactive sessions, never a cron/loop, and no
>   `*_packet`/`*_gate`/`*_handoff`/`*_signoff` scripts.
> - F1/F2 are `cancelled` and must never be scheduled (lint G7).

You are executing exactly one graph node: `<NODE_ID>`.

## Claim check

Before editing code:

1. Read the node and all of its `dependsOn` predecessors.
2. Verify predecessor evidence still holds on the current base branch.
3. Confirm the node is READY and is not already claimed by another active worktree/PR.
4. Read the linked GitHub issue and any human decisions/comments.
5. Create/use only the node branch and worktree.

## Scope contract

Implement only the node objective and acceptance criteria. Respect its boundary and file-surface constraints.

If you discover:

- a missing prerequisite → propose/create a predecessor node and block this node;
- a consequential choice → create/activate a decision node and request human input;
- useful but non-required work → create a separate successor/related node;
- an invalid assumption → update the planning graph in a dedicated planning commit/PR.

Do not absorb these into the current implementation merely because you can.

## Engineering loop

1. DISCOVER: inspect current behavior, tests, relevant history and predecessor evidence.
2. PLAN: state the smallest coherent change and verification strategy.
3. IMPLEMENT: make atomic commits; avoid unrelated cleanup.
4. VERIFY: run node tests plus repository-required regression/security/lint checks.
5. REFLECT: record divergences and retrospective data.

## PR completion contract

The PR description must contain:

- Node ID and linked issue (`Closes #...`).
- Objective.
- Dependency evidence checked.
- Changes made.
- Acceptance criteria checklist.
- Exact verification commands and results.
- Boundary/non-goals confirmation.
- New graph nodes/edges discovered, if any.
- Risks and rollback notes where applicable.

Before final merge, rebase onto the latest default branch and rerun required verification.
