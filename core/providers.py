"""Provider abstraction over the declared preference order (issue B3,
tests T-026..T-028).

Provider neutrality is an ADL promise; this module is where it either holds
or visibly breaks. It is pure and deterministic: no network, no credential
handling, no provider SDKs. Availability is a caller-supplied data table
(in the dry-run arena it comes from a fixture profile), never probed —
declaring a provider is not credential authorization, and a declared
provider whose credentials are absent fails closed with a stated reason
rather than silently falling back to something undeclared (T-026).

Selection contract:
  * Only providers in the declared order (model.providers.preferred, then
    .fallbacks, in declared sequence) are ever considered. An available but
    undeclared provider is invisible.
  * The first declared provider that is present and credentialed is
    selected. Every skip is recorded with a reason.
  * The selection's capabilities are checked against model.requirements.
    Anything missing yields status "degraded" with the missing list named —
    never silent success (T-027). "ok" means nothing was missing.
  * Nothing usable in the declared order -> status "unavailable",
    provider None: fail closed.

Divergence (T-028): the deterministic engine's only provider-sensitive
channel is the declared requirements — a provider whose contextWindow
capability is below the declared requirement caps the bot's effective fuel.
divergence_report() runs the same bots under each declared provider's
effective constraints and reports where outcomes diverge, measured and
published rather than hidden. Live cross-provider execution is a separate
approval-gated lane; this measures the declared-contract channel only.
"""
from __future__ import annotations

import copy

# Requirements checked against a provider's capability table. Booleans must
# be satisfied when declared true; numerics must meet or exceed the declared
# value; modalities must be a superset of the declared list.
_BOOL_REQS = ("toolCalling", "structuredOutput")
_NUM_REQS = ("contextWindow", "maxOutputTokens")


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def declared_order(doc: dict) -> list[str]:
    """The declared preference order, preferred first, deduplicated."""
    providers = (doc.get("model") or {}).get("providers") or {}
    order = []
    if providers.get("preferred"):
        order.append(providers["preferred"])
    for fb in providers.get("fallbacks") or []:
        if fb not in order:
            order.append(fb)
    return order


def _missing_requirements(requirements: dict, capabilities: dict) -> list[str]:
    missing = []
    for req in _BOOL_REQS:
        if requirements.get(req) and not capabilities.get(req):
            missing.append(req)
    for req in _NUM_REQS:
        declared = requirements.get(req)
        if declared is not None:
            offered = capabilities.get(req)
            # A non-numeric offered value is treated as unmet, not compared with
            # `<` (which would raise TypeError on e.g. a string) — this mirrors
            # effective_doc capping such a value to 0 (audit T11 consistency).
            if not _is_num(offered) or offered < declared:
                missing.append(req)
    declared_modes = set(requirements.get("modalities") or [])
    if declared_modes and not declared_modes <= set(capabilities.get("modalities") or []):
        missing.append("modalities")
    return missing


def select_provider(doc: dict, available: dict) -> dict:
    """Select a provider for `doc` from the caller-supplied availability
    table {name: {"credentials": bool, "capabilities": {...}}}.

    Returns {"provider", "status", "missing", "considered"} where status is
    "ok" | "degraded" | "unavailable" and considered records every declared
    provider examined with the outcome and reason (selection evidence,
    mirroring lane events).
    """
    requirements = (doc.get("model") or {}).get("requirements") or {}
    considered: list[dict] = []
    for name in declared_order(doc):
        entry = available.get(name)
        if entry is None:
            considered.append({"provider": name, "outcome": "skipped",
                               "reason": "not available"})
            continue
        if not entry.get("credentials"):
            considered.append({"provider": name, "outcome": "skipped",
                               "reason": "missing credentials (fail closed, "
                                         "no undeclared fallback)"})
            continue
        missing = _missing_requirements(requirements,
                                        entry.get("capabilities") or {})
        if missing:
            considered.append({"provider": name, "outcome": "selected-degraded",
                               "reason": "missing declared requirements: "
                                         + ", ".join(missing)})
            return {"provider": name, "status": "degraded",
                    "missing": missing, "considered": considered}
        considered.append({"provider": name, "outcome": "selected",
                           "reason": "credentialed, all declared requirements met"})
        return {"provider": name, "status": "ok", "missing": [],
                "considered": considered}
    return {"provider": None, "status": "unavailable", "missing": [],
            "considered": considered}


def effective_doc(doc: dict, capabilities: dict) -> dict:
    """The document as constrained by a provider's capabilities: declared
    numeric requirements are capped at what the provider actually offers.
    This is the deterministic engine's provider-sensitive channel — a lower
    provider contextWindow means less fuel on the scale.

    A provider that OMITS a numeric capability (or offers a non-numeric value)
    offers NONE of it, so the requirement caps to 0 — consistent with
    select_provider marking such an omission missing/degraded. Leaving it
    uncapped (the old behavior) handed the bot its full declared requirement,
    so a degraded provider produced the same effective fuel as a fully-capable
    one and biased the divergence report to zero (audit T11)."""
    eff = copy.deepcopy(doc)
    requirements = ((eff.get("model") or {}).get("requirements") or {})
    caps = capabilities or {}
    for req in _NUM_REQS:
        declared = requirements.get(req)
        if not _is_num(declared):
            continue  # non-numeric declared: leave it for _read_fuel to fault
        offered = caps.get(req)
        requirements[req] = min(declared, offered if _is_num(offered) else 0)
    return eff


def divergence_report(bot_a: dict, bot_b: dict, available: dict,
                      seeds: range | list) -> dict:
    """Run the same match under each provider usable by bot_a and measure
    behavioural divergence (T-028). Every divergent seed is listed — the
    report publishes mismatches, it never suppresses them."""
    try:  # local import: avoids a cycle at module load
        from arena import run_vault_match
    except ImportError:
        from core.arena import run_vault_match

    runs: dict[str, dict] = {}
    for name in declared_order(bot_a):
        entry = available.get(name)
        if not entry or not entry.get("credentials"):
            continue
        caps = entry.get("capabilities") or {}
        eff_a = effective_doc(bot_a, caps)
        runs[name] = {
            "selection": select_provider(bot_a, {name: entry}),
            "outcomes": {s: {"winner": t["winner"], "traceHash": t["traceHash"]}
                         for s in seeds
                         for t in [run_vault_match(eff_a, bot_b, seed=s)]},
        }
    providers = sorted(runs)
    seed_list = list(seeds)
    divergent: dict[int, dict] = {}
    outcome_divergent: list[int] = []
    if len(providers) >= 2:
        for s in seed_list:
            winners = {p: runs[p]["outcomes"][s]["winner"] for p in providers}
            hashes = {p: runs[p]["outcomes"][s]["traceHash"] for p in providers}
            if len(set(hashes.values())) > 1:
                same_winner = len(set(winners.values())) == 1
                divergent[s] = {"winners": winners,
                                "identical_outcome": same_winner}
                if not same_winner:
                    outcome_divergent.append(s)
    n = len(seed_list) or 1
    return {
        "providersCompared": providers,
        "seedsRun": seed_list,
        # Trace divergence: any byte of the replayable evidence differs
        # (fuel scale included). Outcome divergence: the winner changes.
        # Both are published; neither is suppressed.
        "divergentSeeds": divergent,
        "traceDivergenceRate": len(divergent) / n,
        "outcomeDivergentSeeds": outcome_divergent,
        "outcomeDivergenceRate": len(outcome_divergent) / n,
        "channel": ("declared numeric requirements capped by provider "
                    "capabilities (effective fuel); live provider execution "
                    "is a separate approval-gated lane"),
    }
