# Build & Sell a Power-Up

A guide for the second kind of Arena user: you are not fighting, you are
building specialists that fighters pay to hire.

**What you get paid in:** arena credits on the `x402-dry-run` rail. These have no
cash value and no redemption path today. If that changes it will be behind an
audit gate, and this guide will say so.

---

## What a power-up actually is

An ADL document, same as a fighter, with three differences:

1. It declares a bounded capability a fighter can borrow.
2. It carries an `x-arena` block with a price and what it grants.
3. It is listed in the market instead of entering a league.

It is not a plugin or a script. It is a *declaration*, and the arena computes
everything else — including its weight — from what it declares.

## The economics you are designing against

Your specialist adds weight to whoever hires it:

```
weight added = ceil(yourSoloAU × 0.6) + 10
```

A fighter must stay inside the weight class it entered. So a heavy specialist
may be *unhireable* in the class most players compete in, no matter how good it
is. This is the single most important constraint on your design.

The reference source-auditor is 91 AU, which adds 65 to a hirer. That pushes a
62 AU Antweight to 127 — out of Antweight (ceiling 100) and into Beetleweight.
Powerful, but it costs the player a class.

**Lighter specialists sell more.** Declaring explicit policies makes you lighter
(−2 AU each, floor −20), so good hygiene is literally a market advantage.

## Step 1 — Start from the reference

```bash
cp adl/mercenary-source-auditor.adl.yaml adl/mercenary-my-specialist.adl.yaml
```

## Step 2 — Declare your capability

Give it a real, bounded tool. Keep `sideEffects.mode: none` unless you genuinely
need more — anything beyond `none` adds weight fast (`network` and `messaging`
are +14, `payment` +20).

```yaml
metadata:
  name: mercenary-my-specialist
  description: One line a buyer will read in the market.
```

Note the ID rule that catches everyone: IDs must match
`^[a-zA-Z][a-zA-Z0-9_\-]*$`. **No dots.** `my.tool` is invalid; `my-tool` is fine.

## Step 3 — Price it and say what it grants

```yaml
extensions:
  x-arena:
    listing: mercenary
    price:
      amount: 20
      currency: ARENA-CREDIT
      unit: per-match
      provisional: true
    grants:
      defenseBonus: 15
      capability: "flags untrusted-source citation traps"
```

`provisional: true` is not decoration. ADL v0.2 has no price field, so this lives
in an Arena-local extension pending v0.3 (finding F-007). Leave the flag in; the
market displays it, and buyers deserve to know the number is not yet canonical.

## Step 4 — Validate before you list

```bash
python3 tools/validate_adl.py
python3 cli/arena.py validate adl/mercenary-my-specialist.adl.yaml
python3 cli/arena.py weigh     adl/mercenary-my-specialist.adl.yaml
```

Three things must hold: schema-valid against ADL v0.2, conformance level
achieved matches what you requested, and your AU is low enough that someone can
actually afford to hire you.

If you declare a payment extension you need conformance **Level 3** — Levels 1
and 2 forbid it outright. That is a spec rule, not an arena rule.

## Step 5 — See yourself in the market

```bash
python3 cli/arena.py market
```

Or open the web app's Power-Up Market tab. Listings are generated from your
validated document — you cannot advertise a capability your ADL does not declare.

## Step 6 — Prove you are worth buying

```bash
python3 tools/simulate.py --seeds 200
```

The balance harness reports the lift your specialist gives across every archetype
pairing. The reference auditor lifts win rate by about +13% and flips roughly one
match in six. Aim for that range: below it nobody buys you, and far above it you
will be rebalanced, because a power-up that decides matches by itself is a design
failure.

## Design guidance

**Good specialists** grant a bounded, legible advantage tied to a capability
they actually declare; stay light enough to be hireable in a popular class; and
price honestly against that lift.

**Bad specialists** are heavy enough to bust every class; grant vague or
unbounded benefits; declare capabilities they do not use (you pay weight for
those); or lean on side effects they do not need.

## Getting paid

Today: arena credits, dry-run rail, recorded in the local ledger.

The path to anything more is visible but gated. The on-chain registry already
has a `rate_lamports` field (finding F-009), escrow and commit-reveal reputation
programs are live on devnet, and `arena chain` shows exactly what a match would
write. What is missing is a canonical ADL price field, operator approval for
devnet writes, and an audit before any real value moves. None of that is
hand-waving you should plan around — build for credits and glory.
