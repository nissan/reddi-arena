#!/usr/bin/env bash
# Creates the reddi-arena issue graph on GitHub in topological order.
# Requires: gh CLI authenticated with write access to nissan/reddi-arena.
# Idempotency: run once; gh offers no cheap upsert. Review before running.
set -euo pipefail

declare -A NUM  # issue-id -> created issue number

BODY=$(cat <<'REDDI_EOF'
The reference bots were drafted from prose, not from the schema. Until validated they are hypotheses, not artifacts.

**Boundary:** Validation proves document shape only. It authorizes no execution.

**Artifact:** spdd/prompt/*-a1-*.md
**Doneness tests:** T-001, T-002
REDDI_EOF
)
NUM[A1]=$(gh issue create --repo nissan/reddi-arena --title 'A1 — Validate reference ADL documents against the published v0.2 schema' --body "$BODY" --label lane:SL-A --label phase:P0 --label epic:E01 --label status:done | grep -oE '[0-9]+$')
echo "created A1 -> #${NUM[A1]}"

BODY=$(cat <<'REDDI_EOF'
Invalid documents must fail for the stated reason, not incidentally.

**Boundary:** Fixtures are review artifacts; they do not define new ADL semantics.

**Artifact:** spdd/prompt/*-a2-*.md
**Doneness tests:** T-003, T-004
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A1]}"
NUM[A2]=$(gh issue create --repo nissan/reddi-arena --title 'A2 — Build the Arena negative-fixture corpus' --body "$BODY" --label lane:SL-A --label phase:P0 --label epic:E01 --label status:ready | grep -oE '[0-9]+$')
echo "created A2 -> #${NUM[A2]}"

BODY=$(cat <<'REDDI_EOF'
Arena needs match-specific metadata (format, class, fuel cap) without polluting canonical ADL.

**Boundary:** An x- namespace is Arena-local. It confers no canonical status and must not carry payment-like semantics.

**Artifact:** spdd/prompt/*-a3-*.md
**Doneness tests:** T-005, T-006
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A1]}"
NUM[A3]=$(gh issue create --repo nissan/reddi-arena --title 'A3 — Define the arena-profile extension namespace' --body "$BODY" --label lane:SL-A --label phase:P0 --label epic:E01 --label status:ready | grep -oE '[0-9]+$')
echo "created A3 -> #${NUM[A3]}"

BODY=$(cat <<'REDDI_EOF'
If weight is not deterministic and independently recomputable, the whole competitive frame collapses.

**Boundary:** A weight certificate authorizes nothing; it is an eligibility input only.

**Artifact:** spdd/prompt/*-a4-*.md
**Doneness tests:** T-007, T-008, T-009
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A1]}"
NUM[A4]=$(gh issue create --repo nissan/reddi-arena --title 'A4 — Specify and freeze the AU weight formula v0.1' --body "$BODY" --label lane:SL-A --label phase:P0 --label epic:E02 --label status:ready | grep -oE '[0-9]+$')
echo "created A4 -> #${NUM[A4]}"

BODY=$(cat <<'REDDI_EOF'
The class-bump-on-hire tradeoff is the core strategic mechanic and must be computed identically by every implementation.

**Boundary:** Computing coupled weight does not engage a specialist or move value.

**Artifact:** spdd/prompt/*-a5-*.md
**Doneness tests:** T-010, T-011, T-012
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A4]}"
NUM[A5]=$(gh issue create --repo nissan/reddi-arena --title 'A5 — Implement coupled weight for hired specialists' --body "$BODY" --label lane:SL-A --label phase:P0 --label epic:E02 --label status:ready | grep -oE '[0-9]+$')
echo "created A5 -> #${NUM[A5]}"

BODY=$(cat <<'REDDI_EOF'
Any scoring function invites optimisation against its own artifacts.

**Boundary:** Review output is advisory to formula v0.2; it does not change v0.1 mid-season.

**Artifact:** spdd/prompt/*-a6-*.md
**Doneness tests:** T-013, T-014
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A4]}"
NUM[A6]=$(gh issue create --repo nissan/reddi-arena --title 'A6 — Anti-gaming review of the weight formula' --body "$BODY" --label lane:SL-A --label phase:P0 --label epic:E02 --label status:ready | grep -oE '[0-9]+$')
echo "created A6 -> #${NUM[A6]}"

BODY=$(cat <<'REDDI_EOF'
This is the teaching mechanism — players learn the spec by ranking up, not by reading it.

**Boundary:** Reaching a tier grants match eligibility only. It never grants provider, network, wallet, or rail access.

**Artifact:** spdd/prompt/*-a7-*.md
**Doneness tests:** T-015, T-016
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A1]} #${NUM[A4]}"
NUM[A7]=$(gh issue create --repo nissan/reddi-arena --title 'A7 — Map conformance levels to league tiers' --body "$BODY" --label lane:SL-A --label phase:P1 --label epic:E03 --label status:ready | grep -oE '[0-9]+$')
echo "created A7 -> #${NUM[A7]}"

BODY=$(cat <<'REDDI_EOF'
The lab records that charge intents can escape intended Level-3 enforcement. Arena must not inherit that hole.

**Boundary:** The guard is Arena-local compensating control. It does not fix the spec and must not be described as fixing it.

**Artifact:** spdd/prompt/*-a8-*.md
**Doneness tests:** T-017, T-018
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A7]}"
NUM[A8]=$(gh issue create --repo nissan/reddi-arena --title 'A8 — Guard the known v0.2 charge-intent conformance gap' --body "$BODY" --label lane:SL-A --label phase:P1 --label epic:E03 --label status:ready | grep -oE '[0-9]+$')
echo "created A8 -> #${NUM[A8]}"

BODY=$(cat <<'REDDI_EOF'
Execution is the one place the declaration becomes action, so it is the one place fail-closed must be provably enforced.

**Boundary:** The lane is the ONLY component permitted to execute, and only for declared, policy-matched, locally-bound capabilities.

**Artifact:** spdd/prompt/*-b1-*.md
**Doneness tests:** T-019, T-020, T-021, T-022
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A1]}"
NUM[B1]=$(gh issue create --repo nissan/reddi-arena --title 'B1 — Build the bounded execution lane' --body "$BODY" --label lane:SL-B --label phase:P1 --label epic:E04 --label status:ready | grep -oE '[0-9]+$')
echo "created B1 -> #${NUM[B1]}"

BODY=$(cat <<'REDDI_EOF'
Deterministic lifecycle is the precondition for replayable evidence.

**Boundary:** Lifecycle events are evidence, not adjudication.

**Artifact:** spdd/prompt/*-b2-*.md
**Doneness tests:** T-023, T-024, T-025
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B1]}"
NUM[B2]=$(gh issue create --repo nissan/reddi-arena --title 'B2 — Implement the turn loop and match lifecycle' --body "$BODY" --label lane:SL-B --label phase:P1 --label epic:E04 --label status:ready | grep -oE '[0-9]+$')
echo "created B2 -> #${NUM[B2]}"

BODY=$(cat <<'REDDI_EOF'
Provider neutrality is an ADL promise; the Arena is where it either holds or visibly breaks.

**Boundary:** Declaring a provider is not credential authorization. Missing credentials fail closed rather than silently falling back.

**Artifact:** spdd/prompt/*-b3-*.md
**Doneness tests:** T-026, T-027, T-028
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B1]}"
NUM[B3]=$(gh issue create --repo nissan/reddi-arena --title 'B3 — Provider abstraction across declared model providers' --body "$BODY" --label lane:SL-B --label phase:P1 --label epic:E04 --label status:ready | grep -oE '[0-9]+$')
echo "created B3 -> #${NUM[B3]}"

BODY=$(cat <<'REDDI_EOF'
Efficiency becomes a skill only if fuel is metered and enforced.

**Boundary:** Fuel accounting is deterministic bookkeeping, not billing.

**Artifact:** spdd/prompt/*-b4-*.md
**Doneness tests:** T-029, T-030, T-031
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B2]}"
NUM[B4]=$(gh issue create --repo nissan/reddi-arena --title 'B4 — Implement token fuel accounting' --body "$BODY" --label lane:SL-B --label phase:P1 --label epic:E05 --label status:ready | grep -oE '[0-9]+$')
echo "created B4 -> #${NUM[B4]}"

BODY=$(cat <<'REDDI_EOF'
The trace is the evidence substrate for receipts, learning mode, and disputes.

**Boundary:** A trace records what happened. It does not by itself establish task success or reputation eligibility.

**Artifact:** spdd/prompt/*-b5-*.md
**Doneness tests:** T-032, T-033, T-034
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B2]}"
NUM[B5]=$(gh issue create --repo nissan/reddi-arena --title 'B5 — Emit conformance-aligned trace events with redaction' --body "$BODY" --label lane:SL-B --label phase:P1 --label epic:E05 --label status:ready | grep -oE '[0-9]+$')
echo "created B5 -> #${NUM[B5]}"

BODY=$(cat <<'REDDI_EOF'
A format nobody can argue about is worth more than five ambiguous ones.

**Boundary:** Scoring is deterministic given a trace; it does not judge intent.

**Artifact:** spdd/prompt/*-b6-*.md
**Doneness tests:** T-035, T-036, T-037
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B2]} #${NUM[B4]}"
NUM[B6]=$(gh issue create --repo nissan/reddi-arena --title 'B6 — Implement Vault attack/defend scoring' --body "$BODY" --label lane:SL-B --label phase:P1 --label epic:E06 --label status:ready | grep -oE '[0-9]+$')
echo "created B6 -> #${NUM[B6]}"

BODY=$(cat <<'REDDI_EOF'
Without a balance harness, the first dominant strategy ends the format's competitive life.

**Boundary:** Balance findings inform format v0.2; they do not retroactively alter results.

**Artifact:** spdd/prompt/*-b7-*.md
**Doneness tests:** T-038, T-039
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B6]}"
NUM[B7]=$(gh issue create --repo nissan/reddi-arena --title 'B7 — Format balance harness' --body "$BODY" --label lane:SL-B --label phase:P1 --label epic:E06 --label status:ready | grep -oE '[0-9]+$')
echo "created B7 -> #${NUM[B7]}"

BODY=$(cat <<'REDDI_EOF'
Discovery is where players first meet RAP's "relevance is not trust" rule.

**Boundary:** A listing is a claim, not verified truth. Discovery grants no invocation permission and no publication.

**Artifact:** spdd/prompt/*-c1-*.md
**Doneness tests:** T-040, T-041, T-042
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A1]} #${NUM[A4]}"
NUM[C1]=$(gh issue create --repo nissan/reddi-arena --title 'C1 — Integrate discovery-source into the specialist listing surface' --body "$BODY" --label lane:SL-C --label phase:P2 --label epic:E07 --label status:parked | grep -oE '[0-9]+$')
echo "created C1 -> #${NUM[C1]}"

BODY=$(cat <<'REDDI_EOF'
The spec is emphatic that publication must never happen accidentally.

**Boundary:** Import, mapping, and export must never publish a live listing.

**Artifact:** spdd/prompt/*-c2-*.md
**Doneness tests:** T-043, T-044
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C1]}"
NUM[C2]=$(gh issue create --repo nissan/reddi-arena --title 'C2 — Separate publication from discovery as an explicit gate' --body "$BODY" --label lane:SL-C --label phase:P2 --label epic:E07 --label status:parked | grep -oE '[0-9]+$')
echo "created C2 -> #${NUM[C2]}"

BODY=$(cat <<'REDDI_EOF'
Decide is the layer players most often skip conceptually, so the game must make it unavoidable and visible.

**Boundary:** An allow decision permits a bounded engagement only. It never widens buyer authority beyond the operator-declared envelope.

**Artifact:** spdd/prompt/*-c3-*.md
**Doneness tests:** T-045, T-046, T-047
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C1]} #${NUM[A5]}"
NUM[C3]=$(gh issue create --repo nissan/reddi-arena --title 'C3 — Integrate buyer-authority-policy as the hire decision engine' --body "$BODY" --label lane:SL-C --label phase:P2 --label epic:E08 --label status:parked | grep -oE '[0-9]+$')
echo "created C3 -> #${NUM[C3]}"

BODY=$(cat <<'REDDI_EOF'
The hire-versus-class tradeoff is the strategic heart of the game and must resolve deterministically before combat.

**Boundary:** Draft outcomes bind eligibility only; no work or payment occurs at draft.

**Artifact:** spdd/prompt/*-c4-*.md
**Doneness tests:** T-048, T-049, T-050
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C3]} #${NUM[A5]}"
NUM[C4]=$(gh issue create --repo nissan/reddi-arena --title 'C4 — Implement the draft window and weigh-in recomputation' --body "$BODY" --label lane:SL-C --label phase:P2 --label epic:E08 --label status:parked | grep -oE '[0-9]+$')
echo "created C4 -> #${NUM[C4]}"

BODY=$(cat <<'REDDI_EOF'
The purse teaches the single most important RAP lesson: payment success is not work success.

**Boundary:** Rail is pinned to x402-dry-run. livePaymentAccess is false. No wallet, facilitator, custody, or real value exists anywhere in this issue.

**Artifact:** spdd/prompt/*-c5-*.md
**Doneness tests:** T-051, T-052, T-053, T-054
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C3]}"
NUM[C5]=$(gh issue create --repo nissan/reddi-arena --title 'C5 — Implement dry-run escrow for purse and fees' --body "$BODY" --label lane:SL-C --label phase:P2 --label epic:E09 --label status:parked | grep -oE '[0-9]+$')
echo "created C5 -> #${NUM[C5]}"

BODY=$(cat <<'REDDI_EOF'
The receipt is the artifact an external analyst can actually check.

**Boundary:** A receipt records that policy, payment reference, and evidence reference existed. It does not prove settlement finality or provider quality.

**Artifact:** spdd/prompt/*-c6-*.md
**Doneness tests:** T-055, T-056, T-057, T-058
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C5]} #${NUM[B5]}"
NUM[C6]=$(gh issue create --repo nissan/reddi-arena --title 'C6 — Integrate receipts and receipt-evidence-binding per match and engagement' --body "$BODY" --label lane:SL-C --label phase:P2 --label epic:E09 --label status:parked | grep -oE '[0-9]+$')
echo "created C6 -> #${NUM[C6]}"

BODY=$(cat <<'REDDI_EOF'
RAP already names a paid judge actor; the arena referee is that actor.

**Boundary:** An attestation is one evidence input. It cannot substitute for required eval gates or for payment proof.

**Artifact:** spdd/prompt/*-c7-*.md
**Doneness tests:** T-059, T-060, T-061
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C6]}"
NUM[C7]=$(gh issue create --repo nissan/reddi-arena --title 'C7 — Integrate attestation-reputation as the judge actor' --body "$BODY" --label lane:SL-C --label phase:P2 --label epic:E09 --label status:parked | grep -oE '[0-9]+$')
echo "created C7 -> #${NUM[C7]}"

BODY=$(cat <<'REDDI_EOF'
The spec is explicit that reputation must not mutate when policy failed or evidence is missing. This is the cleanest thing an analyst can audit.

**Boundary:** Reputation is a derived signal within one season. It is not portable identity and carries no external warranty.

**Artifact:** spdd/prompt/*-c8-*.md
**Doneness tests:** T-062, T-063, T-064
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C6]} #${NUM[C7]}"
NUM[C8]=$(gh issue create --repo nissan/reddi-arena --title 'C8 — Integrate offchain-reputation-preview and enforce eligibility rules' --body "$BODY" --label lane:SL-C --label phase:P3 --label epic:E10 --label status:parked | grep -oE '[0-9]+$')
echo "created C8 -> #${NUM[C8]}"

BODY=$(cat <<'REDDI_EOF'
Rivals scoring rivals invites retaliation and copying; commit-reveal is the spec's answer and the arena is a natural stress test.

**Boundary:** Off-chain commit-reveal only in P3. On-chain projection is E15.

**Artifact:** spdd/prompt/*-c9-*.md
**Doneness tests:** T-065, T-066, T-067
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C8]}"
NUM[C9]=$(gh issue create --repo nissan/reddi-arena --title 'C9 — Implement commit-reveal scoring' --body "$BODY" --label lane:SL-C --label phase:P3 --label epic:E10 --label status:parked | grep -oE '[0-9]+$')
echo "created C9 -> #${NUM[C9]}"

BODY=$(cat <<'REDDI_EOF'
The garage is the on-ramp; if it emits anything other than canonical ADL, the whole proof is undermined.

**Boundary:** The garage authors documents. It never executes or publishes them.

**Artifact:** spdd/prompt/*-d1-*.md
**Doneness tests:** T-068, T-069, T-070
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A1]} #${NUM[A4]}"
NUM[D1]=$(gh issue create --repo nissan/reddi-arena --title 'D1 — Build the visual garage that emits ADL' --body "$BODY" --label lane:SL-D --label phase:P2 --label epic:E11 --label status:parked | grep -oE '[0-9]+$')
echo "created D1 -> #${NUM[D1]}"

BODY=$(cat <<'REDDI_EOF'
Experts will not adopt a tool that mangles their handwritten documents.

**Boundary:** Round-tripping preserves semantics; it does not validate intent.

**Artifact:** spdd/prompt/*-d2-*.md
**Doneness tests:** T-071, T-072
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[D1]}"
NUM[D2]=$(gh issue create --repo nissan/reddi-arena --title 'D2 — Round-trip fidelity between visual and raw editing' --body "$BODY" --label lane:SL-D --label phase:P2 --label epic:E11 --label status:parked | grep -oE '[0-9]+$')
echo "created D2 -> #${NUM[D2]}"

BODY=$(cat <<'REDDI_EOF'
The replay is where a receipt and a trace become a learning experience instead of a compliance artifact.

**Boundary:** The replay renders recorded evidence. It never reconstructs, infers, or embellishes what was not traced.

**Artifact:** spdd/prompt/*-d3-*.md
**Doneness tests:** T-073, T-074
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B5]} #${NUM[B6]}"
NUM[D3]=$(gh issue create --repo nissan/reddi-arena --title 'D3 — Render the annotated match replay' --body "$BODY" --label lane:SL-D --label phase:P3 --label epic:E12 --label status:parked | grep -oE '[0-9]+$')
echo "created D3 -> #${NUM[D3]}"

BODY=$(cat <<'REDDI_EOF'
One concrete fix per loss is the difference between churn and mastery.

**Boundary:** Coaching is advisory. It never edits a player's bot and never guarantees an outcome.

**Artifact:** spdd/prompt/*-d4-*.md
**Doneness tests:** T-075, T-076
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[D3]}"
NUM[D4]=$(gh issue create --repo nissan/reddi-arena --title 'D4 — Build the pit-crew coach' --body "$BODY" --label lane:SL-D --label phase:P3 --label epic:E12 --label status:parked | grep -oE '[0-9]+$')
echo "created D4 -> #${NUM[D4]}"

BODY=$(cat <<'REDDI_EOF'
This single control is what makes weight class meaningful and makes ADL a contract rather than documentation.

**Boundary:** Binding enforces the declaration. It does not evaluate whether the declaration was wise.

**Artifact:** spdd/prompt/*-e1i-*.md
**Doneness tests:** T-077, T-078, T-079
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B1]} #${NUM[A4]}"
NUM[E1I]=$(gh issue create --repo nissan/reddi-arena --title 'E1I — Enforce runtime binding against the weighed declaration' --body "$BODY" --label lane:SL-E --label phase:P1 --label epic:E13 --label status:ready | grep -oE '[0-9]+$')
echo "created E1I -> #${NUM[E1I]}"

BODY=$(cat <<'REDDI_EOF'
The subtler cheat is not declaring a tool but relying on capacity beyond the declared envelope.

**Boundary:** Detection flags a discrepancy; adjudication is a separate human-reviewed step.

**Artifact:** spdd/prompt/*-e2i-*.md
**Doneness tests:** T-080, T-081
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[E1I]} #${NUM[B4]}"
NUM[E2I]=$(gh issue create --repo nissan/reddi-arena --title 'E2I — Detect undeclared-capability reliance' --body "$BODY" --label lane:SL-E --label phase:P1 --label epic:E13 --label status:ready | grep -oE '[0-9]+$')
echo "created E2I -> #${NUM[E2I]}"

BODY=$(cat <<'REDDI_EOF'
The Vault format deliberately makes injection a legitimate move, which makes containment non-negotiable rather than optional.

**Boundary:** Containment protects the platform and third parties. It does not protect a competitor from a fair in-match attack.

**Artifact:** spdd/prompt/*-e3i-*.md
**Doneness tests:** T-082, T-083, T-084
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[B1]} #${NUM[B6]}"
NUM[E3I]=$(gh issue create --repo nissan/reddi-arena --title 'E3I — Contain cross-competitor prompt injection' --body "$BODY" --label lane:SL-E --label phase:P2 --label epic:E14 --label status:parked | grep -oE '[0-9]+$')
echo "created E3I -> #${NUM[E3I]}"

BODY=$(cat <<'REDDI_EOF'
Player-authored agents are user-generated content and will eventually include harmful material.

**Boundary:** Moderation covers Arena-hosted play. It makes no claim about what players run privately.

**Artifact:** spdd/prompt/*-e4i-*.md
**Doneness tests:** T-085, T-086
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[E3I]}"
NUM[E4I]=$(gh issue create --repo nissan/reddi-arena --title 'E4I — Abuse, harm and content handling for player-authored bots' --body "$BODY" --label lane:SL-E --label phase:P2 --label epic:E14 --label status:parked | grep -oE '[0-9]+$')
echo "created E4I -> #${NUM[E4I]}"

BODY=$(cat <<'REDDI_EOF'
Real players generating real evidence is a better tester gate than recruiting people to run conformance suites.

**Boundary:** Devnet proof is not mainnet readiness. Rich metadata stays off-chain; only hashes and references project.

**Artifact:** spdd/prompt/*-f1-*.md
**Doneness tests:** T-087, T-088, T-089
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[C6]} #${NUM[C9]}"
NUM[F1]=$(gh issue create --repo nissan/reddi-arena --title 'F1 — Project eligible match results to localnet then devnet' --body "$BODY" --label lane:SL-F --label phase:P4 --label epic:E15 --label status:struck | grep -oE '[0-9]+$')
echo "created F1 -> #${NUM[F1]}"

BODY=$(cat <<'REDDI_EOF'
This is the concrete artifact the release ladder is waiting on.

**Boundary:** The packet is evidence for review. It is not audit completion and must never be described as such.

**Artifact:** spdd/prompt/*-f2-*.md
**Doneness tests:** T-090, T-091
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[F1]}"
NUM[F2]=$(gh issue create --repo nissan/reddi-arena --title 'F2 — Assemble the external tester evidence packet' --body "$BODY" --label lane:SL-F --label phase:P4 --label epic:E15 --label status:struck | grep -oE '[0-9]+$')
echo "created F2 -> #${NUM[F2]}"

BODY=$(cat <<'REDDI_EOF'
The binding rule is that spec flows down and findings flow up. A proof project is exactly where that discipline erodes first.

**Boundary:** Arena may propose. Only the lab may make an ADL semantic canonical.

**Artifact:** spdd/prompt/*-f3-*.md
**Doneness tests:** T-092, T-093
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[A1]}"
NUM[F3]=$(gh issue create --repo nissan/reddi-arena --title 'F3 — Establish the one-way canonicality workflow' --body "$BODY" --label lane:SL-F --label phase:P0 --label epic:E16 --label status:ready | grep -oE '[0-9]+$')
echo "created F3 -> #${NUM[F3]}"

BODY=$(cat <<'REDDI_EOF'
The 2026-08-01 operational correction exists because planning was being reported as implementation. A public game multiplies that risk.

**Boundary:** This issue governs what Arena says about itself. It creates no technical capability.

**Artifact:** spdd/prompt/*-f4-*.md
**Doneness tests:** T-094, T-095
REDDI_EOF
)
BODY="$BODY" ; BODY+=$'\n\n' ; BODY+="depends-on: #${NUM[F3]}"
NUM[F4]=$(gh issue create --repo nissan/reddi-arena --title 'F4 — Enforce claims discipline across all public Arena surfaces' --body "$BODY" --label lane:SL-F --label phase:P0 --label epic:E16 --label status:ready | grep -oE '[0-9]+$')
echo "created F4 -> #${NUM[F4]}"
