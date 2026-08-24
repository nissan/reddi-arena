<!-- GENERATED from plan/backlog.yaml by tools/render_plan.py — do not hand-edit. -->

# Reddi Arena — Automated Doneness Tests (plan-v0.4-superseded)

An issue is done when its tests pass in CI. Nothing is done because a planning ticket closed — that failure mode is exactly what the 2026-08-01 operational correction was about.

## Coverage by test type

| Type | Count | Purpose |
|---|---|---|
| adversarial | 20 | Attempts to break a control; passes only if the control holds. |
| contract | 40 | Asserts a declared contract holds exactly as specified. |
| determinism | 5 | Asserts identical inputs always yield identical outputs. |
| e2e | 3 | Asserts whole-system behaviour over realistic play. |
| integration | 13 | Asserts components compose correctly across a boundary. |
| property | 10 | Asserts an invariant across generated inputs (hypothesis). |
| unit | 4 | Asserts a single computation against golden values. |

## Test register

| Test | Type | Automation | Asserts | Proves done |
|---|---|---|---|---|
| T-001 | contract | pytest + jsonschema | Both reference ADLs validate against the pinned v0.2 schema with zero errors | A1 |
| T-002 | determinism | CI hash check | Vendored schema sha256 matches the pinned upstream value; CI fails on drift | A1, F3 |
| T-003 | contract | pytest parametrized over fixtures | Every negative fixture fails validation | A2 |
| T-004 | contract | pytest | Each negative fixture produces its expected diagnostic code, not a generic error | A2 |
| T-005 | contract | pytest | x-arena namespaced fields pass strict validation | A3 |
| T-006 | adversarial | pytest | Unprefixed arena keys and payment-like semantics under x-arena are rejected | A3 |
| T-007 | determinism | pytest, 1000 iterations | Identical AU and capability hash across repeated runs | A4 |
| T-008 | property | hypothesis | YAML key reordering and whitespace changes never alter the capability hash | A4 |
| T-009 | unit | pytest golden files | Reference bot weighs exactly 62 AU; mercenary exactly 91 AU | A4 |
| T-010 | unit | pytest | Hiring the reference mercenary moves the reference bot 62 to 127 AU, Antweight to Beetleweight | A5 |
| T-011 | integration | pytest | A hire breaching the entered class is refused at draft with the AU delta stated | A5, C4 |
| T-012 | property | hypothesis | Transitive hire depth beyond the cap is refused; no unbounded recursion | A5 |
| T-013 | adversarial | pytest exploit suite | No-op deny-policy padding cannot push AU below the declared floor | A6 |
| T-014 | adversarial | pytest exploit suite | Capability hidden in skills or instructions still fails runtime binding | A6, E1I |
| T-015 | contract | pytest | A Level-1 document is refused entry to a Title fight | A7 |
| T-016 | contract | pytest | requestedLevel above achieved level is rejected naming the failing requirement | A7 |
| T-017 | adversarial | pytest | An under-constrained charge intent is refused at pre-draft check | A8 |
| T-018 | contract | doc lint | The charge-intent guard is documented as compensating, never as a spec fix | A8, F4 |
| T-019 | adversarial | pytest sandbox suite | An undeclared tool cannot be invoked at runtime | B1 |
| T-020 | adversarial | pytest sandbox suite | A declared tool lacking a matching policyRef cannot be invoked | B1 |
| T-021 | integration | network-isolated CI job | Egress with an empty allowlist is refused and logged | B1 |
| T-022 | contract | pytest | Every refusal emits an event carrying subject, resource, action and reason | B1 |
| T-023 | property | hypothesis state machine | Every match reaches exactly one defined terminal state | B2 |
| T-024 | integration | pytest with fault injection | Crashed or hung competitors forfeit without hanging the match | B2 |
| T-025 | property | hypothesis state machine | Illegal lifecycle transitions are unreachable | B2 |
| T-026 | contract | pytest with provider mocks | Undeclared fallback providers are never selected | B3 |
| T-027 | contract | pytest with provider mocks | A provider missing a declared requirement reports degraded rather than succeeding silently | B3 |
| T-028 | e2e | nightly cross-provider job | Cross-provider behavioural divergence is measured and published | B3 |
| T-029 | unit | pytest | Exceeding the declared fuel cap fails the budget-check gate | B4 |
| T-030 | integration | pytest | Fuel exhaustion mid-turn produces the defined sputter outcome, never an exception | B4 |
| T-031 | property | hypothesis | Fuel accounting reconciles exactly with the emitted trace for every match | B4 |
| T-032 | contract | pytest | Every match emits a complete ordered replayable event stream | B5 |
| T-033 | contract | pytest | ADL-declared redaction rules are applied rather than engine defaults | B5 |
| T-034 | adversarial | secret-scanner over stored traces | No credential or canary value appears in any stored trace | B5, E3I |
| T-035 | determinism | pytest golden traces | Identical traces always produce identical scores | B6 |
| T-036 | property | hypothesis | Every terminal state maps to exactly one scoring outcome | B6 |
| T-037 | adversarial | pytest canary suite | A canary value leaked in verbatim or JSON-escaped form scores as extraction (encoded/paraphrased/transformed leaks are out of scope for the dry-run arena, per `core/scoring.py`) | B6 |
| T-038 | e2e | nightly round-robin simulation | Attacker/defender win split stays inside the published tolerance band | B7 |
| T-039 | e2e | nightly round-robin simulation | No archetype exceeds the published dominance threshold | B7 |
| T-040 | contract | pytest | A listing cannot advertise a capability absent from its ADL | C1 |
| T-041 | contract | pytest | Provenance is present and displayed for every listing | C1 |
| T-042 | adversarial | pytest | No discovery call triggers invocation or publication as a side effect | C1, C2 |
| T-043 | adversarial | pytest | No import, mapping, or export path can publish a live listing | C2 |
| T-044 | contract | pytest | Every publication event records an explicit approver identity | C2 |
| T-045 | contract | pytest | Every hire attempt produces a machine-readable decision with reason codes | C3 |
| T-046 | adversarial | pytest | An external mandate attempting to widen local buyer authority is rejected | C3 |
| T-047 | unit | pytest | A hire exceeding the declared purse budget is denied | C3 |
| T-048 | integration | pytest | Fielded weight is recomputed and surfaced before a hire commits | C4 |
| T-049 | property | hypothesis | No hire can take effect after the draft window closes | C4 |
| T-050 | adversarial | pytest | The draft window cannot be reopened by any request path | C4 |
| T-051 | contract | pytest | Transport success alone never releases escrow | C5 |
| T-052 | contract | pytest | A failed required gate routes to refund or dispute, never to payout | C5 |
| T-053 | adversarial | pytest | Selecting any rail other than x402-dry-run is refused | C5 |
| T-054 | property | hypothesis | Escrow accounting balances to zero across every terminal state | C5 |
| T-055 | contract | pytest + receipt schema | Every completed match and engagement emits a schema-valid reddi.receipt.v1 | C6 |
| T-056 | contract | pytest | A receipt missing paymentProofRef fails validation closed | C6 |
| T-057 | adversarial | secret scanner over receipts | No receipt contains credential or wallet material | C6 |
| T-058 | integration | pytest | evidenceRef on every receipt resolves to a retrievable trace | C6 |
| T-059 | contract | pytest | Attestation state is present on every emitted receipt | C7 |
| T-060 | contract | pytest | A failed attestation blocks payout even when transport succeeded | C7 |
| T-061 | integration | pytest with fault injection | Judge unavailability produces a defined outcome without indefinite hang | C7 |
| T-062 | contract | pytest | A match failing policy produces zero reputation change | C8 |
| T-063 | contract | pytest | A match with a missing evidence reference produces zero reputation change | C8 |
| T-064 | integration | pytest | Every rating change traces to exactly one eligible receipt | C8 |
| T-065 | adversarial | pytest | No score is readable before the reveal window opens | C9 |
| T-066 | contract | pytest | A non-revealed commit is penalised per the published rule | C9 |
| T-067 | contract | pytest | A reveal not matching its commit hash is rejected | C9 |
| T-068 | property | hypothesis over UI state space | Every reachable garage state emits a schema-valid ADL document | D1 |
| T-069 | integration | pytest comparing UI and CLI | Garage-displayed AU matches the CLI calculator exactly | D1 |
| T-070 | contract | pytest | Validation errors name the offending field and link a spec section | D1 |
| T-071 | property | hypothesis round-trip | Import then export is semantically lossless | D2 |
| T-072 | contract | pytest | UI-unsupported fields are reported explicitly, never silently dropped | D2 |
| T-073 | contract | pytest | Every rendered replay claim maps to a specific trace event | D3 |
| T-074 | contract | pytest | Season disclosure rules are enforced in the replay renderer | D3 |
| T-075 | contract | pytest over labelled failure corpus | Each loss yields at most one concrete evidence-grounded suggestion | D4 |
| T-076 | contract | pytest | Insufficient evidence yields an honest cannot-determine message, not a guess | D4 |
| T-077 | adversarial | pytest binding suite | A capability absent from the weighed hash cannot execute | E1I |
| T-078 | integration | pytest | An escape attempt forfeits the match and records evidence | E1I |
| T-079 | determinism | pytest | The bound hash on every trace matches its weigh-in certificate | E1I |
| T-080 | integration | nightly telemetry job | Declared-versus-actual usage is measured on every match | E2I |
| T-081 | contract | pytest | Sustained overrun is flagged with the measured delta and routed to review, not auto-ban | E2I |
| T-082 | adversarial | pytest injection corpus | Opponent content never reaches an approved-source path | E3I |
| T-083 | adversarial | pytest injection corpus | No opponent payload alters judge or broker behaviour | E3I |
| T-084 | adversarial | fuzzing job | Hostile and protocol-shaped payloads produce zero platform-level escapes | E3I |
| T-085 | contract | doc lint + CI gate | Prohibited-behaviour policy is published before season open | E4I |
| T-086 | contract | pytest | Every moderation action is logged with reviewer and reason and is reversible | E4I |
| T-087 | integration | localnet CI job | Localnet rehearsal passes before any devnet write is attempted | F1 |
| T-088 | adversarial | chain-payload scanner | No rich or personal metadata is written on chain; hashes and refs only | F1 |
| T-089 | integration | reconciliation job | Every on-chain projection reconciles to exactly one off-chain receipt | F1 |
| T-090 | contract | doc lint | The tester packet contains an explicit non-claims section | F2 |
| T-091 | contract | packet build job | Failed and anomalous matches are included in the packet, not filtered | F2 |
| T-092 | determinism | CI gate | CI fails if the vendored ADL schema diverges from the pinned upstream hash | F3 |
| T-093 | contract | repo lint | No Arena document redefines an ADL semantic; every finding has an upstream reference | F3 |
| T-094 | contract | copy lint over public surfaces | No public surface claims audit completion, mainnet readiness, or production status | F4 |
| T-095 | contract | copy lint | Every capability claim links to a passing test or published artifact | F4 |

## Phase exit gates

| Phase | Exit gate | Tests that must be green |
|---|---|---|
| P0 | All P0 tests green; ADL fixtures validate against published schema. | T-001, T-002, T-003, T-004, T-005, T-006, T-007, T-008, T-009, T-010, T-011, T-012, T-013, T-014, T-092, T-093, T-094, T-095 |
| P1 | 100 consecutive local matches with complete traces and zero policy escapes. | T-015, T-016, T-017, T-018, T-019, T-020, T-021, T-022, T-023, T-024, T-025, T-026, T-027, T-028, T-029, T-030, T-031, T-032, T-033, T-034, T-035, T-036, T-037, T-038, T-039, T-077, T-078, T-079, T-080, T-081 |
| P2 | Every paid engagement produces a valid receipt bound to evidence. | T-040, T-041, T-042, T-043, T-044, T-045, T-046, T-047, T-048, T-049, T-050, T-051, T-052, T-053, T-054, T-055, T-056, T-057, T-058, T-059, T-060, T-061, T-068, T-069, T-070, T-071, T-072, T-082, T-083, T-084, T-085, T-086 |
| P3 | Season completes with reputation derived only from eligible evidence. | T-062, T-063, T-064, T-065, T-066, T-067, T-073, T-074, T-075, T-076 |
| P4 | Bounded devnet evidence accepted by lab release-readiness review. | T-087, T-088, T-089, T-090, T-091 |
| P5 | Out of scope for this programme. | n/a — not scheduled |
