# Node / Release Retrospective Prompt

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
> - Hard boundaries from AGENTS.md apply above everything here: dry-run rail
>   only, one-way spec canonicality, claims discipline, determinism, and the
>   2026-07-26 automation pause — this workflow is process run inside
>   interactive sessions, never a cron/loop, and no
>   `*_packet`/`*_gate`/`*_handoff`/`*_signoff` scripts.
> - F1/F2 are `cancelled` and must never be scheduled (lint G7).

Use Git history, the issue timeline, PR review, CI results, graph revisions and node evidence. Do not rely only on the final implementation state.

Answer:

1. What did we predict would happen?
2. What actually happened?
3. Which assumption was weakest?
4. Where did rework enter the system?
5. Did the graph expose the prerequisite/decision early enough?
6. Did the node boundary prevent scope creep?
7. Which prompt/context/tooling rule helped?
8. Which rule created friction without enough value?
9. What should change: graph topology, node sizing, tests/evals, prompts, GitHub workflow, or human gates?
10. What single measurable experiment will we run on the next comparable node?

Classify recommendations as:
- PROJECT-SPECIFIC
- TEMPLATE-CANDIDATE
- TOOLING-CANDIDATE

Promote a TEMPLATE-CANDIDATE only after it repeats or has strong evidence across projects. Avoid turning one incident into permanent process bureaucracy.
