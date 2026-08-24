# Retroactive independent audit — 2026-08-24

The `requireIndependentReview` gate (planning/graph.yaml) was added on
2026-08-24, after node A7 shipped and immediately caught a blocker there. This
register records a retroactive audit of all code merged **before** the gate
existed: four independent reviewers (fresh contexts, none the author) examined
the merged state on `main` by subsystem. Baseline at audit time: 214 checks
green (207 pre-hardening + 7 web regression checks).

Every finding below is either fixed (with the remediation PR noted) or has a
disposition. Severities are the reviewers' own. This document is the triage
source of truth; each remediation PR links back to the finding ids here.

## Subsystem 1 — web/CLI/waitlist (public surface)

Reviewer verdict: FINDINGS (one blocker). **Remediated in PR #62** (branch
`fix/web-surface-hardening`).

| id | sev | finding | disposition |
|---|---|---|---|
| W1 | blocker | unauthenticated path traversal / arbitrary file open via `bot`/`hire` fields | fixed #62 (`safe_adl_path`) |
| W2 | major | concurrent writes lose waitlist/ledger entries; truncated-file reads | fixed #62 (lock + atomic write) |
| W3 | major | unbounded unauthenticated writes to the persistent volume (disk DoS) | fixed #62 (body cap, rate limit, entry cap) |
| W4 | major | signup email amplification (any address emailed via Resend, no limit) | partially fixed #62 (rate limit + validation); double-opt-in deferred → W4-followup |
| W5 | minor | no body-size limit / read timeout | fixed #62 |
| W6 | minor | malformed JSON / missing keys drop the connection | fixed #62 (400) |
| W7 | minor | leaked file descriptors | fixed #62 (context managers) |
| W8 | minor | admin token accepted in URL query string | fixed #62 (header-only) |
| W9 | nit | `claims_lint` negation line-global; stale "49 tests" on landing | fixed #62 |

Confirmed clean by the reviewer: Resend key never logged/echoed; no server-side
HTML reflection of stored data; `_admin_ok` constant-time and fail-closed; CLI
is a genuine thin surface with no wallet/rail path.

## Subsystem 2 — lifecycle/fuel/engine

Reviewer verdict: FINDINGS (yellow). **Remediation pending** (branch
`fix/engine-fault-hardening` for the crash/dodge class; trace-integrity items
share the structured-outcome fix with subsystem 3).

| id | sev | finding | disposition |
|---|---|---|---|
| E1 | major | `budget_gate` crashes (TypeError) on non-numeric `maxOutputTokens` | fault-hardening PR |
| E2 | major | `_read_strategy`/`_read_fuel` crash (AttributeError) on non-dict containers | fault-hardening PR |
| E3 | major | string-number `contextWindow` is a weight-class dodge worth huge fuel (readers disagree) | fault-hardening PR |
| E4 | major | duplicate competitor names silently destroy trace evidence (dict-keyed maps collapse) | trace-integrity PR |
| E5 | major | void matches emit `result: "draw"`; chain settlement takes the wrong path | trace-integrity PR |
| E6 | major | defense bonus keyed on a name substring, not the declared grant | game-rule PR / see L3 |
| E7 | major | draft class-ceiling never enforced at match time | game-rule PR / see L2 |
| E8 | minor | "fuel efficiency" tie-break decided at declaration time; parity bias on odd max_turns | game-rule PR |
| E9 | minor | `KeyError` on missing `metadata.name` | fault-hardening PR |
| E10 | minor | non-terminal-trace invariant is an `assert` (vanishes under `python3 -O`) | fault-hardening PR |
| E11 | nit | dead gate branch (`TURN_COST > cap` unreachable via run_vault_match) | comment only |
| E12 | nit | LCG low-bit parity structure (deterministic, swept by simulate) | note only |

Confirmed clean: lifecycle state machine exhaustively correct; FuelMeter
arithmetic and reconciliation; hash determinism across PYTHONHASHSEED; LCG
stream discipline; sputter/extract turn records.

## Subsystem 3 — trace projections + providers

Reviewer verdict: FINDINGS (yellow). **Remediation status (2026-08-24):**

- **Landed in #65** (structured-outcome PR): T3, T6, T7, T8 — outcome now
  carried by structured `outcomeKind`/`atFault`/`budgetGateFailed` fields
  instead of reason-string parsing, and `audit` gained a `declared-envelope-
  overspent` (`spent > cap`) signal.
- **Landed in `fix/trace-projection-hardening`** (this PR): T2 (off-roster
  canary key now ignored, no `IndexError`), T4 (structured/nested secret leaves
  are collected and scrubbed), T5 (JSON-escaped canaries detected via the
  escaped form; non-string canaries coerced, no `TypeError`), T9 (scrub
  longest-first, no overlapping-secret tail).
- **Still open:** T1 — publishing raw leaked values in the score result
  conflicts with the documented T-037 contract (which asserts the value is
  surfaced); needs a design decision, not a silent change. Substring
  false-positives from competitor-controlled strings are mitigated by canary
  entropy and already documented as a textual-detection limit. T10 — the
  single mask+scrub path is already the strictest (fail-closed); honoring an
  alternate `mode` needs the spec to define one, and mask-spoofing exposes no
  secret. T11 — `effective_doc` capping omitted-capability providers changes
  fuel and therefore match outcomes, so it moves to the land-last
  outcome-changing batch with a BALANCE-REPORT regen. T12 — doc/assert nit.

| id | sev | finding | disposition |
|---|---|---|---|
| T1 | major | canary detection substring-matches the whole trace incl. competitor-controlled strings; leaks published as values | trace-projection PR |
| T2 | major | off-roster canary key → `IndexError` (should refuse) | trace-projection PR |
| T3 | major | outcome classified by `"extracted" in reason`; schema-valid names spoof extraction-win | structured-outcome PR |
| T4 | major | three redaction bypasses (dict/list value under declared field; numeric echo; payload-local scrub) | trace-projection PR |
| T5 | major | `detect_leak` fails open on JSON-escaped canaries (non-ASCII/quotes/backslash) | trace-projection PR |
| T6 | major | competitor attribution by `name in reason` substring; prefix names frame the innocent | structured-outcome PR |
| T7 | major | audit has no signal for actual overspend (`spent > cap` audits clean) | trace-projection PR |
| T8 | major | no name-uniqueness enforcement (same as E4) | structured-outcome PR |
| T9 | minor | sequential scrubbing corrupts overlapping secrets (scrub longest-first) | trace-projection PR |
| T10 | minor | mask spoofing; declared redaction `mode` never honored | trace-projection PR |
| T11 | minor | `effective_doc` leaves capability-omitting providers uncapped (biases divergence to zero) | trace-projection PR |
| T12 | nit | `flag_sustained` mixed-competitor aggregation; TEST-PLAN T-037 row overstates verbatim scope | doc/assert |

Confirmed clean: determinism of all projections; fail-closed provider
selection; fail-closed payload withholding; no ban machinery; all four modules
pure.

## Subsystem 4 — lane/binding/weigh-in (trust chain)

Reviewer verdict: FINDINGS. **Remediation status (2026-08-24):**

- **Landed in #67** (`fix/binding-hash-coverage`): L1 (capability hash now
  covers the egress allowlist, per-policy `(resource, action, effect)`
  targeting, and the `maxInvocations` cap — every lane-enforced input) and L5
  (egress/policy-target/cap escape tests added). Independent review found and
  closed a follow-on blocker (the invocation cap) before merge.
- **Land-last (outcome-changing) batch:** L2 (draft class-ceiling enforcement =
  E7) and L4 (lane authorization gating the outcome) are the user-approved
  game-rule changes — decision recorded, BALANCE-REPORT regen required.
  L3 (in-match hire bonus keyed on name substring = E6) rides the same batch.
- **Follow-up:** L6 nit (`HIRE_DEPTH_CAP` sub-hire scope).

| id | sev | finding | disposition |
|---|---|---|---|
| L1 | major | capability hash does not cover egress allowlist or policy targeting — E1I binding defeated for those changes | binding PR |
| L2 | major | draft class-ceiling gate advisory only; `run_vault_match` never enforces it (= E7) | **decision node** — see below |
| L3 | major | in-match hire bonus keyed on name substring, farmable/dodgeable (= E6) | game-rule PR |
| L4 | major | lane authorization does not gate the match outcome; undeclared/denied capability still "executes" | **decision node** — see below |
| L5 | minor | escape-test coverage blind spot (only tool-add mutations); egress/policy-target changes untested | binding PR |
| L6 | nit | `HIRE_DEPTH_CAP` bounds caller chain length, not sub-hires declared inside a specialist | note / follow-up |

Confirmed clean: `evaluate_hire` ceiling math and fail-closed unknown-class
default; O(1) depth-cap refusal; determinism; hash DOES change for
tool/skill/function/modality/side-effect/policy-count mutations; deny-credit
farming floored.

## Design decisions requiring a human gate (not unilateral fixes)

Two findings are consequential design choices, not clear bugs — per the graph
methodology they become decision nodes with an ADR rather than a silent code
change:

- **DEC-LANE-GATES-OUTCOME (L4/E-comment):** should a policy-denied or
  undeclared capability *suppress the in-match effect* (fail-closed execution),
  or is the lane deliberately audit-only in the dry-run arena? The code comment
  currently claims "capability use goes through the lane or it does not happen",
  which the review shows is false — so at minimum the claim must change; whether
  the behaviour changes is the decision.
- **DEC-DRAFT-ENFORCEMENT (L2/E7):** should `run_vault_match` refuse an illegal
  fielding (class-ceiling breach / depth-cap) as a forfeit, or is draft legality
  a surface-layer concern the match engine trusts its caller to have checked?
  The Discover→Decide→Prove thesis argues for enforcement at Prove.

Both are filed as decision nodes on the graph; remediation of the mechanical
findings does not wait on them.
