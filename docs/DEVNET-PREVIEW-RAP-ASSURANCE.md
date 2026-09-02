# Solana Devnet Preview — RAP Assurance

This is the earliest safe Arena experience for demonstrating RAP Assurance without
external deployment. It is a local/public preview in `/play` and `/api/assurance`.

## What the preview proves

- An ADL-defined Arena match can produce deterministic work evidence (`traceHash`).
- A deterministic parsed Solana `TransferChecked` fixture can satisfy exact payment
  metadata checks: network, mint, token program, payee owner, amount, authority,
  memo, and replay slot.
- A RAP Assurance receipt can bind payment metadata to authority, resource
  authorization, work output, eval evidence, replay idempotency, privacy
  accounting, dispute state, and rollback/hold state.
- A successful payment fixture is not enough: tampered work, wrong mint, wrong
  payee, replay, authorization denial, or failed eval gates refuse payout or route
  to refund/blocked outcomes.

## Canonical adapter boundaries

Arena does not define a new RAP or ADL schema. The adapter in `core/assurance.py`
uses existing boundaries:

| Boundary | Source |
|---|---|
| ADL document validation | `vendor/ADL-v0.2.schema.json` pinned from `reddiagent-lab` |
| RAP receipt and policy names | `nissan/reddi-agent-protocol/docs/RAP-RECEIPT-POLICY-V1.md` |
| Receipt-integrity diagnostics | `reddinft/reddiagent-lab/scripts/rap_receipt_validator.py` taxonomy |
| x402/Solana `TransferChecked` observation semantics | `nissan/reddi-agent-protocol/packages/x402-solana/src/spl-token-observer.ts` |
| Solana devnet program metadata | `core/chain.py` projection constants |
| AUDD rail identity, policy reason codes | `nissan/reddi-agent-protocol/packages/agent-protocol/src/audd-rail-config.ts`, `.../policy.ts` |

The payment fixture uses the canonical `AUDD_DETERMINISTIC_FIXTURE_MINT`
sentinel (`AUDDdev111111111111111111111111111111111111`) on the
`deterministic-fixture` rail, which is `non_eligible` for grant volume. The
official AUDD mainnet mint is never a fixture value: `load_payment_fixture()`
and the fixture verifier both refuse it. `policyDecision.reasonCodes` only ever
carry codes from the closed canonical `ReddiPolicyReasonCode` set.

If those upstream interfaces change, Arena should update this adapter or file a
finding upstream. It should not silently invent a competing receipt contract.

## Fixture scenarios

The preview catalog is returned by `GET /api/assurance/scenarios`.

| Scenario | Expected result |
|---|---|
| `valid-receipt` | accepted fixture receipt; projected settlement release |
| `tampered-trace` | rejected; trace content no longer hashes to the receipt-bound hash |
| `wrong-mint` | rejected; payment observation reports wrong mint |
| `wrong-payee` | rejected; payment observation reports wrong payee |
| `duplicate-replay` | rejected; replay store and receipt idempotency detect reuse |
| `refund-gate-failed` | rejected for reputation/payout; projected settlement refund |
| `authorization-denied` | blocked before payment; no receipt is emitted |

When the payment observation does not verify, the receipt's
`settlementProgramProof` reports `unobserved` fields and an `unverified`
confirmation rather than restating the expected transfer, so the canonical
`rap_receipt.settlement.unconfirmed` / `.payee_mismatch` diagnostics fire on the
receipt itself and not only on the payment adapter.

## What is simulated, read-only, blocked, or approval-gated

| State | In this preview |
|---|---|
| Simulated | Arena turns, AUDD payment observation fixture, receipt fixture, settlement decision |
| Read-only | Devnet program IDs and local PDA derivation metadata already in `core/chain.py` |
| Blocked | mainnet, live value, wallets, secrets, signing, custody, RPC, transaction submission, external deployment, official-mint observation, grant evidence |
| Separately approval-gated | Any real Solana devnet write, live payment, wallet/RPC scope, spend cap, or externally hosted launch |

## Contribution path

1. Add the smallest deterministic fixture under `fixtures/assurance/`.
2. State the boundary in the fixture or its README: what is simulated, what is
   read-only, what is blocked, and what evidence it does **not** prove.
3. Add an executable test in `tests/test_arena.py` that calls `core.assurance` or
   `/api/assurance` and asserts observable accept/refuse behavior.
4. Run:

```bash
python3 tests/test_arena.py
python3 tools/validate_adl.py
python3 tools/graph_lint.py
```

Do not add wallet helpers, RPC clients, transaction builders, custody, or live
payment paths to this preview.
