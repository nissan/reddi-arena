# planning/ — canonical execution graph (graph-engineering pilot)

`graph.yaml` is the **source of truth for scheduling and status** as of node
GE01. It was migrated from `plan/backlog.yaml` by `tools/plan_to_graph.py`;
the backlog file is retained as the superseded fuller design (its own header
says so) and still backs the generated `spdd/prompt/` artifacts, which remain
the binding per-node context.

- Lint: `python3 tools/graph_lint.py` — invariants G1–G7, prints the READY
  frontier.
- Rules of engagement: `prompts/00-bootstrap.md` (project lead),
  `prompts/10-node-executor.md` (one node), `prompts/20-graph-supervisor.md`
  (scheduling pass), `prompts/30-retrospective.md` (node/release retro).
- Node workflow: claim a READY node → branch `node/<ID>-<slug>` (worktree if
  parallel) → local loop → one PR linking the node issue with evidence →
  rebase + re-verify → merge → retrospective → status flip to `done` in a
  planning commit that records evidence.
- Two classes of edges: `dependsOn` schedules; `informs`/`validates`/
  `produces`/`conflictsWith`/`supersedes` carry context and never block.
- Decision nodes (`DEC-*`, `humanGate: true`) turn consequential ambiguity
  into topology. Parked lanes reopen only through them, post-launch, with an
  ADR in `docs/adr/`.
- Do not record volatile GitHub state (PR numbers, worktree paths, CI runs)
  in `graph.yaml`; reconstruct it from GitHub when needed.
- `maxParallelNodes: 2` and per-node `surfaces` bound collision risk; two
  dependency-independent nodes still must not overlap allowed surfaces on
  high-conflict files (`core/arena.py`).

The pilot's exit is node GE03: after 3–5 full node cycles, a meta-retrospective
decides promote / adjust / abandon for the template — nothing is promoted to
`reddiagent-lab` or `reddi-agent-protocol` before that.
