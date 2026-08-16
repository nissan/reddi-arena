<!-- GENERATED from plan/backlog.yaml by tools/render_plan.py — do not hand-edit. -->

# Reddi Arena — Backlog (plan-v0.4-superseded)

Every issue carries: rationale, dependencies, an explicit boundary (what it does **not** authorize), tasks, acceptance criteria, and the automated tests that constitute doneness.

---

## E01 — ADL Arena Profile and Fixture Corpus

**Lane:** SL-A Spec and Conformance  |  **Phase:** P0 Foundry

**Outcome:** A competitor bot is expressible as a schema-valid ADL v0.2 document, and a corpus of valid/invalid fixtures exists that the lab can adopt.

### A1 — Validate reference ADL documents against the published v0.2 schema

*Why:* The reference bots were drafted from prose, not from the schema. Until validated they are hypotheses, not artifacts.

*Depends on:* none

*Boundary:* Validation proves document shape only. It authorizes no execution.

**Tasks**

- [ ] Fetch specs/ADL-v0.2.schema.json from the published downloads or lab repo
- [ ] Pin schema by sha256 into the repo as a vendored fixture
- [ ] Run both reference ADLs through a Draft 2020-12 validator
- [ ] Correct every field-name and enum drift found; log each drift as a finding
- [ ] File drift findings upstream to the lab as implementation reports

**Acceptance criteria**

- [ ] Both reference ADL documents validate with zero schema errors
- [ ] The pinned schema hash is recorded and checked in CI
- [ ] Every drift correction has a one-line changelog entry citing the schema path

**Doneness tests**

- `T-001` (contract) — Both reference ADLs validate against the pinned v0.2 schema with zero errors
- `T-002` (determinism) — Vendored schema sha256 matches the pinned upstream value; CI fails on drift

### A2 — Build the Arena negative-fixture corpus

*Why:* Invalid documents must fail for the stated reason, not incidentally.

*Depends on:* A1

*Boundary:* Fixtures are review artifacts; they do not define new ADL semantics.

**Tasks**

- [ ] Author >= 20 invalid fixtures, one per intended failure mode
- [ ] Cover bare-string instructions, missing policyRef on a risky tool, duplicate tool/function IDs, sourceRef prefix mismatch, unprefixed extension namespace
- [ ] Assert each fixture fails with the expected diagnostic code, not merely "invalid"

**Acceptance criteria**

- [ ] Every negative fixture fails validation
- [ ] Every negative fixture asserts a specific diagnostic, not a generic failure
- [ ] Zero negative fixtures pass silently

**Doneness tests**

- `T-003` (contract) — Every negative fixture fails validation
- `T-004` (contract) — Each negative fixture produces its expected diagnostic code, not a generic error

### A3 — Define the arena-profile extension namespace

*Why:* Arena needs match-specific metadata (format, class, fuel cap) without polluting canonical ADL.

*Depends on:* A1

*Boundary:* An x- namespace is Arena-local. It confers no canonical status and must not carry payment-like semantics.

**Tasks**

- [ ] Specify x-arena namespace fields (format, declaredClass, fuelCap, seasonId)
- [ ] Assert strict validation rejects unprefixed arena keys
- [ ] Document the promotion path if the lab later adopts any field

**Acceptance criteria**

- [ ] x-arena fields validate under strict mode
- [ ] An unprefixed "arena:" key fails strict validation
- [ ] No payment, spend, or authority semantics exist in x-arena

**Doneness tests**

- `T-005` (contract) — x-arena namespaced fields pass strict validation
- `T-006` (adversarial) — Unprefixed arena keys and payment-like semantics under x-arena are rejected

---

## E02 — Deterministic Weigh-In and Capability Hash

**Lane:** SL-A Spec and Conformance  |  **Phase:** P0 Foundry

**Outcome:** Weight class is a reproducible pure function of a validated ADL document.

### A4 — Specify and freeze the AU weight formula v0.1

*Why:* If weight is not deterministic and independently recomputable, the whole competitive frame collapses.

*Depends on:* A1

*Boundary:* A weight certificate authorizes nothing; it is an eligibility input only.

**Tasks**

- [ ] Publish the AU table and class bands as a versioned spec document
- [ ] Implement the calculator as a pure function with no IO, clock, or randomness
- [ ] Emit a capability hash over the canonicalised certificate
- [ ] Version the formula so historical certificates remain interpretable

**Acceptance criteria**

- [ ] Same document yields identical AU and hash across runs, machines, and key order
- [ ] Certificate records weightsVersion so old results stay interpretable
- [ ] Reordering YAML keys does not change the hash

**Doneness tests**

- `T-007` (determinism) — Identical AU and capability hash across repeated runs
- `T-008` (property) — YAML key reordering and whitespace changes never alter the capability hash
- `T-009` (unit) — Reference bot weighs exactly 62 AU; mercenary exactly 91 AU

### A5 — Implement coupled weight for hired specialists

*Why:* The class-bump-on-hire tradeoff is the core strategic mechanic and must be computed identically by every implementation.

*Depends on:* A4

*Boundary:* Computing coupled weight does not engage a specialist or move value.

**Tasks**

- [ ] Apply the coupling factor and per-engagement overhead
- [ ] Recompute fielded class and flag classBumped
- [ ] Handle transitive hires (a specialist that itself hires) with a depth cap

**Acceptance criteria**

- [ ] Hiring a specialist increases fielded AU and can change fielded class
- [ ] A hire that would exceed the entered class is rejected at draft, not mid-match
- [ ] Transitive hire depth beyond the cap is refused with a stated reason

**Doneness tests**

- `T-010` (unit) — Hiring the reference mercenary moves the reference bot 62 to 127 AU, Antweight to Beetleweight
- `T-011` (integration) — A hire breaching the entered class is refused at draft with the AU delta stated
- `T-012` (property) — Transitive hire depth beyond the cap is refused; no unbounded recursion

### A6 — Anti-gaming review of the weight formula

*Why:* Any scoring function invites optimisation against its own artifacts.

*Depends on:* A4

*Boundary:* Review output is advisory to formula v0.2; it does not change v0.1 mid-season.

**Tasks**

- [ ] Attempt to farm the policy hygiene credit with no-op deny policies
- [ ] Attempt to understate contextWindow while relying on more at runtime
- [ ] Attempt to hide capability in skills or instructions rather than tools
- [ ] Produce a written exploit report with recommended v0.2 changes

**Acceptance criteria**

- [ ] No-op policy padding cannot reduce AU below the declared floor
- [ ] Understated declarations are detectable at runtime by E13 binding
- [ ] Exploit report exists and is linked from the formula spec

**Doneness tests**

- `T-013` (adversarial) — No-op deny-policy padding cannot push AU below the declared floor
- `T-014` (adversarial) — Capability hidden in skills or instructions still fails runtime binding

---

## E03 — Conformance-to-League Mapping

**Lane:** SL-A Spec and Conformance  |  **Phase:** P1 First Blood

**Outcome:** ADL conformance levels gate league entry, so players climb the spec ladder by playing.

### A7 — Map conformance levels to league tiers

*Why:* This is the teaching mechanism — players learn the spec by ranking up, not by reading it.

*Depends on:* A1, A4

*Boundary:* Reaching a tier grants match eligibility only. It never grants provider, network, wallet, or rail access.

**Tasks**

- [ ] {'Bind five tiers': 'L0 garage entry, L1 Rookie, L2 Open, L3 Title, L4 Pro/Hosted'}
- [ ] Enforce that purses and hiring require L3, because L1/L2 forbid the payment extension
- [ ] {'Inspect declared rails separately': 'achieved L3 does not imply dry-run only (F-006)'}
- [ ] Run the conformance checker at registration and store the verdict
- [ ] Reject documents whose requestedLevel exceeds their achieved level

**Acceptance criteria**

- [ ] A Level-1 document cannot enter a Title fight or carry a purse
- [ ] requestedLevel above achieved level is rejected with the failing requirement named
- [ ] The tier verdict is recorded in the weigh-in certificate

**Doneness tests**

- `T-015` (contract) — A Level-1 document is refused entry to a Title fight
- `T-016` (contract) — requestedLevel above achieved level is rejected naming the failing requirement

### A8 — Guard the known v0.2 charge-intent conformance gap

*Why:* The lab records that charge intents can escape intended Level-3 enforcement. Arena must not inherit that hole.

*Depends on:* A7

*Boundary:* The guard is Arena-local compensating control. It does not fix the spec and must not be described as fixing it.

**Tasks**

- [ ] Enumerate intent shapes that escape Level-3 enforcement
- [ ] Add an Arena-side pre-draft check refusing under-constrained charge intents
- [ ] File the reproduction upstream as a v0.3 candidate

**Acceptance criteria**

- [ ] An under-constrained charge intent is refused at draft with a stated reason
- [ ] The guard is documented as compensating, not as a spec fix
- [ ] An upstream issue exists with a minimal reproduction

**Doneness tests**

- `T-017` (adversarial) — An under-constrained charge intent is refused at pre-draft check
- `T-018` (contract) — The charge-intent guard is documented as compensating, never as a spec fix

---

## E04 — Match Engine and Bounded Execution

**Lane:** SL-B Arena Runtime  |  **Phase:** P1 First Blood

**Outcome:** Two ADL-defined bots run a complete match inside a fail-closed sandbox.

### B1 — Build the bounded execution lane

*Why:* Execution is the one place the declaration becomes action, so it is the one place fail-closed must be provably enforced.

*Depends on:* A1

*Boundary:* The lane is the ONLY component permitted to execute, and only for declared, policy-matched, locally-bound capabilities.

**Tasks**

- [ ] Implement a runtime binder that refuses any undeclared capability
- [ ] Default network egress to deny; require explicit allowlist entries
- [ ] Refuse persistent/external memory backends unless separately approved
- [ ] Emit a structured refusal event for every blocked attempt

**Acceptance criteria**

- [ ] A tool absent from the ADL cannot be invoked
- [ ] A tool present but lacking a matching policyRef cannot be invoked
- [ ] Network egress with an empty allowlist is refused and logged
- [ ] Every refusal emits an event with subject, resource, action, and reason

**Doneness tests**

- `T-019` (adversarial) — An undeclared tool cannot be invoked at runtime
- `T-020` (adversarial) — A declared tool lacking a matching policyRef cannot be invoked
- `T-021` (integration) — Egress with an empty allowlist is refused and logged
- `T-022` (contract) — Every refusal emits an event carrying subject, resource, action and reason

### B2 — Implement the turn loop and match lifecycle

*Why:* Deterministic lifecycle is the precondition for replayable evidence.

*Depends on:* B1

*Boundary:* Lifecycle events are evidence, not adjudication.

**Tasks**

- [ ] Define match states and legal transitions
- [ ] Enforce turn limits and per-turn timeouts from the declared harness
- [ ] Handle competitor crash, timeout, and malformed output as defined outcomes

**Acceptance criteria**

- [ ] Every match terminates in a defined terminal state
- [ ] A crashed or hung competitor forfeits rather than hanging the match
- [ ] Illegal state transitions are impossible, not merely discouraged

**Doneness tests**

- `T-023` (property) — Every match reaches exactly one defined terminal state
- `T-024` (integration) — Crashed or hung competitors forfeit without hanging the match
- `T-025` (property) — Illegal lifecycle transitions are unreachable

### B3 — Provider abstraction across declared model providers

*Why:* Provider neutrality is an ADL promise; the Arena is where it either holds or visibly breaks.

*Depends on:* B1

*Boundary:* Declaring a provider is not credential authorization. Missing credentials fail closed rather than silently falling back.

**Tasks**

- [ ] Honour the declared preference order without inventing fallbacks
- [ ] Report degraded semantics when a provider lacks a declared requirement
- [ ] Run the same bot across at least two providers and diff behaviour

**Acceptance criteria**

- [ ] Undeclared fallbacks are never used
- [ ] A provider missing structuredOutput reports degraded, not silent success
- [ ] Cross-provider divergence is measured and published, not hidden

**Doneness tests**

- `T-026` (contract) — Undeclared fallback providers are never selected
- `T-027` (contract) — A provider missing a declared requirement reports degraded rather than succeeding silently
- `T-028` (e2e) — Cross-provider behavioural divergence is measured and published

---

## E05 — Fuel Metering and Trace Emission

**Lane:** SL-B Arena Runtime  |  **Phase:** P1 First Blood

**Outcome:** Tokens are a scarce in-match resource and every match yields a complete trace.

### B4 — Implement token fuel accounting

*Why:* Efficiency becomes a skill only if fuel is metered and enforced.

*Depends on:* B2

*Boundary:* Fuel accounting is deterministic bookkeeping, not billing.

**Tasks**

- [ ] Meter prompt and completion tokens per turn against the declared cap
- [ ] Enforce the budget-check eval gate at the declared threshold
- [ ] Define sputter behaviour when fuel is exhausted mid-turn

**Acceptance criteria**

- [ ] Exceeding the declared fuel cap fails the budget gate
- [ ] Fuel exhaustion produces a defined outcome, never an exception
- [ ] Accounting reconciles exactly with the emitted trace

**Doneness tests**

- `T-029` (unit) — Exceeding the declared fuel cap fails the budget-check gate
- `T-030` (integration) — Fuel exhaustion mid-turn produces the defined sputter outcome, never an exception
- `T-031` (property) — Fuel accounting reconciles exactly with the emitted trace for every match

### B5 — Emit conformance-aligned trace events with redaction

*Why:* The trace is the evidence substrate for receipts, learning mode, and disputes.

*Depends on:* B2

*Boundary:* A trace records what happened. It does not by itself establish task success or reputation eligibility.

**Tasks**

- [ ] Emit the declared observability event set for every match
- [ ] Apply declared redaction to prompt and output payloads
- [ ] Assert no secret, key, or canary value can reach the trace

**Acceptance criteria**

- [ ] Every match emits a complete, ordered, replayable event stream
- [ ] Redaction rules from the ADL are applied, not defaults
- [ ] No credential or canary value appears anywhere in a stored trace

**Doneness tests**

- `T-032` (contract) — Every match emits a complete ordered replayable event stream
- `T-033` (contract) — ADL-declared redaction rules are applied rather than engine defaults
- `T-034` (adversarial) — No credential or canary value appears in any stored trace

---

## E06 — Vault Arena Format

**Lane:** SL-B Arena Runtime  |  **Phase:** P1 First Blood

**Outcome:** One complete, balanced, adjudicable arena format ships end to end.

### B6 — Implement Vault attack/defend scoring

*Why:* A format nobody can argue about is worth more than five ambiguous ones.

*Depends on:* B2, B4

*Boundary:* Scoring is deterministic given a trace; it does not judge intent.

**Tasks**

- [ ] Implement canary-based secret-extraction detection
- [ ] Score defence holds, successful extractions, and fuel efficiency
- [ ] Define draws, double-forfeits, and mutual-extraction tie-breaks

**Acceptance criteria**

- [ ] Identical traces always produce identical scores
- [ ] Every terminal state has exactly one defined scoring outcome
- [ ] A secret leaked in any form the canary detects scores as extraction

**Doneness tests**

- `T-035` (determinism) — Identical traces always produce identical scores
- `T-036` (property) — Every terminal state maps to exactly one scoring outcome
- `T-037` (adversarial) — Secret leakage in encoded, partial, or paraphrased form still scores as extraction

### B7 — Format balance harness

*Why:* Without a balance harness, the first dominant strategy ends the format's competitive life.

*Depends on:* B6

*Boundary:* Balance findings inform format v0.2; they do not retroactively alter results.

**Tasks**

- [ ] Run round-robin baselines across archetype bots
- [ ] Measure first-mover advantage and attack/defence win asymmetry
- [ ] Publish the balance report with the season rules

**Acceptance criteria**

- [ ] Attacker/defender win split falls within the published tolerance band
- [ ] No single archetype exceeds the published dominance threshold
- [ ] The balance report is published before the season opens

**Doneness tests**

- `T-038` (e2e) — Attacker/defender win split stays inside the published tolerance band
- `T-039` (e2e) — No archetype exceeds the published dominance threshold

---

## E07 — Discover — Mercenary Market

**Lane:** SL-C RAP Economy  |  **Phase:** P2 Mercenary Market

**Outcome:** Specialists advertise bounded capability with traceable provenance.

### C1 — Integrate discovery-source into the specialist listing surface

*Why:* Discovery is where players first meet RAP's "relevance is not trust" rule.

*Depends on:* A1, A4

*Boundary:* A listing is a claim, not verified truth. Discovery grants no invocation permission and no publication.

**Tasks**

- [ ] Adopt discovery-source and ranking-explainability rather than reimplementing
- [ ] Render the relevance_only_not_trust vocabulary directly from the package
- [ ] Derive listings from validated ADL, never from free-text claims
- [ ] Record and display the provenance of every listing
- [ ] Show reputation state including "insufficient evidence"

**Acceptance criteria**

- [ ] A listing cannot claim a capability absent from its ADL
- [ ] Provenance is displayed for every listing
- [ ] Discovery never triggers invocation or publication as a side effect

**Doneness tests**

- `T-040` (contract) — A listing cannot advertise a capability absent from its ADL
- `T-041` (contract) — Provenance is present and displayed for every listing
- `T-042` (adversarial) — No discovery call triggers invocation or publication as a side effect

### C2 — Separate publication from discovery as an explicit gate

*Why:* The spec is emphatic that publication must never happen accidentally.

*Depends on:* C1

*Boundary:* Import, mapping, and export must never publish a live listing.

**Tasks**

- [ ] Make publication an explicit operator-approved action
- [ ] Assert no import/export path can publish
- [ ] Log every publication with approver identity

**Acceptance criteria**

- [ ] No code path publishes without explicit approval
- [ ] Publication events record the approver
- [ ] Export of a listing does not publish it

**Doneness tests**

- `T-043` (adversarial) — No import, mapping, or export path can publish a live listing
- `T-044` (contract) — Every publication event records an explicit approver identity

---

## E08 — Decide — Buyer Policy and the Draft Broker

**Lane:** SL-C RAP Economy  |  **Phase:** P2 Mercenary Market

**Outcome:** Hiring is a bounded policy decision under budget, trust, and authority constraints, resolved before the match starts.

### C3 — Integrate buyer-authority-policy as the hire decision engine

*Why:* Decide is the layer players most often skip conceptually, so the game must make it unavoidable and visible.

*Depends on:* C1, A5

*Boundary:* An allow decision permits a bounded engagement only. It never widens buyer authority beyond the operator-declared envelope.

**Tasks**

- [ ] Adopt buyer-authority-policy from @reddi/agent-protocol as the decision core
- [ ] Evaluate trust class, budget ceiling, rail, and approval posture
- [ ] Emit a machine-readable decision with reason codes for allow and deny
- [ ] Assert an external mandate can narrow but never widen local authority

**Acceptance criteria**

- [ ] Every hire attempt yields a recorded decision with reason codes
- [ ] A mandate attempting to widen local authority is rejected
- [ ] Exceeding the declared purse budget denies the hire

**Doneness tests**

- `T-045` (contract) — Every hire attempt produces a machine-readable decision with reason codes
- `T-046` (adversarial) — An external mandate attempting to widen local buyer authority is rejected
- `T-047` (unit) — A hire exceeding the declared purse budget is denied

### C4 — Implement the draft window and weigh-in recomputation

*Why:* The hire-versus-class tradeoff is the strategic heart of the game and must resolve deterministically before combat.

*Depends on:* C3, A5

*Boundary:* Draft outcomes bind eligibility only; no work or payment occurs at draft.

**Tasks**

- [ ] Open a bounded draft window with a hard close
- [ ] Recompute fielded weight on every hire and re-check class eligibility
- [ ] Refuse hires that would breach the entered class, with the AU delta shown

**Acceptance criteria**

- [ ] Fielded weight is recomputed and shown before the hire is committed
- [ ] A class-breaching hire is refused before the match, never mid-match
- [ ] The draft window closes deterministically and cannot be reopened

**Doneness tests**

- `T-048` (integration) — Fielded weight is recomputed and surfaced before a hire commits
- `T-049` (property) — No hire can take effect after the draft window closes
- `T-050` (adversarial) — The draft window cannot be reopened by any request path

---

## E09 — Prove — Escrow, Receipts and Attestation

**Lane:** SL-C RAP Economy  |  **Phase:** P2 Mercenary Market

**Outcome:** Purse and fees move only on the allowed success path, and every movement is bound to evidence.

### C5 — Implement dry-run escrow for purse and fees

*Why:* The purse teaches the single most important RAP lesson: payment success is not work success.

*Depends on:* C3

*Boundary:* Rail is pinned to x402-dry-run. livePaymentAccess is false. No wallet, facilitator, custody, or real value exists anywhere in this issue.

**Tasks**

- [ ] Lock both purses and any hire fees at match start
- [ ] Release only on completion.status=pass with required gates passed
- [ ] Implement refund, timeout, and dispute paths
- [ ] Assert no live rail can be selected even if declared

**Acceptance criteria**

- [ ] Transport success alone never releases escrow
- [ ] A failed required gate routes to refund or dispute, never payout
- [ ] Selecting any non-dry-run rail is refused
- [ ] Escrow accounting balances to zero across every terminal state

**Doneness tests**

- `T-051` (contract) — Transport success alone never releases escrow
- `T-052` (contract) — A failed required gate routes to refund or dispute, never to payout
- `T-053` (adversarial) — Selecting any rail other than x402-dry-run is refused
- `T-054` (property) — Escrow accounting balances to zero across every terminal state

### C6 — Integrate receipts and receipt-evidence-binding per match and engagement

*Why:* The receipt is the artifact an external analyst can actually check.

*Depends on:* C5, B5

*Boundary:* A receipt records that policy, payment reference, and evidence reference existed. It does not prove settlement finality or provider quality.

**Tasks**

- [ ] Adopt receipts and receipt-evidence-binding rather than reimplementing
- [ ] Populate the full v1 envelope including request/response hashes
- [ ] Bind evidenceRef to the stored match trace
- [ ] Fail closed on missing proof refs, malformed fields, or credential leakage

**Acceptance criteria**

- [ ] Every completed match and engagement emits a schema-valid receipt
- [ ] A receipt with a missing paymentProofRef fails validation
- [ ] No receipt ever contains credential material
- [ ] evidenceRef resolves to a retrievable trace

**Doneness tests**

- `T-055` (contract) — Every completed match and engagement emits a schema-valid reddi.receipt.v1
- `T-056` (contract) — A receipt missing paymentProofRef fails validation closed
- `T-057` (adversarial) — No receipt contains credential or wallet material
- `T-058` (integration) — evidenceRef on every receipt resolves to a retrievable trace

### C7 — Integrate attestation-reputation as the judge actor

*Why:* RAP already names a paid judge actor; the arena referee is that actor.

*Depends on:* C6

*Boundary:* An attestation is one evidence input. It cannot substitute for required eval gates or for payment proof.

**Tasks**

- [ ] Adopt attestation-reputation and hosted-attestation-claim from the package
- [ ] Define the judge as an ADL-declared agent with its own eval gates
- [ ] Record attestation state on every receipt
- [ ] Detect and handle judge unavailability and judge disagreement

**Acceptance criteria**

- [ ] Attestation state is present on every receipt
- [ ] A failed attestation blocks payout even when transport succeeded
- [ ] Judge unavailability produces a defined outcome, not an indefinite hang

**Doneness tests**

- `T-059` (contract) — Attestation state is present on every emitted receipt
- `T-060` (contract) — A failed attestation blocks payout even when transport succeeded
- `T-061` (integration) — Judge unavailability produces a defined outcome without indefinite hang

---

## E10 — Reputation — Commit-Reveal League Table

**Lane:** SL-C RAP Economy  |  **Phase:** P3 League and Learning

**Outcome:** Standing derives only from verified work, never from listings or payment alone.

### C8 — Integrate offchain-reputation-preview and enforce eligibility rules

*Why:* The spec is explicit that reputation must not mutate when policy failed or evidence is missing. This is the cleanest thing an analyst can audit.

*Depends on:* C6, C7

*Boundary:* Reputation is a derived signal within one season. It is not portable identity and carries no external warranty.

**Tasks**

- [ ] Adopt offchain-reputation-preview as the eligibility evaluator
- [ ] Gate mutation on policy pass, evidence present, attestation pass, payment proof verified
- [ ] Assert every ineligible path leaves standing unchanged
- [ ] Expose the eligibility verdict alongside every rating change

**Acceptance criteria**

- [ ] A match failing policy produces zero reputation change
- [ ] A match with a missing evidence ref produces zero reputation change
- [ ] Every rating change is traceable to a specific eligible receipt

**Doneness tests**

- `T-062` (contract) — A match failing policy produces zero reputation change
- `T-063` (contract) — A match with a missing evidence reference produces zero reputation change
- `T-064` (integration) — Every rating change traces to exactly one eligible receipt

### C9 — Implement commit-reveal scoring

*Why:* Rivals scoring rivals invites retaliation and copying; commit-reveal is the spec's answer and the arena is a natural stress test.

*Depends on:* C8

*Boundary:* Off-chain commit-reveal only in P3. On-chain projection is E15.

**Tasks**

- [ ] Commit score hashes before any reveal
- [ ] Enforce the reveal deadline and penalise non-reveal
- [ ] Detect copied scores and late-reveal advantage

**Acceptance criteria**

- [ ] No score is visible before the reveal window opens
- [ ] A non-revealed commit is penalised per published rule
- [ ] A reveal not matching its commit hash is rejected

**Doneness tests**

- `T-065` (adversarial) — No score is readable before the reveal window opens
- `T-066` (contract) — A non-revealed commit is penalised per the published rule
- `T-067` (contract) — A reveal not matching its commit hash is rejected

---

## E11 — Garage and Progressive Disclosure

**Lane:** SL-D Player Experience  |  **Phase:** P2 Mercenary Market

**Outcome:** A newcomer assembles a valid bot without reading the spec; an expert hand- writes ADL. Both produce the same artifact.

### D1 — Build the visual garage that emits ADL

*Why:* The garage is the on-ramp; if it emits anything other than canonical ADL, the whole proof is undermined.

*Depends on:* A1, A4

*Boundary:* The garage authors documents. It never executes or publishes them.

**Tasks**

- [ ] Emit schema-valid ADL from every UI state
- [ ] Show live AU weight and class as the player builds
- [ ] Surface validation errors in plain language with a spec link

**Acceptance criteria**

- [ ] Every reachable garage state emits a schema-valid document
- [ ] Weight updates live and matches the CLI calculator exactly
- [ ] Errors name the offending field and link to the governing spec section

**Doneness tests**

- `T-068` (property) — Every reachable garage state emits a schema-valid ADL document
- `T-069` (integration) — Garage-displayed AU matches the CLI calculator exactly
- `T-070` (contract) — Validation errors name the offending field and link a spec section

### D2 — Round-trip fidelity between visual and raw editing

*Why:* Experts will not adopt a tool that mangles their handwritten documents.

*Depends on:* D1

*Boundary:* Round-tripping preserves semantics; it does not validate intent.

**Tasks**

- [ ] Import a handwritten ADL into the visual editor without semantic loss
- [ ] Export and diff to confirm no silent field drops
- [ ] Report unsupported-in-UI semantics explicitly rather than discarding

**Acceptance criteria**

- [ ] Import then export is semantically lossless
- [ ] Any UI-unsupported field is reported, never silently dropped
- [ ] Comments and ordering loss is disclosed to the player

**Doneness tests**

- `T-071` (property) — Import then export is semantically lossless
- `T-072` (contract) — UI-unsupported fields are reported explicitly, never silently dropped

---

## E12 — Learning Mode — Replay Telemetry and Pit Crew

**Lane:** SL-D Player Experience  |  **Phase:** P3 League and Learning

**Outcome:** Losing a match reliably teaches the player something specific and actionable.

### D3 — Render the annotated match replay

*Why:* The replay is where a receipt and a trace become a learning experience instead of a compliance artifact.

*Depends on:* B5, B6

*Boundary:* The replay renders recorded evidence. It never reconstructs, infers, or embellishes what was not traced.

**Tasks**

- [ ] Render turn-by-turn fuel burn, tool calls, and gate outcomes
- [ ] Highlight the decisive moment that determined the result
- [ ] Show the opponent's approach only within the season's disclosure rules

**Acceptance criteria**

- [ ] Every rendered claim maps to a specific trace event
- [ ] No replay statement is unsupported by evidence
- [ ] Disclosure rules are enforced per season configuration

**Doneness tests**

- `T-073` (contract) — Every rendered replay claim maps to a specific trace event
- `T-074` (contract) — Season disclosure rules are enforced in the replay renderer

### D4 — Build the pit-crew coach

*Why:* One concrete fix per loss is the difference between churn and mastery.

*Depends on:* D3

*Boundary:* Coaching is advisory. It never edits a player's bot and never guarantees an outcome.

**Tasks**

- [ ] Derive a single highest-leverage suggestion from the failure mode
- [ ] Cite the governing spec section for each suggestion
- [ ] Suppress coaching when evidence is insufficient rather than guessing

**Acceptance criteria**

- [ ] Each loss yields at most one concrete, evidence-grounded suggestion
- [ ] Every suggestion cites a spec section or a trace event
- [ ] Insufficient evidence produces an honest "cannot determine" message

**Doneness tests**

- `T-075` (contract) — Each loss yields at most one concrete evidence-grounded suggestion
- `T-076` (contract) — Insufficient evidence yields an honest cannot-determine message, not a guess

---

## E13 — Declaration-Behaviour Binding

**Lane:** SL-E Trust, Safety and Anti-Cheat  |  **Phase:** P1 First Blood

**Outcome:** A bot cannot do at runtime what its ADL did not declare.

### E1I — Enforce runtime binding against the weighed declaration

*Why:* This single control is what makes weight class meaningful and makes ADL a contract rather than documentation.

*Depends on:* B1, A4

*Boundary:* Binding enforces the declaration. It does not evaluate whether the declaration was wise.

**Tasks**

- [ ] Bind the runtime to the exact capability hash weighed in
- [ ] Refuse any capability outside the bound declaration
- [ ] Forfeit the match on an attempted escape and record the evidence

**Acceptance criteria**

- [ ] A capability absent from the weighed hash cannot execute
- [ ] An escape attempt forfeits the match with recorded evidence
- [ ] The bound hash on the trace matches the weigh-in certificate exactly

**Doneness tests**

- `T-077` (adversarial) — A capability absent from the weighed hash cannot execute
- `T-078` (integration) — An escape attempt forfeits the match and records evidence
- `T-079` (determinism) — The bound hash on every trace matches its weigh-in certificate

### E2I — Detect undeclared-capability reliance

*Why:* The subtler cheat is not declaring a tool but relying on capacity beyond the declared envelope.

*Depends on:* E1I, B4

*Boundary:* Detection flags a discrepancy; adjudication is a separate human-reviewed step.

**Tasks**

- [ ] Compare actual context and output usage against declared requirements
- [ ] Flag sustained overrun beyond the published tolerance
- [ ] Route flagged matches to review rather than auto-banning

**Acceptance criteria**

- [ ] Declared-versus-actual usage is measured on every match
- [ ] Sustained overrun is flagged with the measured delta
- [ ] No automatic ban occurs without human review

**Doneness tests**

- `T-080` (integration) — Declared-versus-actual usage is measured on every match
- `T-081` (contract) — Sustained overrun is flagged with the measured delta and routed to review, not auto-ban

---

## E14 — Injection Containment and Arena Safety

**Lane:** SL-E Trust, Safety and Anti-Cheat  |  **Phase:** P2 Mercenary Market

**Outcome:** Adversarial content between competitors stays inside the match and cannot reach the platform, the judge, or another player.

### E3I — Contain cross-competitor prompt injection

*Why:* The Vault format deliberately makes injection a legitimate move, which makes containment non-negotiable rather than optional.

*Depends on:* B1, B6

*Boundary:* Containment protects the platform and third parties. It does not protect a competitor from a fair in-match attack.

**Tasks**

- [ ] Treat all opponent output as untrusted, never as instruction
- [ ] Assert opponent content cannot alter judge, broker, or platform behaviour
- [ ] Fuzz the transport with hostile payloads including protocol-shaped strings

**Acceptance criteria**

- [ ] Opponent content never reaches an approved-source path
- [ ] No opponent payload can alter judge or broker behaviour
- [ ] Hostile payload fuzzing produces zero platform-level escapes

**Doneness tests**

- `T-082` (adversarial) — Opponent content never reaches an approved-source path
- `T-083` (adversarial) — No opponent payload alters judge or broker behaviour
- `T-084` (adversarial) — Hostile and protocol-shaped payloads produce zero platform-level escapes

### E4I — Abuse, harm and content handling for player-authored bots

*Why:* Player-authored agents are user-generated content and will eventually include harmful material.

*Depends on:* E3I

*Boundary:* Moderation covers Arena-hosted play. It makes no claim about what players run privately.

**Tasks**

- [ ] Define prohibited bot behaviours and publish them before the season
- [ ] Implement report, review, and appeal paths
- [ ] Ensure moderation actions are logged and reversible

**Acceptance criteria**

- [ ] Prohibited-behaviour policy is published before the first season
- [ ] Every moderation action is logged with reviewer and reason
- [ ] An appeal path exists and is documented

**Doneness tests**

- `T-085` (contract) — Prohibited-behaviour policy is published before season open
- `T-086` (contract) — Every moderation action is logged with reviewer and reason and is reversible

---

## E15 — Devnet Projection and External Tester Packet

**Lane:** SL-F Release Ops and Evidence  |  **Phase:** P4 Devnet Proof

**Outcome:** Arena play generates the bounded devnet evidence the protocol repo still owes on the release ladder.

### F1 — Project eligible match results to localnet then devnet

*Why:* Real players generating real evidence is a better tester gate than recruiting people to run conformance suites.

*Depends on:* C6, C9

*Boundary:* Devnet proof is not mainnet readiness. Rich metadata stays off-chain; only hashes and references project.

**Tasks**

- [ ] Rehearse on localnet before any devnet write
- [ ] Project only hashes and references, never rich metadata
- [ ] Reconcile on-chain projections against off-chain receipts

**Acceptance criteria**

- [ ] Localnet rehearsal passes before devnet is touched
- [ ] No personal or rich metadata appears on chain
- [ ] Every projection reconciles to exactly one off-chain receipt

**Doneness tests**

- `T-087` (integration) — Localnet rehearsal passes before any devnet write is attempted
- `T-088` (adversarial) — No rich or personal metadata is written on chain; hashes and refs only
- `T-089` (integration) — Every on-chain projection reconciles to exactly one off-chain receipt

### F2 — Assemble the external tester evidence packet

*Why:* This is the concrete artifact the release ladder is waiting on.

*Depends on:* F1

*Boundary:* The packet is evidence for review. It is not audit completion and must never be described as such.

**Tasks**

- [ ] Bundle traces, receipts, policy decisions, and reconciliation reports
- [ ] State explicitly what the packet does not prove
- [ ] Include the negative results and the failures, not only the successes

**Acceptance criteria**

- [ ] The packet includes a written non-claims section
- [ ] Failed and anomalous matches are included, not filtered out
- [ ] Every claim in the packet cites a specific artifact

**Doneness tests**

- `T-090` (contract) — The tester packet contains an explicit non-claims section
- `T-091` (contract) — Failed and anomalous matches are included in the packet, not filtered

---

## E16 — Lab Feedback Loop and Claims Discipline

**Lane:** SL-F Release Ops and Evidence  |  **Phase:** P0 Foundry

**Outcome:** Arena findings reach the lab as evidence, and no Arena surface overstates maturity.

### F3 — Establish the one-way canonicality workflow

*Why:* The binding rule is that spec flows down and findings flow up. A proof project is exactly where that discipline erodes first.

*Depends on:* A1

*Boundary:* Arena may propose. Only the lab may make an ADL semantic canonical.

**Tasks**

- [ ] Route every finding through the public feedback intake
- [ ] Forbid Arena-local ADL forks in CI
- [ ] Track which findings the lab accepted, rejected, or deferred

**Acceptance criteria**

- [ ] CI fails if a vendored ADL schema diverges from the pinned upstream hash
- [ ] Every finding has an upstream reference and a disposition
- [ ] No Arena document redefines an ADL semantic

**Doneness tests**

- `T-092` (determinism) — CI fails if the vendored ADL schema diverges from the pinned upstream hash
- `T-093` (contract) — No Arena document redefines an ADL semantic; every finding has an upstream reference

### F4 — Enforce claims discipline across all public Arena surfaces

*Why:* The 2026-08-01 operational correction exists because planning was being reported as implementation. A public game multiplies that risk.

*Depends on:* F3

*Boundary:* This issue governs what Arena says about itself. It creates no technical capability.

**Tasks**

- [ ] Ban the words implying audit, mainnet, or production readiness in copy
- [ ] Require every capability claim to cite a passing test or artifact
- [ ] Add a release-state banner reflecting actual gate status

**Acceptance criteria**

- [ ] No public surface claims audit completion or mainnet readiness
- [ ] Every capability claim links to a passing test or a published artifact
- [ ] A closed planning issue is never rendered as a shipped capability

**Doneness tests**

- `T-094` (contract) — No public surface claims audit completion, mainnet readiness, or production status
- `T-095` (contract) — Every capability claim links to a passing test or published artifact
