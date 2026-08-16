# Open-Spec Review — ADL v0.2 has no price-discovery field

_Prepared for `docs/OPEN-SPEC-REVIEW-INTAKE.md` submission. Sanitized. No
secrets, payloads, keys, or live data._

## Reviewer role

Downstream implementer building a competitive arena (Reddi Arena) as a proof use
case for ADL v0.2 and RAP. Feedback surfaced while building a specialist
marketplace where competitors hire "power-up" agents.

## Target

`specs/PAYMENT-REPUTATION-EXTENSION-v0.1.md` and the `paymentIntent` /
`paymentAuthority` definitions in `specs/ADL-v0.2.schema.json`.
Related existing note: `docs/AGENT-TEAM-DELEGATION-EXAMPLES.md`, v0.3 candidate #4
("No price-discovery field").

## State classification

**Stable** — a canonical schema/spec gap needing a v0.3 field, not a fluid design
surface. Confirmed against the shipped schema, not assumed.

## Concrete problem

`maxAmount` is a spending/charging **cap**, not a **quoted price**. A `charge`
intent can say "I will not charge more than 25" but cannot say "this service
costs 20 per task." There is no field on a seller-side intent, on
`paymentAuthority`, or in the A2A card mapping that expresses a quoted unit
price.

This blocks any marketplace where buyers compare specialists on price before
hiring, because the price is the comparison key and it does not exist in the
document. Every consumer must invent a local extension (we used
`extensions.x-arena.price`), which fragments the one number a discovery UI most
needs to standardize.

## Reproduction

From this package (validates against the pinned v0.2 schema
`sha256:679a5c3e…`):

- `adl/mercenary-source-auditor.adl.yaml` — a Level-3 specialist. Its only
  price signal is `extensions.x-arena.price.amount: 20`, an Arena-local
  extension. Remove it and nothing in canonical ADL states what the service
  costs; `maxAmount: "25.00"` remains only a ceiling.
- `core/arena.py::advertised_price()` — the single function that reads the
  provisional field, isolated precisely so a real v0.3 price field is a one-line
  swap.

## Supporting evidence from the project's own program state (F-009)

`programs/escrow/src/state.rs::AgentAccount` carries `rate_lamports`, set by
`register_agent` and updated by `update_agent`. The on-chain registry already
treats a quoted rate as first-class. ADL — the language that *defines* the
agent — cannot express the same thing. The two layers of one protocol disagree
about whether price is a modelled property.

This makes the gap a parity problem rather than a feature request: any consumer
that builds a specialist listing from an ADL document must go to chain for the
price, or invent an extension.

## Suggested acceptance criteria

- A seller-side (`charge`) intent can declare a quoted price: an `amount`, a
  `currency` from the supported set, and a `unit` (e.g. `per-task`,
  `per-match`, `per-1k-tokens`).
- Price is distinct from `maxAmount`; validators may check `price <= maxAmount`.
- The A2A card mapping carries the quoted price, or documents its loss explicitly
  (consistent with the existing `would_drop_reddi_semantics` refusal behavior).
- Conformance reporting can surface "priced service" as a discoverable property.
- The ADL price field and `AgentAccount.rate_lamports` are documented as the same
  concept, with a stated unit/denomination mapping between them.

## Prototype/beta separation

Report-only. This is a spec/schema change request. No runtime, rail, wallet, or
settlement behavior is proposed or exercised. Every example here runs on
`x402-dry-run`.

## Proposed backlog shape

Parent: ADL v0.3 payment-extension revision.
Child A: add `price` to the seller-side intent shape (schema + spec prose).
Child B: `price <= maxAmount` cross-check in the conformance checker.
Child C: A2A card mapping for quoted price, or documented lossy-export refusal.

## Companion finding (separate issue)

`currency` enum is closed to `USD`/`USDC`/`EUR`/`GBP`. Non-monetary units
(arena credits, loyalty points, test currencies) have nowhere to live, forcing
either misuse of `USDC` on the dry-run rail (which reads as real money in
downstream artifacts) or a full extension. Suggest a `TEST`/`CREDIT` member or a
`unit` escape hatch. Classification: **Experimental**. No existing counterpart
found in the lab specs.
