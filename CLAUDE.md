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

Work here follows the lab's SPDD approach with GitHub issues as the spine:

1. **Every work loop anchors on one GitHub issue.** Each issue has a binding
   REASONS-LITE artifact in `spdd/prompt/` (see `spdd/INDEX.md` for topological
   order). Read the artifact in full before implementing; **update it in the
   same PR** if your implementation materially diverges.
2. **The graph decides the order.** `plan/backlog.yaml` is the canonical
   dependency DAG; `tools/plan_lint.py` enforces its seven invariants and
   `tools/generate_prompts.py` regenerates artifacts and the issue script from
   it. Edit the plan, never the generated files.
3. **Doneness is a passing test**, never a closed ticket. Every issue names its
   tests; `python3 tests/test_arena.py` and `python3 tools/validate_adl.py`
   must both be green before any PR.
4. **Loops end with a retrospective** comment on the issue (Loop Protocol:
   what changed the plan, weakest assumption, next loop).

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

python3 tests/test_arena.py            # 55 checks — must pass before any PR
python3 tools/validate_adl.py          # schema gate against pinned v0.2
python3 tools/simulate.py --seeds 200  # balance sweep; regen BALANCE-REPORT if engine changed
python3 tools/plan_lint.py             # plan invariants L1-L7
python3 tools/generate_prompts.py      # regenerate spdd/ + github/ from the graph
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
