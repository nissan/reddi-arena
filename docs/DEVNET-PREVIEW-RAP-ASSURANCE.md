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
refuses a fixture carrying it, and the verifier refuses it on both the expected
terms and the parsed transaction without echoing the mint back.

Canonical documents keep their exact canonical shape. The observation's
`evidence` object carries only `source` and `grantEligible`;
`policyDecision.reasonCodes` only carry codes from the closed
`ReddiPolicyReasonCode` set; and observation failures only carry codes from the
closed `SplTransferCheckedObservationFailureReason` union. Arena-only
disclosure lives outside those documents in
`adapters.paymentObservation.arenaPreviewLabels`
(`reddi.arena.devnet-preview-labels.v1`), and an Arena-specific refusal such as
the official-mint prohibition travels in `arenaRefusal` alongside the closest
truthful canonical `reason`.

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

`receiptArtifact.kind` classifies the emitted JSON from the document itself —
whether a payment was actually observed and whether the evidence layers are
canonically complete — never from the assurance verdict alone, and the UI
labels it with that classification:

| `kind` | Meaning |
|---|---|
| `receipt` | Observed payment, complete layers, assurance accepted |
| `verified-rejected-receipt` | Observed payment and complete layers, but assurance rejected or held on semantic grounds (`rap_receipt.eval.failed`, `.replay.duplicate_payment`, a tampered trace) |
| `invalid-candidate` | No verified observation or canonically incomplete layers |
| `not-emitted` | Denied before payment; no candidate exists |

When the payment observation does not verify, the artifact is an
`invalid-candidate`. Every evidence field that would have to be *observed* is
absent rather than restated from the expected terms: `settlementProgramProof`
omits each observable field, `paymentEvidence.payee` / `.amount` and
`payment.paymentProofRef` / `payment.amount` are null, and
`replayIdempotency.idempotencyKey` is absent. The canonical
`rap_receipt.payment.invalid`, `.settlement.invalid` and `.replay.invalid`
diagnostics then report incomplete evidence, and that same structural pass is
what classifies the artifact. Semantic cross-checks never run on an incomplete
layer, so the candidate is never accused of a mismatch against a field that was
simply never observed.

The quoted terms the payment was *supposed* to satisfy are not evidence, so
they live in Arena-owned `metadata.expectedPaymentTerms` (and in the canonical
`policyDecision.quotedAmount` and `paymentEvidence.requiredHash` digest), never
in `paymentEvidence` values or the settlement proof.

A fixture that is unreadable, unparseable, or the wrong shape is a server-side
defect, not caller error: `load_payment_fixture()` validates the file, its
required top-level keys, its expected-terms keys, the base-unit amount, and the
`parsedTransaction` paths every scenario reaches into (a parsed
`TransferChecked` instruction and the `postTokenBalances` entry for its
destination account). Each failure raises `AssuranceIntegrityError`, which
`/api/assurance` answers with a sanitized 500 plus a bounded server-side log
line. Only malformed client input (an unknown or non-string `scenario`) is
a 400.

The refusal scenarios break the one transfer that satisfies the expected
payment terms — the transfer an observer would otherwise accept — located
semantically rather than by position, so a decoy transfer earlier in the
transaction cannot absorb the mutation. Each scenario then re-observes its own
mutated fixture and requires the intended canonical refusal
(`wrong_mint`, `wrong_payee`) before serving it. If a contributed fixture
cannot demonstrate its refusal — it already holds the value the scenario needs
to break, it offers no single transfer matching the expected terms, or the
mutation fails to change the verdict — the scenario refuses as an integrity
fault rather than presenting a verifiable payment under a "wrong mint" or
"wrong payee" card.

When a payment *was* observed, `replayIdempotency.idempotencyKey` extends the
verifier's own consume-once replay key — network, signature, and the exact
matched outer or inner instruction index — so an inner-instruction fixture
never claims index `0`.

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
