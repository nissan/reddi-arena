# Tutorial — The Vault Duel

_A capstone for the ReddiAgent learning path. Lessons 1–10 teach you to write an
ADL agent; this one lets two of them fight, and shows you why the declaration is
a contract, not documentation._

**Teaching rule honored:** you end this lesson with a runnable artifact — a match
you can replay, a leaderboard you climb, and a power-up you can buy.

**Boundary:** everything here runs locally on the `x402-dry-run` rail. Prizes are
arena credits with no real value. No wallet, no live rail, no model provider is
called — competitors play from a declared, seeded strategy so the whole thing is
deterministic and inspectable.

---

## What you already know (lessons 1–10)

You can write an agent as an ADL document: a `model` envelope, a `harness` with
tools, policies, and eval gates, and — at Level 3 — a payment extension. You know
that a document is validated against the canonical schema and that conformance
levels gate what an agent may do.

## The one new idea

**Weight class is computed from the declaration.** Everything your bot declares —
its context window, its tools, its data sources, its payment intents — adds
*arena units* (AU). Add enough and you change weight class. So a power-up is a
real tradeoff: it makes you stronger and heavier at the same time.

That is the whole game, and it is only possible because ADL is machine-readable.

## Step 1 — Weigh in

```bash
python3 cli/arena.py weigh adl/antweight-vault-defender.adl.yaml
```

You'll see each declared capability priced in AU, a total, and a class. The
reference defender is 62 AU — an Antweight. Note that declaring explicit policies
makes it *lighter*: good hygiene is a competitive advantage.

## Step 2 — Fight

```bash
python3 cli/arena.py fight \
  adl/antweight-vault-defender.adl.yaml \
  adl/antweight-vault-raider.adl.yaml --seed 2
```

The raider wins on turn 3: its probe of 80 beats the defender's defense of 65.
Run it again with the same seed — identical result. The match is a pure function
of the two documents and the seed.

## Step 3 — Shop the market

```bash
python3 cli/arena.py market
```

One specialist is listed: a source-auditor that grants +15 defense (it catches
the untrusted-source citation traps the Vault format allows as a legal attack).
It costs 20 arena credits and weighs 91 AU on its own.

## Step 4 — Try to draft it

```bash
python3 cli/arena.py draft \
  adl/antweight-vault-defender.adl.yaml \
  --hire adl/mercenary-source-auditor.adl.yaml --class Antweight
```

**Refused.** The hire adds 65 AU (coupled weight), pushing you to 127 — over the
Antweight ceiling of 100. This is the tradeoff made concrete: the power-up would
make you fight as a Beetleweight. You either enter the heavier class or drop the
hire.

## Step 5 — Power up and win

Enter as a Beetleweight and the hire is legal. Now re-run the same seed-2 match
with the power-up:

```bash
python3 cli/arena.py fight \
  adl/antweight-vault-defender.adl.yaml \
  adl/antweight-vault-raider.adl.yaml --seed 2 \
  --hire-a adl/mercenary-source-auditor.adl.yaml
```

The match that you lost on turn 3 you now **win on turn 6** — the +15 defense
held off the probe that beat you before. Same opponent, same seed, different
outcome, because you changed your declaration.

## Step 6 — Learn from the replay

```bash
python3 cli/arena.py fight ... --out match.json
python3 cli/arena.py replay match.json
```

The pit-crew read tells you exactly which turn decided the match and what would
have changed it — and every line maps to a recorded event in the trace. Nothing
is inferred beyond what happened.

## Play in the browser

```bash
python3 web/server.py 8000
# open http://127.0.0.1:8000
```

Same engine, same rules, with the weigh-in scale showing your class bump live as
you select a power-up.

## What you learned

- A bot's strength and its weight both come from the same declaration.
- A power-up is a real decision, not a free upgrade — the class line is the cost.
- The match is deterministic and fully evidenced, so every loss is a lesson.

## Build your own power-up

Lesson complete. Now flip sides: write a specialist other players will pay to
hire. See `web/static/index.html` → "Build a Power-Up" for the shape, or copy
`adl/mercenary-source-auditor.adl.yaml` and change its `x-arena` block.

_Note: the specialist price currently lives in an `x-arena.price` extension
because ADL v0.2 has no price field. That gap is filed as an open-spec review
(F-007); when v0.3 adds a price field, the extension swaps out with a one-line
change._
