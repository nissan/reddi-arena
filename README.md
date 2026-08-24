# Reddi Arena

A competitive homebrew-bot arena used as a **proof use case** for the Reddi Agent
Protocol (RAP) and Agent Definition Language (ADL) v0.2.

> USENIX Security 2026 found security-rule violations in all fifteen major x402
> payment facilitators. "Payment succeeded, therefore the work was done" is an
> empirically endemic failure, not a hypothetical one. An arena where thousands
> of adversarial players try to get paid without doing the work is a direct test
> of the protocol's answer to it.

Players assemble bots in a garage, weigh in, optionally hire specialists from a
mercenary market, and fight over a purse. Underneath, every one of those actions
is an ADL document, a RAP policy decision, an eval gate, a receipt, or an
attestation. The game is the demo.

## Why a game

| Protocol layer | Game surface | What it proves |
|---|---|---|
| ADL document | The bot | ADL is a complete agent contract, not a prompt |
| Machine-readable declaration | Weight class | ADL is computable, not just descriptive |
| Conformance levels | League tiers (5, L0–L4) | Players climb the spec ladder by playing |
| L1 forbids payment ext | Rookie league is purse-free | The economy unlocks only at Level 3 |
| RAP Discover | Mercenary market | Relevance is not trust |
| RAP Decide | Draft window | Bounded authority, budgets, narrowing mandates |
| RAP Prove | Purse escrow, receipts | **Payment success is not work success** |
| Eval gates | Match adjudication | Transport success is never task success |
| Reputation eligibility | League table | Standing derives only from verified work |
| Fail-closed policy | Anti-cheat | The declaration is a contract, enforced at runtime |
| Evidence archive | Replay telemetry | Every loss teaches something specific |

Adversarial players are the best conformance suite you can get: they will try to
lie in their declarations, farm the weight formula, and inject through the
protocol layer. A leaderboard is a bug bounty that people want to enter.

## What actually runs today

```bash
pip install pyyaml jsonschema --break-system-packages

python3 tools/validate_adl.py      # A1/T-001/T-002 — schema validation gate
python3 tools/weigh_in.py adl/antweight-vault-defender.adl.yaml \
        --hire adl/mercenary-source-auditor.adl.yaml
python3 tools/plan_lint.py         # plan invariants L1-L7
python3 tools/render_plan.py       # canonical plan -> markdown projections
```

Add the official conformance checker from the
[v0.2.0-beta bundle](https://agent-protocol.reddi.tech/downloads/adl-v0.2.0-beta.zip):

```bash
python3 scripts/adl_v02_conformance.py <arena-doc>.yaml
# antweight-vault-defender  requested 1  achieved 1  pass
# mercenary-source-auditor  requested 3  achieved 3  pass
```

**Issue `A1` is done.** Both reference documents validate with zero errors
against the canonical ADL v0.2 schema
(`sha256:679a5c3ecfb18f80374aff59190456ea51b94f845ee9d84a3e96f419100af0ed`,
vendored in `vendor/`). Getting there took 15 corrections and produced 5 spec
findings plus 3 plan corrections — all in `docs/FINDINGS.md`.

Everything else remains a design document.

## Status: playable

**Live preview:** https://reddi-arena-production.up.railway.app — `/` is the
landing page, `/play` is the arena. The leaderboard and waitlist persist across
redeploys (Railway volume mounted at `/data`, `DATA_DIR=/data`). Dry-run rail
only; prizes are ARENA-CREDIT.

**Release state:** playable preview on the `x402-dry-run` rail. Every
capability claim on this page is backed by the check suite in
[`tests/test_arena.py`](tests/test_arena.py), run in CI on every push and PR
together with the schema, claims, and graph lints; current gate status is
whatever `python3 tools/graph_lint.py` prints. No security audit has been
performed, and nothing here is mainnet- or production-ready.

The competition arena and the power-up market are **built and running**, CLI and
web, on the honest dry-run lane. Start here:

- **`QUICKSTART.md`** — run the CLI or the web app in one command.
- **`docs/OPERATIONS.md`** — operator runbook for the deployed preview:
  waitlist admin endpoints, signup email, env vars, deploy gotchas.
- **`tutorials/vault-duel.md`** — the guided first match (learning-path capstone).
- **`findings/F-007-price-field-intake.md`** — the spec finding filed in parallel
  so the power-up market can become a true priced marketplace at ADL v0.3.

What you can do right now: weigh in a bot, browse power-ups for hire, get refused
for busting your weight class, enter a heavier class, win the rematch, and climb
a leaderboard — with every match deterministic and every fighter validated
against the canonical ADL v0.2 schema. Prizes are arena credits on the
`x402-dry-run` rail; no real value moves.

## Current recommendation — read this first

**The 5-phase programme in `docs/ROADMAP.md` is superseded and should not be
run.** See `docs/REVISED-RECOMMENDATION.md`. In short: 26 days to the 2026-08-31
launch, nothing here is on that critical path, two issues violate a standing
automation pause, and the Arena's real value lands as one tutorial plus two spec
findings. The plan documents are retained as design, not as work.

## Contents

| Path | What it is |
|---|---|
| `adl/antweight-vault-defender.adl.yaml` | Reference Antweight competitor, 62 AU — **validates** |
| `adl/mercenary-source-auditor.adl.yaml` | Reference hireable specialist with bounded x402 dry-run intent, 91 AU — **validates** |
| `docs/REVISED-RECOMMENDATION.md` | **The actual proposal** — cut to fit the launch window |
| `docs/FINDINGS.md` | Drift log, findings (2 novel, 3 confirmed, 1 withdrawn), 11 plan corrections |
| `fixtures/negative/charge-intent-unbounded.yaml` | Minimal repro of the charge-intent gap (F-001) |
| `vendor/ADL-v0.2.schema.json` | Pinned canonical schema |
| `tools/validate_adl.py` | Schema-validation gate (T-001, T-002) |
| `docs/WEIGHT-CLASS-v0.1.md` | The AU formula and class bands |
| `docs/VAULT-MATCH-RULESET-v0.1.md` | Full match lifecycle mapped to Discover → Decide → Prove |
| `plan/backlog.yaml` | **Canonical** programme plan |
| `docs/ROADMAP.md` | Projection: phases, swimlanes, epics, mermaid dependency graph |
| `docs/BACKLOG.md` | Projection: issues, tasks, acceptance criteria, boundaries |
| `docs/TEST-PLAN.md` | Projection: 95 automated doneness tests and phase exit gates |
| `docs/OPERATIONS.md` | Operator runbook: waitlist admin, signup email, env vars, deploys |
| `docs/ANALYST-REVIEW-BRIEF.md` | Adversarial review brief for an independent pass |
| `tools/weigh_in.py` | Deterministic weigh-in and capability hash |
| `tools/plan_lint.py` | Plan invariant checker (L1–L7) |
| `tools/render_plan.py` | Canonical plan → markdown projections |

The markdown plan documents are **generated**. Edit `plan/backlog.yaml` and
re-render — the same canonical-source-plus-projections discipline ADL applies to
agent definitions.

## Boundaries

Arena is a downstream consumer. ADL semantics flow one way from
`reddiagent-lab`; Arena files findings back as issues and evidence and never
forks the spec.

This programme runs entirely in the OSS/local lane with `x402-dry-run`,
localnet, and devnet. It makes **no claim** of audit completion, mainnet
readiness, production readiness, live rail integration, or wallet custody. Real
value rails are phase P5 and P5 is **not scheduled**.

Arena credits have no redemption path and no external value.
