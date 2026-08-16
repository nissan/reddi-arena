# Reddi Arena — Findings from `A1` (schema validation pass)

**Date:** 2026-08-05
**Schema:** `public/downloads/ADL-v0.2.schema.json` from `nissan/reddi-agent-protocol@main`
**sha256:** `679a5c3ecfb18f80374aff59190456ea51b94f845ee9d84a3e96f419100af0ed`
**Method:** `jsonschema` Draft 2020-12 validation of both reference documents.

**Result:** 65 and 54 errors on first pass; 0 and 0 after correction. Both
reference documents now validate.

These are implementation reports from a downstream consumer, filed per the
one-way canonicality rule. None of them proposes changing ADL unilaterally.

---

## Drift corrected in the Arena documents (not spec issues)

Reconstructing ADL from prose got these wrong. Recording them because they are
exactly the mistakes any new implementer working from the whitepaper will make,
which makes them useful documentation feedback.

| # | Assumed | Actual |
|---|---|---|
| D-01 | `sideEffect` | `sideEffects`, with mode enum including `network`, `messaging`, `shell`, `filesystem`, `mcp`, `multiple` |
| D-02 | `retry` | `retryPolicy` |
| D-03 | `timeout.onTimeout` | `timeout.behavior` (`fail-closed`/`cancel`/`retry`) |
| D-04 | Dotted ids (`vault.seal`) | `^[a-zA-Z][a-zA-Z0-9_\-]*$` — **no dots permitted** |
| D-05 | `citation: required` | `citationRequired: <boolean>` |
| D-06 | `sourceCheck: required` | `sourceCheck: {required, expectation}` object |
| D-07 | `sourceRef: file://…` | `file:…`, plus a **separate required `path`** for file sources |
| D-08 | evalGate free-form | `rule`, `appliesTo.scope`, `evidence.{ref,schema}`, `onFailure.{completion,defaultStatus}` all required |
| D-09 | severity `major` | enum is `info`/`warning`/`error`/`critical` |
| D-10 | policy `scope: {match: current}` | `scope: {type, value}` with a closed type enum |
| D-11 | enforcement `pre-invocation` | `before-execution`/`during-execution`/`after-execution`; target enum `static-validator`/`runtime-adapter`/`policy-engine`/`human-review` |
| D-12 | `memory.retention` object | `retention` is a **string**; `scope` is a separate enum field |
| D-13 | observability free-form | requires `events`/`summaries`/`destinations`/`retention`/`redaction`, with a **closed 14-member event-name enum** |
| D-14 | `recovery.rollback: dry-run-disable` | `recovery.{disable,restart}` objects; `rollback` lives under deployment |
| D-15 | `harness` required = instructions only | **`harness.runtime` is also required** |

## Spec findings worth an upstream conversation

### F-001 — Seller-side `charge` intents escape the authority envelope

**STATUS: DUPLICATE — already known.** `docs/AGENT-TEAM-DELEGATION-EXAMPLES.md`
in the lab records this as ADL v0.3 candidate #1 and #2, in almost the same
words. My contribution is not the discovery; it is the executable reproduction
and the ablation table below, which the existing note does not have. File as
evidence attached to the existing item, not as a new finding.

**My first draft of this finding over-claimed. Running the official conformance
checker narrowed it.** Recording both, because the correction is the point.

*What I claimed:* a `charge` intent with only `id`/`direction`/`maxAmount`/
`currency`/`rails` passes at Level 3.

*What is actually true:* the conformance checker catches that document — it
requires `extensions.x402.intents[*].policyRefs`, `extensions.receipts.required=true`,
`extensions.receipts.refs`, `extensions.reputation.emitSignals`, and the Level 3
observability events. The minimal fixture achieves **Level 0, status fail**.

*The residual gap, isolated by ablation from a passing Level 3 document:*

| Ablation on a `direction: charge` intent | Achieved level |
|---|---|
| baseline, full envelope | 3 — pass |
| remove `authority` | **3 — pass** |
| remove `scope` | **3 — pass** |
| remove `purpose` | **3 — pass** |
| remove `requireReceipt` | **3 — pass** |
| remove `receiptRef` | **3 — pass** |

So the gap is real but specific: **the authority envelope that `spend` and
`refund` intents must satisfy is not required of `charge` intents.** A seller
can reach Level 3 with a fee-taking intent carrying no principal, spender,
expiry, revocation path, or audit binding — as long as it declares `policyRefs`,
receipts, and reputation signals.

This matters because `charge` is the *marketplace* direction. Every specialist
listing in a RAP market is a charge intent, and Level 3 is the tier that gates
market participation.

**Repro:** `fixtures/negative/charge-intent-unbounded.yaml` for the schema case;
the ablation table above for the conformance case, reproducible from
`adl/mercenary-source-auditor.adl.yaml` by deleting any one field.

### F-006 — Level 3 does not constrain the declared rail

Ablation also shows a `charge` intent with `rails: [solana]` and
`maxAmount: "999999.00"` achieves **Level 3 pass**. The spec's own table lists
live rails as gated "before a separately reviewed lane", so this is arguably by
design — the conformance checker is not the audit lane.

The consequence for any consumer: **"achieved Level 3" does not imply dry-run
only.** Arena cannot use conformance level as its safety gate and must inspect
`rails` separately. Worth stating explicitly in the spec prose, because Level 3
reads like a safety tier and is not one.

### F-002 — Currency enum excludes non-monetary units

`currency` is closed to `USD`/`USDC`/`EUR`/`GBP`. A game economy using
non-redeemable arena credits has nowhere to put them, so the Arena is forced to
either denominate in `USDC` on the dry-run rail — which *looks* like real money
in every downstream artifact — or push the whole economy into an `x-` extension
and lose the payment semantics being demonstrated.

This is likely to bite any non-financial x402 use case: loyalty points, internal
chargeback units, test currencies. Worth considering a `TEST`/`CREDIT` member or
an explicit `unit` escape hatch.

### F-003 — `x402-dry-run` is a rail, not a mode

Because the safe rail is a member of the same enum as `solana`/`base`/`stripe`,
"is this document safe to execute" requires inspecting every `rails` array in
every intent and authority block. A top-level `enabled`/`livePaymentAccess`
style flag would make the safety property checkable in one place. The Arena
implements this as an external guard, which is a workaround, not a fix.

### F-004 — WITHDRAWN

*Was:* `citationRequired: true` alongside `expectation: not-citable` reads as a
contradiction.

*Withdrawn:* `specs/ADL-v0.2.md` explains it directly — untrusted and unknown
sources must still require citation and source-check evidence so they stay
review-visible and cannot silently become trusted completion evidence. The
prose is clear; I had only the schema. Recorded as a withdrawal rather than
deleted, because "the implementer who read only the schema got this wrong" is
itself mild evidence for schema-adjacent commentary.

### F-004a — original note, retained for context

The conditional forces `citationRequired: true` for `untrusted` and `unknown`
trust, alongside `expectation: not-citable`. The intended reading is presumably
"any use must be attributed, but the source is inadmissible as approved
evidence." As written, the two field names read as a contradiction and the first
instinct of an implementer is to set `citationRequired: false`. A note in the
prose spec would prevent that.

### F-005 — `policy.scope.type` and `paymentScope.type` use different enums

`paymentScope.type` includes `service`; `policy.scope.type` does not. A payment
policy therefore cannot mirror the scope type of the intent it governs, which
weakens the "policy must match the exact resource and scope" requirement. The
mercenary uses `resource` as the nearest available match.

---

## Plan corrections required

### PC-01 — Arena must consume `@reddi/agent-protocol`, not reimplement it

The protocol package already ships 47 modules, including `receipts.ts`,
`receipt-evidence-binding.ts`, `policy.ts`, `buyer-authority-policy.ts`,
`evidence-archive.ts`, `attestation-reputation.ts`,
`offchain-reputation-preview.ts`, `discovery-source.ts`, and
`source-trust-conformance-matrix.ts`.

Several Arena issues were scoped as if these did not exist. They should be
rewritten as *integration* work:

| Issue | Was | Should be |
|---|---|---|
| `C3` | Build a buyer policy engine | Integrate `buyer-authority-policy` |
| `C6` | Emit and validate receipts | Integrate `receipts` + `receipt-evidence-binding` |
| `C7` | Implement attestation | Integrate `attestation-reputation` |
| `C8` | Enforce reputation eligibility | Integrate `offchain-reputation-preview` |
| `C1` | Build discovery | Integrate `discovery-source` |

This materially shrinks P2 and P3 and strengthens the analyst's "cut the
programme down" question — much of SL-C may be a thin adapter rather than an
epic.

### PC-02 — `relevance_only_not_trust` already exists as a vocabulary term

`packages/agent-protocol/src/ranking-explainability.ts` implements the
Discover-stage explainability block the Arena market surface was going to invent,
including the all-eight-gates array where `not_evaluated` never counts as passed.
The Arena mercenary market should render that model directly.

### PC-03 — The context pack understated implementation maturity

The pack described many surfaces as static or report-only. `STATUS.md` shows
shipped read models, test suites in the hundreds, and evidence directories. The
Arena plan's phase sequencing assumed a thinner base. **This cuts against the
programme's own claims-discipline principle in the opposite direction from
usual** — understating maturity is safer than overstating it, but it still
produced a wrong plan.

---

## Conformance evidence (official checker)

Run from the v0.2.0-beta bundle:
`python3 scripts/adl_v02_conformance.py <doc>`

| Document | Requested | Achieved | Status |
|---|---|---|---|
| `antweight-vault-defender` | 1 | 1 | pass |
| `mercenary-source-auditor` | 3 | 3 | pass |
| `charge-intent-unbounded` (negative) | 3 | 0 | fail |

Both reference documents initially **passed schema validation but failed
conformance**, missing required observability events (`task.failed` for L1;
`model.called`, `policy.checked`, `reputation.signal.emitted` for L2/L3). That
distinction — schema-valid is not conformance-passing — is precisely what issue
`A7` is about, and it is now demonstrated rather than asserted.

---

## Further plan corrections

### PC-04 — There are five conformance levels, not four

The Arena league mapping used 0–3. Level 4 exists: *production deployment
compatible*, requiring a hosted/serverless/platform-native/openclaw runtime
target, `deployment.environment`, `deployment.rollback`, `recovery.disable`, and
`deployment.health.checked` / `adapter.loss.reported` events.

`A7` must map five tiers. Level 4 is a natural "Pro/Hosted" division for
operators running persistent bots rather than local ones.

### PC-05 — The spec forces the league structure, and my ruleset was wrong

**Level 1 explicitly forbids the payment/reputation extension.** Payment
capability is only permitted at Level 3 and above.

Therefore a Level 1 Antweight bot **cannot legally carry a purse**. The Vault
ruleset as drafted — Antweight matches with purses in P1 — is not implementable
without pushing every rookie to Level 3.

This is a better design than the one I wrote:

| League | Level | Economy |
|---|---|---|
| Rookie | 1 | No purse. Glory only. Local runnable. |
| Open | 2 | No purse. Provider-portable; compatibility reports. |
| Title | 3 | Purses, mercenary hiring, receipts, reputation. |
| Pro/Hosted | 4 | Hosted runtimes, deployment readiness, rollback. |

The progression is *derived from the spec* rather than invented, which makes the
teaching claim much stronger: a player who wants to bet has to earn payment
conformance first. Purse mechanics move from P1 to P2, and P1 gets simpler.

### PC-06 — The receipt-integrity validator already exists and is stronger than my design

`scripts/rap_receipt_validator.py` (741 lines) and
`rap_receipt_integrity_benchmark.py` ship in the bundle. The benchmark reports
`status: pass`, 10 required layers, 14 threat cases (13 negative), 5 stable
diagnostic contracts.

The ten layers are: `delegatedAuthority`, `resourceAuthorization`,
`paymentEvidence`, `settlementProgramProof`, `serviceOutcome`, `evalEvidence`,
`replayIdempotency`, `privacyAccounting`, `disputeState`, `rollbackHold`.

Its acceptance rule states the principle better than my ruleset did: payment
settlement alone cannot become service success, delegated authority, reputation
eligibility, dispute closure, or accounting acceptance.

`C6` is therefore integration, not construction — and the Arena's Vault scoring
should adopt the ten-layer taxonomy directly. The 14 threat cases (replay,
wrong-payee, paid-but-denied) become arena exploit scenarios for free.

### PC-07 — Motivation is stronger than the plan stated

The project page cites USENIX Security 2026 finding security-rule violations in
all fifteen major x402 payment facilitators. That is the strongest available
argument for why an adversarial arena is worth building: the failure mode being
tested is empirically endemic, not hypothetical. It belongs in the README's
opening, not buried in a roadmap rationale.

### PC-08 — Spec home is moving

The canonical spec is at `github.com/reddinft/reddiagent-lab`, going public with
tagged release `v0.2.0-beta`. Arena's `F3` (one-way canonicality workflow)
should pin against that repo's tagged release rather than the vendored copy in
the product repo, once public.


---

## Findings added after reading the lab repo (public 2026-08-05)

### F-007 — There is no price-discovery field, which blocks the mercenary market

Recorded in the lab as v0.3 candidate #4 and confirmed against the schema:
`maxAmount` is a **cap, not a quoted price**. Neither ADL v0.2 nor the A2A card
mapping can express "this service costs X per task".

This is not a cosmetic gap for the Arena — the mercenary market's entire premise
is specialists advertising a price a competitor pays from a fixed purse. Without
a price field, a listing can only say "will not charge more than 25", which makes
draft-time budget comparison between rival specialists impossible. The Arena
would have to invent an `x-arena.price` field, which means the single most
load-bearing number in the game economy lives outside canonical ADL.

**This is the strongest argument the Arena makes for a v0.3 price field**, and
arguably the most valuable thing the whole proposal surfaces.

### F-008 — Seller-side vocabulary gaps bite the arena directly

Also v0.3 candidate #3 in the lab: `authority.spender` on the charge side holds
the party *being charged*; there is no `payment.intent.received` counterpart to
`payment.intent.created`; and `budget-check` reads as "do not overspend" where a
seller's honest gate is "do not overcharge".

An arena with a live mercenary market is an unusually good forcing function for
fixing this, because both sides are played simultaneously by real people who will
notice the asymmetry immediately.

### F-002 status update

No mention of the currency-enum constraint anywhere in the lab specs or docs.
This one appears genuinely novel. Non-monetary units (game credits, loyalty
points, test currencies) have nowhere to live.

---

## Strategic corrections — these supersede the plan

### PC-09 — The programme conflicts with the launch critical path

`docs/TRACKS.md` states that three commitments share one end-to-end story: the
2026-08-31 launch epic (#386), the AUDD grant M1 evidence chain (#616–#619,
#632–#635), and the Colosseum Eternal Challenge closing in early September. One
working AUDD-denominated, x402-escrowed, RAP-receipted devnet payment demo
satisfies all three, and a slip in protocol-repo devnet evidence slips all three
together.

Today is **2026-08-05. That is 26 days.**

A 16-epic, 36-issue, 5-phase Arena programme is not compatible with that window,
and nothing in it is on the critical path for any of the three commitments. The
analyst brief asked whether this plan repeats the failure mode the 2026-08-01
correction stopped. With the lab repo visible, the answer for the programme as a
whole is **yes — recommend not running it as scoped.**

### PC-10 — Two Arena issues violate a standing instruction

The 2026-07-26 direction reset says: do not add new `*_packet` / `*_gate` /
`*_handoff` / `*_signoff` scripts until automation is explicitly re-authorized.

Arena issues `F1` (devnet projection) and `F2` (external tester evidence packet)
propose exactly that, and `scripts/beta_external_tester_mvp_packet.py` already
exists. **Both should be struck**, not rescheduled. My original framing — that
the Arena would generate the tester evidence the ladder still owes — was wrong
on two counts: the packet machinery exists, and building more of it is currently
prohibited.

### PC-11 — The real insertion point is the learning path, not a programme

`docs/LEARNING-PATH.md` sequences ten lessons: what is an agent, model versus
harness, simple local ADL, tool contracts, policies and eval gates, dry-run
traces, provider compatibility, payment intent and dry-run receipt, reputation
signals, deployment and adapters. Its teaching rule is that **every lesson should
end with a visible artifact the builder can run or inspect.**

The Arena league ladder is a near-exact mirror of that sequence, which is not a
coincidence — both are derived from the conformance levels:

| Learning path lessons | Arena league |
|---|---|
| 1–4 model/harness/ADL/tools | Garage, L0 |
| 5–6 policies, eval gates, dry-run traces | Rookie, L1 |
| 7 provider compatibility | Open, L2 |
| 8–9 payment intent, receipts, reputation | Title, L3 |
| 10 deployment and adapters | Pro/Hosted, L4 |

The lab is the open spec home, aimed at agent-framework builders, and explicitly
intended to become community-maintained. `tutorials/` currently holds two files.
An arena is a community-building instrument, and a competitive capstone is a
much better fit as **lesson 11 of an existing learning path** than as a parallel
programme with its own swimlanes.

### F-009 — On-chain vs ADL price parity gap (strengthens F-007)

`programs/escrow/src/state.rs::AgentAccount` carries `rate_lamports`, set at
`register_agent` and mutable via `update_agent`. The on-chain registry treats a
specialist's quoted rate as a first-class field.

ADL v0.2 has no price field at all. The same protocol therefore expresses a
specialist's price **on-chain** but cannot express it in **the document that
defines the specialist**. A consumer building a listing from ADL alone must
either query chain state or invent an extension.

This is the strongest available argument for the F-007 price field: the need is
not hypothetical and not Arena-specific — the chain layer already committed to
it, and the declaration layer disagrees. Recommend attaching to the F-007 intake.
