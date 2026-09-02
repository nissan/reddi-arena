# Reddi Arena — Architecture

Technical reference for contributors. For getting started, see `QUICKSTART.md`;
for the game rules, `docs/VAULT-MATCH-RULESET-v0.1.md`.

## Design rule: one core, many surfaces

```
                    adl/*.adl.yaml          ← the only source of truth
                          │                    about what a bot can do
                          ▼
    ┌───────────────────────────────────────────────────┐
    │  core/arena.py      weigh-in · draft · match      │
    │  core/chain.py      Solana payload projection     │
    │  core/assurance.py  RAP Assurance preview adapter │
    └───────────────────────────────────────────────────┘
        │              │                │
        ▼              ▼                ▼
   cli/arena.py   web/server.py   tools/simulate.py
                        │
                        ▼
                web/static/index.html
```

No game logic lives in the CLI, the server, or the browser. Both surfaces call
the same functions, which is why `arena fight --seed 2` and the web app produce
byte-identical results. Any rule that exists in only one surface is a bug.

## Modules

| Path | Responsibility |
|---|---|
| `tools/weigh_in.py` | AU weight formula and capability hash. Pure function of a validated ADL document. |
| `core/arena.py` | League tiers, draft/hire evaluation, deterministic Vault match engine, trace emission. |
| `core/chain.py` | Projects matches onto Quasar program payloads. Derives real PDAs. Submits nothing. |
| `core/assurance.py` | Maps deterministic Arena traces plus fixture payment observations into canonical RAP receipt/integrity field names for the local Solana Devnet Preview. Submits nothing. |
| `cli/arena.py` | Terminal surface: validate, weigh, market, draft, fight, replay, leaderboard, chain. |
| `web/server.py` | Stdlib HTTP JSON API over the same core. No logic of its own. |
| `web/static/index.html` | Single-file UI. No build step, no framework. |
| `tools/validate_adl.py` | Schema gate against the pinned ADL v0.2 schema. |
| `tools/simulate.py` | Balance harness: round robin, mirror matches, power-up impact. |
| `tools/rehearse.py` | Offline preflight for a future localnet rehearsal. Starts nothing. |
| `tools/plan_lint.py`, `tools/render_plan.py` | Programme plan invariants and markdown projections. |

## Determinism

The match engine takes `(bot_a, bot_b, seed, hires)` and returns a trace plus a
`traceHash` over the canonicalised result. Properties relied on everywhere else:

- No clock, no `random`, no network, no provider call. The only entropy is the
  caller-supplied seed, fed through a small LCG.
- The same inputs always produce the same trace hash — asserted in the test
  suite and used as the escrow job identifier in `core/chain.py`.
- Replays render recorded events only. If it is not in the trace, the replay
  does not claim it.

Competitors currently play from a declared `x-arena.strategy` profile rather
than a live model. Wiring real providers is a separate, approval-gated lane and
is deliberately absent from this codebase.

## Weight, and why it is the whole design

`weigh_in.py` prices every declared capability in Arena Units. Two figures:
**solo AU** (what class you may enter) and **fielded AU** (after hires, must stay
inside that class). A hire costs `ceil(specialistSoloAU × 0.6) + 10`.

This only works because ADL is machine-readable. A capability that is not
declared does not add weight — and, per the runtime-binding design, also cannot
be used. That is what makes the declaration a contract rather than documentation.

## Extension points

**New arena format:** add a `run_*_match` function in `core/arena.py` returning
the same trace shape (`turns`, `winner`, `result`, `reason`, `traceHash`). The
CLI, web, replay, and chain projection all work unchanged.

**New power-up:** add `adl/mercenary-*.adl.yaml` with an `x-arena` block
declaring `price` and `grants`. The market lists it automatically. Grant effects
are applied in `run_vault_match`; keep them bounded and tied to a capability the
document actually declares.

**New fighter archetype:** add to `ARCHETYPES` in `tools/simulate.py` so it is
covered by the balance sweep before it reaches players.

## The provisional dependency

Specialist price lives in `extensions.x-arena.price` because ADL v0.2 has no
price field (finding F-007; the on-chain registry *does* have `rate_lamports`,
which is finding F-009). Exactly one function reads it —
`core.arena.advertised_price` — so adopting a real v0.3 price field is a
one-line change.

## Boundaries enforced in code, not just prose

- Prizes are `ARENA-CREDIT` on `x402-dry-run`. Asserted in the test suite.
- `core/chain.py` has no RPC client, no keypair handling, and no transaction
  builder. Every payload carries a `not-submitted` marker.
- `core/assurance.py` uses deterministic parsed-payment fixtures and read-only
  devnet metadata only; its boundary flags keep RPC, wallets, signing, custody,
  official-mint observation, grant evidence, and external deployment false.
- `audd_purse_plan()` hard-codes `paymentMode: "dry-run"` with no parameter to
  change it.
- Match traces, ADL documents, and player metadata are explicitly listed as
  never written on-chain; only hashes and references project.

## Testing

`tests/test_arena.py` — the single suite gate (see `AGENTS.md` for the current
check count), across determinism, draft rules, power-up effect, boundary
invariants, chain payloads, RAP Assurance preview refusals, tamper detection,
and balance regression. The tamper tests matter most: they prove the rehearsal
validator rejects malformed payloads rather than rubber-stamping them.

`tools/simulate.py --seeds 200` — the full balance sweep. Run it after any
engine change and regenerate `docs/BALANCE-REPORT.md`.
