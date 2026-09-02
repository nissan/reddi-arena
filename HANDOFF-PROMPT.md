# Handoff index — Reddi Arena

This file used to carry a one-time bootstrap prompt for the first agent session.
That snapshot is history now; it lives in this file's git log. What remains here
is a pointer index, so nothing on this page can go stale independently of the
document that owns it.

Start here, in this order:

| To learn | Read |
|---|---|
| Working rules, methodology, hard boundaries | [`AGENTS.md`](AGENTS.md) — read it in full first |
| What the product is and how to run it | [`README.md`](README.md), [`QUICKSTART.md`](QUICKSTART.md) |
| How the pieces fit together | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| What is in scope right now | [`docs/REVISED-RECOMMENDATION.md`](docs/REVISED-RECOMMENDATION.md) |
| What to work on next | [`planning/graph.yaml`](planning/graph.yaml) via `python3 tools/graph_lint.py` |
| How to execute a node | [`planning/prompts/`](planning/prompts/) and the node's artifact in [`spdd/prompt/`](spdd/prompt/) |
| Operating the deployed service | [`docs/OPERATIONS.md`](docs/OPERATIONS.md) |

`AGENTS.md` is the authority for everything a session must not do; do not restate
those boundaries here.
