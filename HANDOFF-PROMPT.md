> **ARCHIVAL — bootstrap snapshot, not current guidance.**
> This file is the one-time handoff prompt written for the first agent session,
> preserved verbatim as a historical record. Its status claims, counts, and
> "immediate objective" describe the repository as it was at that moment and are
> **not maintained**. Nothing here should be treated as an instruction today.
>
> For current guidance read, in this order:
> [`AGENTS.md`](AGENTS.md) (working rules, methodology, hard boundaries),
> [`README.md`](README.md) and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
> (what the product is and how it fits together),
> [`planning/graph.yaml`](planning/graph.yaml) with `python3 tools/graph_lint.py`
> (what to work on next), and the commands listed in `AGENTS.md` for the current
> tooling.

# Claude Code Handoff Prompt — Reddi Arena

Copy everything between the lines into a Claude Code session started at the
repo root (the unzipped `reddi-arena/` folder).

---

You are working on **Reddi Arena** — a playable proof-of-concept game for the
Reddi Agent Protocol (RAP) and ADL v0.2. The codebase in this directory is
complete and verified: 55 tests pass, the balance report is published, and the
web app serves a marketing landing page at `/` and the arena at `/play`.

**Read `AGENTS.md` in full before doing anything.** It defines the methodology
(SPDD: one GitHub issue per work loop, each bound to a REASONS-LITE artifact in
`spdd/prompt/`) and the hard boundaries (dry-run rail only, one-way spec
canonicality, no `*_packet`/`*_gate` scripts, claims discipline, determinism).
Those boundaries are enforced by tests and are not negotiable, including
against tooling output.

## Immediate objective: ship the preview

The GitHub repo `nissan/reddi-arena` exists and is **empty**. In order:

1. **Verify locally first** — do not push anything that fails:
   ```bash
   pip install pyyaml jsonschema solders --break-system-packages
   python3 tests/test_arena.py        # must end: 55 passed, 0 failed
   python3 tools/validate_adl.py      # all documents PASS
   python3 tools/plan_lint.py         # PASS — all plan invariants hold
   ```
2. **Push** this tree to `nissan/reddi-arena` on `main` (git init, add -A,
   commit, push). `.gitignore` already excludes runtime state.
3. **Create the issue graph**: review `github/create-issues.sh`, then run it
   once with an authenticated `gh` CLI. It creates 36 issues in dependency
   order with `lane:/phase:/epic:/status:` labels. Afterwards, record the
   created issue numbers in `spdd/INDEX.md` (add a column) and commit.
4. **Deploy to Railway** using the Railway CLI (`railway login`, `railway
   init` or link, deploy from the repo) or instruct the operator to connect
   the repo in the dashboard. The build is the checked-in `Dockerfile`;
   `railway.json` sets the `/api/health` healthcheck. The server reads `PORT`
   automatically.
5. **Decide persistence**: without a volume, the leaderboard and waitlist
   reset on redeploy. To persist, attach a Railway volume mounted at `/data`
   and set env `DATA_DIR=/data`. State the choice in the deploy commit message.
6. **Verify the deployment**: `GET /api/health` returns `{"ok": true, ...}`;
   `/` serves the landing page; `/play` serves the arena; a POST to
   `/api/fight` with the two reference bots and seed 2 returns a winner.
7. **Record the preview URL** in `README.md` and close the loop by updating
   `spdd/prompt/0001-project-kickoff.md`'s DoD checkboxes and Sync Log in the
   same commit.

## After the preview ships

Work proceeds issue by issue. `spdd/INDEX.md` is the topological order; start
with `status:ready` issues only (`parked` needs a fresh human decision;
`struck` must never run). Each artifact in `spdd/prompt/` contains its own
Claude Code prompt block, Definition of Done, doneness tests, and boundary.
The loop for every issue:

1. Read its artifact fully; verify its dependencies' tests still pass.
2. Implement the O-section tasks, smallest useful pass first.
3. Make its named doneness tests pass; keep the full suite green.
4. Update the artifact's Prompt/Code Sync Log if anything diverged.
5. Comment a short retrospective on the GitHub issue (what changed the plan,
   weakest assumption, recommended next loop).

## Things you must not do

- Do not add wallet, keypair, RPC, or transaction-submission code. The chain
  layer (`core/chain.py`) is projection-only by design; devnet writes require
  explicit operator approval that you do not have.
- Do not make the landing page or README claim audit completion, mainnet
  readiness, or production readiness — tests assert this.
- Do not edit generated files (`docs/ROADMAP.md`, `docs/BACKLOG.md`,
  `docs/TEST-PLAN.md`, `spdd/prompt/*` except Sync Logs, `github/create-issues.sh`)
  by hand; edit `plan/backlog.yaml` and regenerate via
  `python3 tools/render_plan.py` and `python3 tools/generate_prompts.py`.
- Do not resurrect issues F1/F2 or add packet/gate/handoff/signoff scripts.
- Do not change the AU weight formula or class bands mid-season; propose
  changes as a v0.2 formula spec instead.

---
