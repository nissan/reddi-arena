# SPDD prompt index — topological work order

Generated from plan/backlog.yaml by tools/generate_prompts.py. The graph decides the order; the linter guarantees it is a DAG.

| # | Issue | Status | Phase | Lane | Artifact |
|---|---|---|---|---|---|
| 0002 | A1 | done | P0 | SL-A | [Validate reference ADL documents against the published v0.2 schema](prompt/0002-a1-validate-reference-adl-documents-against-the-pub.md) |
| 0003 | A2 | ready | P0 | SL-A | [Build the Arena negative-fixture corpus](prompt/0003-a2-build-the-arena-negative-fixture-corpus.md) |
| 0004 | A3 | ready | P0 | SL-A | [Define the arena-profile extension namespace](prompt/0004-a3-define-the-arena-profile-extension-namespace.md) |
| 0005 | A4 | ready | P0 | SL-A | [Specify and freeze the AU weight formula v0.1](prompt/0005-a4-specify-and-freeze-the-au-weight-formula-v0-1.md) |
| 0006 | A5 | ready | P0 | SL-A | [Implement coupled weight for hired specialists](prompt/0006-a5-implement-coupled-weight-for-hired-specialists.md) |
| 0007 | A6 | ready | P0 | SL-A | [Anti-gaming review of the weight formula](prompt/0007-a6-anti-gaming-review-of-the-weight-formula.md) |
| 0008 | A7 | ready | P1 | SL-A | [Map conformance levels to league tiers](prompt/0008-a7-map-conformance-levels-to-league-tiers.md) |
| 0009 | A8 | ready | P1 | SL-A | [Guard the known v0.2 charge-intent conformance gap](prompt/0009-a8-guard-the-known-v0-2-charge-intent-conformance-g.md) |
| 0010 | B1 | ready | P1 | SL-B | [Build the bounded execution lane](prompt/0010-b1-build-the-bounded-execution-lane.md) |
| 0011 | B2 | ready | P1 | SL-B | [Implement the turn loop and match lifecycle](prompt/0011-b2-implement-the-turn-loop-and-match-lifecycle.md) |
| 0012 | B3 | ready | P1 | SL-B | [Provider abstraction across declared model providers](prompt/0012-b3-provider-abstraction-across-declared-model-provi.md) |
| 0013 | B4 | ready | P1 | SL-B | [Implement token fuel accounting](prompt/0013-b4-implement-token-fuel-accounting.md) |
| 0014 | B5 | ready | P1 | SL-B | [Emit conformance-aligned trace events with redaction](prompt/0014-b5-emit-conformance-aligned-trace-events-with-redac.md) |
| 0015 | B6 | ready | P1 | SL-B | [Implement Vault attack/defend scoring](prompt/0015-b6-implement-vault-attack-defend-scoring.md) |
| 0016 | B7 | ready | P1 | SL-B | [Format balance harness](prompt/0016-b7-format-balance-harness.md) |
| 0017 | C1 | parked | P2 | SL-C | [Integrate discovery-source into the specialist listing surface](prompt/0017-c1-integrate-discovery-source-into-the-specialist-l.md) |
| 0018 | C2 | parked | P2 | SL-C | [Separate publication from discovery as an explicit gate](prompt/0018-c2-separate-publication-from-discovery-as-an-explic.md) |
| 0019 | C3 | parked | P2 | SL-C | [Integrate buyer-authority-policy as the hire decision engine](prompt/0019-c3-integrate-buyer-authority-policy-as-the-hire-dec.md) |
| 0020 | C4 | parked | P2 | SL-C | [Implement the draft window and weigh-in recomputation](prompt/0020-c4-implement-the-draft-window-and-weigh-in-recomput.md) |
| 0021 | C5 | parked | P2 | SL-C | [Implement dry-run escrow for purse and fees](prompt/0021-c5-implement-dry-run-escrow-for-purse-and-fees.md) |
| 0022 | C6 | parked | P2 | SL-C | [Integrate receipts and receipt-evidence-binding per match and engagement](prompt/0022-c6-integrate-receipts-and-receipt-evidence-binding-.md) |
| 0023 | C7 | parked | P2 | SL-C | [Integrate attestation-reputation as the judge actor](prompt/0023-c7-integrate-attestation-reputation-as-the-judge-ac.md) |
| 0024 | C8 | parked | P3 | SL-C | [Integrate offchain-reputation-preview and enforce eligibility rules](prompt/0024-c8-integrate-offchain-reputation-preview-and-enforc.md) |
| 0025 | C9 | parked | P3 | SL-C | [Implement commit-reveal scoring](prompt/0025-c9-implement-commit-reveal-scoring.md) |
| 0026 | D1 | parked | P2 | SL-D | [Build the visual garage that emits ADL](prompt/0026-d1-build-the-visual-garage-that-emits-adl.md) |
| 0027 | D2 | parked | P2 | SL-D | [Round-trip fidelity between visual and raw editing](prompt/0027-d2-round-trip-fidelity-between-visual-and-raw-editi.md) |
| 0028 | D3 | parked | P3 | SL-D | [Render the annotated match replay](prompt/0028-d3-render-the-annotated-match-replay.md) |
| 0029 | D4 | parked | P3 | SL-D | [Build the pit-crew coach](prompt/0029-d4-build-the-pit-crew-coach.md) |
| 0030 | E1I | ready | P1 | SL-E | [Enforce runtime binding against the weighed declaration](prompt/0030-e1i-enforce-runtime-binding-against-the-weighed-decl.md) |
| 0031 | E2I | ready | P1 | SL-E | [Detect undeclared-capability reliance](prompt/0031-e2i-detect-undeclared-capability-reliance.md) |
| 0032 | E3I | parked | P2 | SL-E | [Contain cross-competitor prompt injection](prompt/0032-e3i-contain-cross-competitor-prompt-injection.md) |
| 0033 | E4I | parked | P2 | SL-E | [Abuse, harm and content handling for player-authored bots](prompt/0033-e4i-abuse-harm-and-content-handling-for-player-autho.md) |
| 0034 | F1 | struck | P4 | SL-F | [Project eligible match results to localnet then devnet](prompt/0034-f1-project-eligible-match-results-to-localnet-then-.md) |
| 0035 | F2 | struck | P4 | SL-F | [Assemble the external tester evidence packet](prompt/0035-f2-assemble-the-external-tester-evidence-packet.md) |
| 0036 | F3 | ready | P0 | SL-F | [Establish the one-way canonicality workflow](prompt/0036-f3-establish-the-one-way-canonicality-workflow.md) |
| 0037 | F4 | ready | P0 | SL-F | [Enforce claims discipline across all public Arena surfaces](prompt/0037-f4-enforce-claims-discipline-across-all-public-aren.md) |
