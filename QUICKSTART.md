# Reddi Arena — Quickstart

Two ways to get into the arena. Both call the same engine (`core/arena.py`), so
results are identical.

**Prizes are ARENA-CREDIT on the x402-dry-run rail — no real value.** No wallet,
no live rail, no model provider is called. Matches are deterministic simulations
driven by each bot's declared strategy.

## Install

```bash
pip install pyyaml jsonschema --break-system-packages   # core + validation
# optional, for the browser UI screenshots/tests:
pip install playwright --break-system-packages && python3 -m playwright install chromium
```

## CLI

```bash
python3 cli/arena.py validate adl/antweight-vault-defender.adl.yaml
python3 cli/arena.py weigh     adl/antweight-vault-defender.adl.yaml
python3 cli/arena.py market
python3 cli/arena.py draft     adl/antweight-vault-defender.adl.yaml \
                     --hire adl/mercenary-source-auditor.adl.yaml --class Antweight
python3 cli/arena.py fight     adl/antweight-vault-defender.adl.yaml \
                     adl/antweight-vault-raider.adl.yaml --seed 2 --out match.json
python3 cli/arena.py replay    match.json
python3 cli/arena.py leaderboard

# what a match WOULD write on Solana — writes nothing
python3 cli/arena.py chain antweight-vault-defender.adl.yaml \
                     antweight-vault-raider.adl.yaml --audd 50.00
python3 cli/arena.py chain ... --fail-gate    # payout blocked despite a completed match
python3 cli/arena.py chain ... --no-attest    # dispute instead of payout

# local Solana Devnet Preview — RAP Assurance fixtures, writes nothing.
# Off by default; start the server with the flag to reach it (see Web, below).
curl -s http://127.0.0.1:8000/api/assurance/scenarios
```

## Web

```bash
python3 web/server.py 8000

# with the Solana Devnet Preview tab (off by default, exact value required)
REDDI_ENABLE_SOLANA_DEVNET_ASSURANCE_PREVIEW=true python3 web/server.py 8000
```

| Route | What it is |
|---|---|
| `/` | Landing page — the pitch, the demo, waitlist signup |
| `/play` | The arena app |

Waitlist emails are stored locally in `core/waitlist.json`. There is no account
system and no published retention policy — the landing page says so plainly.

Five tabs: **The Arena** (weigh in, draft, fight, coached replay), **Power-Up
Market** (specialists for hire), **Leaderboard**, **Build a Power-Up** (the ADL
shape for sellers), **On-Chain** (the Solana projection). A sixth, **Devnet
Preview** (local RAP Assurance receipt and tamper/replay fixtures), appears only
when `REDDI_ENABLE_SOLANA_DEVNET_ASSURANCE_PREVIEW` is set — boundaries and the
exact accepted values are in `docs/DEVNET-PREVIEW-RAP-ASSURANCE.md`.

## Tests

```bash
python3 tools/simulate.py --seeds 200   # balance sweep -> docs/BALANCE-REPORT.md
python3 tools/rehearse.py       # localnet rehearsal preflight (starts nothing)
python3 tests/test_arena.py     # whole suite: determinism, draft rules, boundaries, Devnet Preview refusals
python3 tools/validate_adl.py   # all fighters validate against the pinned ADL v0.2 schema
```

## Documentation

| Doc | For |
|---|---|
| `tutorials/vault-duel.md` | First match, step by step |
| `docs/BUILD-A-POWERUP.md` | Building and selling specialists |
| `docs/ARCHITECTURE.md` | Contributors — module map, determinism, extension points |
| `docs/VAULT-MATCH-RULESET-v0.1.md` | Full format rules and league ladder |
| `docs/WEIGHT-CLASS-v0.1.md` | The AU formula |
| `docs/BALANCE-REPORT.md` | Published balance data |
| `docs/BLOCKCHAIN-INTEGRATION-ASSESSMENT.md` | Solana/AUDD/x402/identity mapping |
| `docs/DEVNET-PREVIEW-RAP-ASSURANCE.md` | The Devnet Preview tab — scenarios, boundaries, fixture contributions |
| `docs/FINDINGS.md` | Spec findings filed upstream |

## Two roles

**Compete:** pick a fighter, optionally hire a power-up (mind the class bump),
fight, climb the leaderboard.

**Sell power-ups:** publish a specialist ADL with an `x-arena` block declaring
its price and the capability it grants. Competitors hire it in the draft. See
`tutorials/vault-duel.md` and the "Build a Power-Up" tab.

## What's real vs. provisional

| Real now | Provisional / gated |
|---|---|
| ADL v0.2 schema validation of every fighter | Specialist price (`x-arena.price`) — pending ADL v0.3 (F-007) |
| Deterministic weigh-in, class bump, draft | Real-value prizes — needs an audited mainnet rail (out of scope) |
| Deterministic Vault matches + replay | Live model-driven competitors — separate approval-gated lane |
| Arena-credit prizes on dry-run rail | Any devnet write — needs scoped operator approval |
| On-chain payload projection with **real PDAs** (`find_program_address`) | Actual submission — no RPC/wallet/signing exists in this codebase |
| Local Solana Devnet Preview for RAP Assurance receipts and negative fixtures | Real devnet writes, official AUDD mint observation, grant evidence, custody, or external deployment |
| Offline rehearsal preflight — 33 checks against `programs/escrow` constraints | Running a validator — needs surfpool/solana-test-validator installed |
| AUDD payment plans (`reddi.audd-payment-plan.v1`, dry-run) | AUDD custody, SPL escrow, settlement finality |

The single provisional dependency — price — is isolated to one function
(`core.arena.advertised_price`), so adopting a v0.3 price field is a one-line
change.
