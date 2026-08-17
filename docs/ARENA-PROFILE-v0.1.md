# Reddi Arena — Arena-Profile Extension Namespace v0.1 (`x-arena`)

**Status:** specified (v0.1, issue A3). Arena-local. Confers no canonical
status: nothing under `x-arena` is an ADL semantic, and the lab may ignore all
of it. Enforced by the `x-arena-*` checks in `tools/validate_adl.py` (T-005,
T-006).

**Boundary (A3):** an `x-` namespace is Arena-local and must not carry
payment-like semantics. Payment *machinery* — intents, authority, rails,
receipts, policy references — lives only in canonical `extensions.x402` /
`extensions.receipts`; `x-arena` may carry display metadata about the game
economy, never anything a wallet, facilitator, or settlement layer would read.

## Why this namespace exists

Arena needs match-specific metadata (league, strategy profile, market listing)
without polluting canonical ADL. The schema already enforces the prefix rule:
an unprefixed `arena:` extension key fails validation
(`fixtures/negative/extensions-unprefixed-namespace.yaml`). This spec closes
the other half: what is allowed *inside* `x-arena`.

## Vocabulary v0.1 (closed — unknown top-level keys are lint errors)

| Key | Type | Used by | Meaning |
|---|---|---|---|
| `league` | string | competitors | current league tier label (display) |
| `strategy` | object `{attack: 0-100, defense: 0-100}` | competitors | declared, seeded play profile — the deterministic engine's only behavioral input |
| `listing` | string | mercenaries | market listing kind (e.g. `mercenary`) |
| `price` | object `{amount, currency, unit, provisional, note}` | mercenaries | **provisional** advertised price pending the ADL v0.3 price mechanism (F-007, filed as reddiagent-lab#440). Display-only: the enforceable cap remains canonical `maxAmount`; only `core.arena.advertised_price` may read this key |
| `grants` | object `{defenseBonus, capability}` | mercenaries | what hiring this specialist adds in-match (display + engine bonus) |

Reserved (planned in the original A3 scope, not yet used — reserved so future
use is not an unknown-key error): `format`, `declaredClass`, `fuelCap`,
`seasonId`.

## Forbidden inside `x-arena` (lint: `x-arena-payment-semantics`)

Keys that would smuggle payment machinery into the un-audited namespace, at
any depth: `intents`, `authority`, `rails`, `receipts`, `requireReceipt`,
`receiptRef`, `policyRefs`, `spend`, `refund`, `charge`, `settlement`,
`wallet`, `facilitator`. The one deliberate exception: `price.currency` /
`price.amount` as *display* fields per F-007 — they carry no rail, no
authority, and no receipt binding, and validators must never treat them as a
charging instruction.

## Promotion path

If the lab adopts a field (e.g. a v0.3 price mechanism resolves F-007), the
Arena migrates in one release: the canonical field becomes authoritative, the
`x-arena` key is deprecated with a one-season overlap for old certificates,
then removed from this vocabulary. Promotion is proposed only through the
lab's open-spec-review intake — never by treating an `x-arena` key as if it
were already canonical (one-way canonicality, F3).
