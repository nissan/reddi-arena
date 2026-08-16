# Reddi Arena — Independent Analyst Review Brief

You are reviewing `plan-v0.1` of a programme that proposes a competitive game as
a proof use case for RAP and ADL v0.2. Your job is to find where it is wrong,
not to confirm it is reasonable.

## Run this first

```bash
python3 tools/plan_lint.py          # structural invariants L1-L7
python3 tools/weigh_in.py adl/antweight-vault-defender.adl.yaml \
        --hire adl/mercenary-source-auditor.adl.yaml
```

The linter answers the mechanical questions — cycles, orphan tests, phase
inversions, missing boundaries — so your judgement can go to the parts a script
cannot check. A clean lint means the plan is *coherent*, not that it is *right*.

## Known weaknesses — start here

These are the places the author already believes the plan is weakest. Confirm,
quantify, or refute them.

1. **The reference ADL documents are unvalidated.** They were reconstructed from
   a prose context pack, not read from `ADL-v0.2.schema.json`. Field names and
   enum values are hypotheses. `A1`/`T-001` exists to correct this and is the
   single root of the entire dependency graph — every other issue is downstream
   of it. If `A1` reveals substantial drift, the weight formula, the fixtures,
   and both reference bots may need rework. **Is a single-root plan with a
   verification-shaped root acceptable, or should P0 be restructured so more
   work can start in parallel?**

2. **The weight formula's coefficients are invented.** They were calibrated so
   the worked example demonstrates a class bump, not from any model of real
   compute cost. Is a deliberately arbitrary-but-frozen formula defensible for
   a first season, or does it poison the competitive claim?

3. **Static weighing cannot catch under-declaration.** A player can declare a
   small `contextWindow` and rely on more. `E2I` measures this at runtime and
   routes to human review. **Is human review a scalable anti-cheat posture, or
   is it a euphemism for "unsolved"?**

4. **The programme is a distraction risk.** The 2026-08-01 correction stopped a
   backlog loop for spending time on lifecycle churn while overstating planning
   as implementation. This plan is 16 epics, 36 issues, 114 tasks, and 95 tests
   — produced before a single line of Arena code exists. **Assess honestly
   whether this document is a repeat of exactly that failure mode in a new
   costume.** The counter-argument is that P4 delivers the external tester
   evidence the release ladder actually needs; judge whether that justifies P0
   through P3, or whether the programme should be cut to a much smaller proof.

5. **Injection is a designed-in feature.** Vault deliberately rewards prompt
   injection between competitors. `E14` contains it to the match. Is
   containment-by-design sufficient, or does hosting an adversarial arena create
   a reputational and safety exposure the protocol should not take on?

6. **Reputation is competitive scoring by rivals.** Commit-reveal reduces
   retaliation but does not eliminate collusion, sockpuppets, or coordinated
   rating manipulation. Is the eligibility gating in `C8` load-bearing enough?

## Questions the plan does not answer

- What is the minimum viable proof? Could P0 plus a stripped P1 demonstrate
  everything of protocol value, making P2–P4 optional?
- Who operates this? The plan has swimlanes but no capacity model and no owners.
  At what team size does the sequencing become fiction?
- What happens to player-authored ADL documents on shutdown? There is no data
  lifecycle, retention, or export commitment anywhere in the plan.
- Arena credits have no redemption path today. What stops a secondary market
  forming anyway, and does that drag the programme toward the blocked P5?
- The plan assumes players will hand-write ADL. Is that demand real, or is the
  expert tier hypothetical?

## What a pass verdict must include

- Whether `A1` should gate as much as it currently does.
- A recommended cut line: which epics you would delete outright.
- Any invariant the linter should enforce but does not.
- Any place the plan claims more maturity than its evidence supports — measured
  against the source-priority and claims-discipline rules the programme itself
  adopts in `F4`.

## What this plan explicitly does not claim

It does not claim audit completion, mainnet readiness, production readiness,
live rail integration, wallet custody, or that any listed test currently passes.
Only `tools/plan_lint.py` and `tools/weigh_in.py` execute today; every other
artifact is a design document.
