# Reddi Arena — Revised Recommendation

**Supersedes the phasing in `docs/ROADMAP.md`.** Written after the lab repo went
public on 2026-08-05 and the launch context became visible.

## Recommendation in one line

**Do not run the 5-phase programme. Ship one tutorial and one spec finding
before 2026-08-31, and park everything else behind the launch.**

## Why the plan changed

Three facts from `reddiagent-lab` that were not visible when the plan was written:

1. **26 days to public launch.** One end-to-end AUDD/x402/RAP devnet payment
   demo satisfies the launch epic, the AUDD M1 grant evidence chain, and the
   Colosseum Eternal Challenge. A slip in one slips all three. Nothing in the
   Arena programme is on that critical path.
2. **Automation is paused.** New `*_packet`/`*_gate`/`*_handoff`/`*_signoff`
   work is prohibited pending explicit re-authorization. Arena issues `F1` and
   `F2` proposed exactly that. Struck.
3. **The learning path already exists** and its ten lessons mirror the
   conformance levels the Arena league was going to teach. The Arena is a
   capstone for it, not a parallel structure.

## What to do before 2026-08-31

### Ship 1 — File the price-discovery finding (half a day)

`F-007`: `maxAmount` is a cap, not a price. Neither ADL v0.2 nor the A2A mapping
can express "this service costs X per task". Any marketplace where buyers compare
rival specialists on price is blocked on this.

The Arena is the clearest possible motivating example, and the finding is
strengthened by three already-known v0.3 candidates it sits beside. File through
`docs/OPEN-SPEC-REVIEW-INTAKE.md` as **Stable / spec correction**, targeting
`specs/PAYMENT-REPUTATION-EXTENSION-v0.1.md`, with the Arena mercenary market as
the use case and this repo's ablation evidence attached.

Also file `F-002` (currency enum excludes non-monetary units) as **Experimental**
— it is the only finding here with no existing counterpart in the lab.

### Ship 2 — Attach the ablation evidence to the known charge-intent item

`F-001` is already recorded as v0.3 candidate #1/#2. What the lab does not have
is a reproduction. This repo provides one: a passing Level 3 document from which
deleting `authority`, `scope`, `purpose`, `requireReceipt`, or `receiptRef`
individually still yields Level 3 pass. That converts a written concern into a
regression test the v0.3 checker can be built against.

Cost: attach a fixture and a table to an existing issue.

### Ship 3 — One tutorial, not a programme (2–3 days)

`tutorials/vault-duel.md` as **lesson 11** of the learning path: two ADL
documents, one Vault match, no purse, Level 1 only.

It satisfies the teaching rule — the builder ends with runnable artifacts — and
it demonstrates in a form nobody forgets that **a bot cannot do what its ADL did
not declare**. Deliverables already exist in this repo: two conforming documents,
the deterministic weigh-in, and the ruleset.

Explicitly out of scope for the tutorial: purses, hiring, escrow, receipts,
reputation, devnet. Level 1 forbids the payment extension anyway, so the
constraint is the spec's, not a compromise.

## What to park

| Parked | Revisit when |
|---|---|
| P2 Mercenary Market | v0.3 has a price field; otherwise the market cannot be built honestly |
| P3 League and Learning | After launch, if the tutorial draws real players |
| P4 Devnet Proof | Never as scoped — packet machinery exists and automation is paused |
| Weight-class formula v0.2 | Only if a real league forms |
| `E14` injection containment | Before any *hosted* multiplayer, not before a local tutorial |

## What survives from the original work

- Two conformance-passing ADL documents (L1 and L3) — reusable as lab examples.
- The deterministic weigh-in and capability hash — a genuinely novel demo that
  ADL is computable, and small enough to contribute as a script.
- The league-ladder-from-conformance-levels mapping — the strongest teaching idea
  in the whole proposal, and it costs nothing because the spec already implies it.
- `docs/FINDINGS.md` — 15 drift corrections, 2 novel findings, 3 confirmations
  with evidence, 1 honest withdrawal.

## The honest summary

The Arena is a good idea whose value is almost entirely **pedagogical and
diagnostic**, and both of those cash out at a fraction of the proposed cost. The
programme as scoped would have consumed the launch window to build infrastructure
that mostly already exists, in service of evidence the project is already
generating another way.

The plan documents remain in this repo as the fuller design, should a real league
ever be worth building. They should not be executed now.
