# Blockchain Leverage Assessment — Solana, AUDD, x402, Identity

_2026-08-05. Grounded in the shipped code in `nissan/reddi-agent-protocol` and
`reddinft/reddiagent-lab`, not in design speculation._

## Short answer: mostly already built — and the Arena is not using any of it

The Arena as built is 100% off-chain: an in-memory ledger, arena credits, a JSON
trace. Meanwhile the protocol repo already runs **four Quasar programs on Solana
devnet** whose instruction set maps almost one-to-one onto the Arena's needs.

| Live on devnet | Program ID (devnet) |
|---|---|
| Registry | `Xk7jczJZ1HHJZuE1ZUWDqFmowxYhnom7mWzrNSGf9FU` |
| Escrow | `VYCbMszux9seLK2aXFZMECMBFURvfuJLXsXPmJS5igW` |
| Reputation | `nb9rLVjoHMibsgfRGgKuPqm6M8GVcH9r6bYNfg7Yiy6` |
| Attestation | `CRGsWWkptdxsH6N6aWAyahLbuMsT58yM624EopEsv1Ex` |

The Anchor escrow program exposes 14 instructions. Read them as an arena feature
list:

| Instruction | Arena meaning |
|---|---|
| `lock_escrow` / `release_escrow` / `cancel_escrow` | Purse locked at weigh-in, released on verified win, refunded on no-contest |
| `register_agent` / `update_agent` / `deregister_agent` | Fighter and power-up registration — on-chain identity |
| `commit_rating` / `reveal_rating` / `expire_rating` | Commit-reveal ratings — exactly the anti-retaliation scheme the Arena design called for |
| `attest_quality` / `confirm_attestation` / `dispute_attestation` | The referee: judge scores, confirmation, disputes |
| `delegate_escrow` / `release_escrow_per` | Session-key delegation for ephemeral rollups — per-match low latency |

So the honest position: **the Arena did not need to invent an economy. It needs
to bind to one that already exists.**

---

## What each chain primitive is actually good for here

Ranked by whether a blockchain earns its place, rather than by novelty.

### 1. Commit-reveal ratings — the strongest fit

`RatingAccount` carries `consumer_commitment` and `specialist_commitment` as
separate 32-byte hashes, with optional scores revealed later and an expiry path.
In a competitive arena, rivals rate rivals; that invites retaliation and score
copying. A neutral, tamper-evident ledger with enforced commit-then-reveal
ordering is genuinely the right tool — this is not blockchain-for-its-own-sake.

### 2. Purse escrow — the classic fit

Two competitors stake, a neutral program holds, release is conditional. The key
property the Arena teaches — *payment success is not work success* — becomes
structurally enforced rather than merely documented: release is gated on
attestation, not on the match transport completing.

### 3. Agent identity via `AgentAccount` — good fit, with a caveat

`AgentAccount` holds `owner`, `agent_type`, `model`, `rate_lamports`,
`min_reputation`, `reputation_score`, `jobs_completed`, `jobs_failed`,
`attestation_accuracy`, `active`. That is a portable fighter/specialist passport:
a builder's reputation follows their wallet, not an Arena account.

**Caveat:** this is an on-chain registry, not a full identity system. For
portability across ecosystems there is already `erc8004-export.ts` plus a
conformance module, and the lab's `#378/#392` track records that the
Foundation-endorsed Agent Registry and SATI are live on Solana with **two write
paths, not one shared substrate** — SATI rides SAS/Light Protocol; the
8004-solana port uses SEAL v1 event hashes with an indexer. TRACKS recommends
**SATI-first dual-publish**. The Arena should not pick a side here; it should
consume whatever the attestation-mapping lane concludes.

### 4. Ephemeral rollups for match play — the most underrated fit

`magicblock_cpi.rs` pins the Permission and Delegation program layouts and a
devnet TEE validator, and `delegate_escrow` / `release_escrow_per` exist for the
session-key path. The file is explicit that it **does not yet invoke MagicBlock
programs** — the byte layouts are pinned for the next slice.

For a game this is the single best-fit blockchain feature available: delegate the
match to an ephemeral rollup, play turns at low latency under a per-match session
key, then commit one final result back to the base layer. Arenas are exactly the
high-frequency, low-value-per-action workload that base-layer settlement handles
badly and ERs handle well.

### 5. AUDD — real, but narrower than it sounds

`audd-payment-plan.ts` implements `reddi.audd-payment-plan.v1`: network, mint,
payee, settlement account, amount, quote expiry, failure policy, refund policy,
evidence requirement, and a `dry-run | live` mode — with a preflight decision
carrying 19 reason codes including `live_payment_not_approved`,
`operator_approval_required`, `credential_leakage_rejected`, and
`quote_payment_plan_mismatch`.

But the rail-parity matrix is unambiguous about what AUDD support currently
means: **payment-plan and proof-metadata support. Not AUDD custody, not SPL-token
escrow, not live payment activation, not mainnet readiness, not
settlement-finality proof.** The rail states are `fixture`, `dry-run`,
`proof-metadata-only`, `devnet-gated`, `live-gated`.

The attractive Arena story — "AUD-denominated prize pools for Australian
builders" — is therefore a **future** story, not an available one. What is
available now is generating well-formed AUDD payment plans and binding proof
references in receipts, on dry-run.

### 6. What should stay off-chain

Being clear about this matters more than the list above:

- **Match traces** — too large, and they contain opponent strategy. Store the
  trace hash on-chain, the trace itself in the evidence archive.
- **ADL documents** — same: hash on-chain, document off-chain. This is already
  the pattern (`capabilityHash` in the weigh-in certificate).
- **Leaderboard rendering, replay UI, coaching** — derive from chain events; do
  not write them.
- **Anything with player-identifiable metadata** — the projection rule from the
  original plan (`hashes and references only, never rich metadata`) holds.

---

## New finding: the price gap is a *parity* gap (F-009)

`AgentAccount.rate_lamports` is set by `register_agent` and updated by
`update_agent`. **The on-chain registry already treats a quoted rate as
first-class.** ADL v0.2 — the declaration language — has no price field at all
(finding F-007); `maxAmount` is only a cap.

So the same protocol expresses a specialist's price on-chain but cannot express
it in the document that defines the specialist. Any consumer reading an ADL
document to build a listing must go to chain for the price, or invent an
extension as the Arena did (`x-arena.price`).

This substantially strengthens F-007: the need for a price field is not
hypothetical or Arena-specific — the chain layer has already committed to it, and
the two layers disagree. Recommend adding this to the F-007 intake as the
strongest supporting argument.

---

## Recommended sequencing for the Arena

Respecting the gates: mainnet blocked pending audit; devnet requires explicit
approval, wallet/RPC scope, transaction count, spend cap, artifact path.

**Now — DONE.** Implemented in `core/chain.py`, surfaced via `arena chain` and the
web On-Chain tab, covered by 18 tests. It projects register_agent payloads from
ADL documents, escrow lock, the settlement decision, commit-reveal rating rounds
using the real `sha256(score || salt)` scheme, attestation scores, and a dry-run
AUDD purse plan — submitting nothing. The settlement matrix is the useful part:
a completed match with a failed required gate **refunds**, and an unattested one
**disputes**, so "payment success is not work success" is executable rather than
aspirational.

**Was: now — no new approvals needed.**
Bind the Arena's vocabulary to the on-chain shapes without writing anything:
compute the `AgentAccount` fields a fighter *would* register with, emit a
`reddi.audd-payment-plan.v1` for a purse in dry-run mode, and render the
commit-reveal rating flow locally. This is a projection exercise and it makes the
next step trivial.

**Next — localnet, still no external approval. HARNESS BUILT, EXECUTION BLOCKED.**
`tools/rehearse.py` validates all projected payloads offline against the
constraints in `programs/escrow` (33 checks, all passing), emits the ordered
8-step execution plan, and reports blockers honestly. Its verdict today is
`PAYLOADS-VALID / EXECUTION-BLOCKED`: no validator binary is installed and no
wallet exists in this repo by design. The validator is proven non-vacuous — 8
tamper cases (over-long model, diverted registration fee, release without
attestation, reveal before commit, traces moved on-chain) are each caught.

PDAs are now genuinely derived via `find_program_address` rather than
stand-ins, so the payloads are address-accurate.

To actually rehearse: install surfpool. The lab's `#394` note is directly relevant: rehearse
against Surfpool's copy-on-read mainnet fork with real USDC/PYUSD/AUDD mints and
live Agent Registry/SATI programs, rather than synthetic fixtures.

**Then — devnet, requires explicit approval.**
Register two fighters and one specialist against the live Registry program, run
one match with escrow lock → attestation → release, and one commit-reveal rating
round. That single flow exercises all four programs and produces exactly the kind
of bounded devnet evidence the launch epic needs.

**Later — gated.**
Ephemeral-rollup match play (needs the MagicBlock invoke slice to land first) and
any AUDD movement beyond proof-metadata.

**Not scheduled.**
Real-value prizes. Arena credits must not become redeemable without crossing the
audit gate, and a credits-to-AUDD bridge is precisely the secondary-market risk
flagged in the analyst brief.

---

## The honest summary

Almost every blockchain capability the Arena wants is already deployed on devnet
and unused by it. The work is integration and approval, not invention. The two
genuinely new contributions the Arena can make are:

1. **F-009** — the on-chain/ADL price parity gap, which strengthens F-007 with
   evidence from the project's own program state.
2. **A concrete consumer for the ephemeral-rollup path**, which is currently
   scaffolded but has no motivating workload. A turn-based arena is the most
   natural one available.
