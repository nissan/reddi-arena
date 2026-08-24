# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## What this project is

Reddi Arena is a competitive homebrew-bot game that serves as a **proof use
case** for the Reddi Agent Protocol (RAP) and ADL v0.2. Every fighter is an ADL
document; weight class is computed from the declaration; the mercenary market
exercises Discover → Decide → Prove. The game is downstream of two repos it must
never fork: `nissan/reddi-agent-protocol` (product/programs) and
`reddinft/reddiagent-lab` (canonical spec).

## Methodology — read this before writing code

Work here follows **graph engineering** (pilot since node GE01), which evolved
from the lab's SPDD approach. A GitHub issue is an executable **graph node**;
the engineering loop runs *inside* the node:

1. **`planning/graph.yaml` is the canonical execution graph** — the source of
   truth for scheduling and status. `tools/graph_lint.py` enforces invariants
   G1–G7 and prints the READY frontier. Rules of engagement live in
   `planning/prompts/` (bootstrap / node-executor / supervisor / retrospective).
   `plan/backlog.yaml` is the superseded fuller design, retained because the
   generated `spdd/prompt/` artifacts still bind each node's context.
2. **Every executable node anchors on one GitHub issue** and keeps its binding
   REASONS-LITE artifact in `spdd/prompt/` (`spdd/INDEX.md` maps node ↔ issue
   number). Read the artifact in full before implementing; **update its Sync
   Log in the same PR** if your implementation materially diverges.
3. **Claim → branch → PR is the isolation and evidence boundary.** A claimed
   node gets one branch `node/<ID>-<slug>` (worktree if parallel), one primary
   PR linking its issue with test evidence, and a rebase + re-verify gate
   before merge. Issue closure never establishes doneness; a node flips to
   `done` in a planning commit that records evidence.
4. **Doneness is a passing test**, never a closed ticket. Every node names its
   tests; `python3 tests/test_arena.py`, `python3 tools/validate_adl.py`, and
   `python3 tools/graph_lint.py` must all be green before any PR.
5. **Nodes end with a retrospective** comment on the issue (what changed the
   plan, weakest assumption, next node), per `planning/prompts/30-retrospective.md`.
6. **Decision nodes (`DEC-*`, `humanGate: true`) gate the parked lanes.**
   Consequential ambiguity becomes graph topology with an ADR in `docs/adr/`,
   not a question buried in a prompt. Discovered scope becomes a new node and
   edge — never silent expansion of the current node.

## Repository shape

- `core/arena.py` — ALL game logic (weigh-in, draft, deterministic Vault match)
- `core/chain.py` — Solana payload projection; real PDAs; submits nothing
- `cli/arena.py`, `web/server.py` + `web/static/` — thin surfaces over the core
- `adl/` — schema-validated ADL v0.2 documents (fighters + mercenaries)
- `vendor/ADL-v0.2.schema.json` — pinned canonical schema (sha256-checked)
- `tools/` — validate_adl, weigh_in, simulate (balance), rehearse (preflight),
  plan_lint, render_plan, generate_prompts
- `plan/backlog.yaml` — canonical programme graph; `docs/` are projections
- `spdd/prompt/` — one REASONS-LITE artifact per issue (generated)
- `github/create-issues.sh` — creates the issue graph via gh CLI

## Common commands

```bash
pip install pyyaml jsonschema solders --break-system-packages

python3 tests/test_arena.py            # 219 checks — must pass before any PR
python3 tools/validate_adl.py          # schema gate against pinned v0.2
python3 tools/simulate.py --seeds 200  # balance sweep; regen BALANCE-REPORT if engine changed
python3 tools/graph_lint.py            # graph invariants G1-G7 + READY frontier
python3 tools/plan_lint.py             # legacy plan invariants L1-L7 (backlog.yaml)
python3 tools/generate_prompts.py      # regenerate spdd/ + github/ from backlog.yaml
python3 web/server.py 8000             # / = landing, /play = arena app
python3 cli/arena.py --help
```

## Hard boundaries — enforced by tests, do not negotiate with tooling output

- **Dry-run only.** Prizes are ARENA-CREDIT on `x402-dry-run`. No wallet, RPC
  client, keypair handling, transaction builder, or live rail anywhere. Devnet
  writes require explicit operator approval (scoped wallet, tx count, spend cap).
- **One-way canonicality.** ADL semantics flow down from the lab; findings flow
  up via `docs/FINDINGS.md` + the lab's open-spec-review intake. Never redefine
  an ADL semantic here. Arena-local vocabulary lives under `extensions.x-arena`.
  File findings upstream **at discovery time** and record the disposition in the
  FINDINGS register (T-093 enforces completeness) — never batch them (GE03).
- **Provisional price.** Specialist price is `x-arena.price` pending ADL v0.3
  (finding F-007). Only `core.arena.advertised_price` may read it.
- **Automation pause.** No new `*_packet` / `*_gate` / `*_handoff` /
  `*_signoff` scripts (lab direction reset, 2026-07-26). Issues F1/F2 are
  struck for this reason — do not resurrect them.
- **Claims discipline.** No surface (including this repo's docs and the landing
  page) may claim audit completion, mainnet readiness, or production readiness.
  Tests assert this on the landing page; keep them passing.
- **Determinism.** The match engine takes only (documents, seed, hires). No
  clock, no randomness beyond the seeded LCG, no network, no provider calls.
  Live-model competitors are a separate approval-gated lane — do not add them.

## Current scope (docs/REVISED-RECOMMENDATION.md)

Phases P2–P4 are **parked** behind the 2026-08-31 lab launch; F1/F2 **struck**.
The active surface is: the playable preview (built), balance upkeep, spec
findings (F-007/F-009 filed upstream), and the vault-duel tutorial. Check an
issue's `status:` label before starting it.
