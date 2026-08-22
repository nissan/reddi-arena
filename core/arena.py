"""
Reddi Arena — shared core engine.

One implementation of weigh-in, drafting, and the Vault match, used identically
by the CLI and the web backend. Deterministic: no clock, no randomness except a
seed the caller supplies, no network.

BOUNDARIES (enforced, not decorative):
  * Prizes are ARENA-CREDIT on the x402-dry-run rail. No real value, no rail
    other than dry-run, no wallet, no settlement.
  * The mercenary price lives in an x-arena extension because ADL v0.2 has no
    price field (finding F-007). Marked provisional everywhere it surfaces.
  * This engine simulates competitor turns from a declared, seeded strategy. It
    does NOT call a model provider. Wiring real providers is a separate,
    approval-gated lane and is intentionally not done here.
"""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from weigh_in import weigh, classify, CLASSES  # noqa: E402
from lane import ExecutionLane, find_tool  # noqa: E402

ARENA_RAIL = "x402-dry-run"
ARENA_CURRENCY = "ARENA-CREDIT"

# League tier -> required conformance level. Purses require L3 (the payment
# extension is forbidden below it), so Rookie/Open are glory-only by the spec.
LEAGUE_TIERS = {
    "rookie": {"level": 1, "purse": False, "hiring": False},
    "open": {"level": 2, "purse": False, "hiring": False},
    "title": {"level": 3, "purse": True, "hiring": True},
}


def _yaml():
    import yaml
    return yaml


def load_adl(path: str) -> dict:
    return _yaml().safe_load(open(path))


def _canon(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _hash(obj) -> str:
    return "sha256:" + hashlib.sha256(_canon(obj).encode()).hexdigest()


# --------------------------------------------------------------------------
# Provisional price extension (F-007). ONE function reads it, so swapping to a
# real ADL v0.3 price field later is a one-line change.
# --------------------------------------------------------------------------
def advertised_price(merc_doc: dict) -> dict:
    """Read x-arena.price. Provisional pending ADL v0.3 (F-007)."""
    xarena = (merc_doc.get("extensions") or {}).get("x-arena") or {}
    price = xarena.get("price")
    if price is None:
        return {"amount": None, "currency": ARENA_CURRENCY, "provisional": True,
                "note": "no x-arena.price declared"}
    return {
        "amount": price.get("amount"),
        "currency": price.get("currency", ARENA_CURRENCY),
        "unit": price.get("unit", "per-match"),
        "provisional": True,
        "note": "x-arena.price is an Arena-local extension pending ADL v0.3 price field (F-007)",
    }


# --------------------------------------------------------------------------
# Weigh-in and draft
# --------------------------------------------------------------------------
@dataclass
class DraftResult:
    allowed: bool
    reason: str
    solo_au: int
    fielded_au: int
    entered_class: str
    fielded_class: str
    price: dict = field(default_factory=dict)
    au_delta: int = 0


def weigh_competitor(doc: dict, hires: list[dict] | None = None) -> dict:
    hire_certs = []
    for h in hires or []:
        c = weigh(h)
        hire_certs.append({"name": c["agent"], "au": c["soloAU"]})
    return weigh(doc, hire_certs)


# Draft rule (A5): a fielded specialist cannot itself field sub-hires in v0.1.
# The cap is checked before any weighing, so hire chains can never recurse.
HIRE_DEPTH_CAP = 1


def evaluate_hire_chain(competitor_doc: dict, chain: list[dict],
                        entered_class: str) -> DraftResult:
    """Evaluate a hire chain [specialist, specialist's-hire, ...].

    Depth beyond HIRE_DEPTH_CAP is refused at draft with a stated reason —
    deterministically and without weighing anything, so an adversarial chain of
    any length costs O(1).
    """
    depth = len(chain)
    if depth > HIRE_DEPTH_CAP:
        return DraftResult(
            allowed=False,
            reason=(f"transitive hire depth {depth} exceeds cap {HIRE_DEPTH_CAP}: "
                    f"a fielded specialist cannot itself field sub-hires in "
                    f"weights v0.1. Drop the sub-hire chain."),
            solo_au=0, fielded_au=0,
            entered_class=entered_class, fielded_class=entered_class,
        )
    if not chain:
        solo = weigh(competitor_doc)
        return DraftResult(
            allowed=True, reason="no hires requested.",
            solo_au=solo["soloAU"], fielded_au=solo["soloAU"],
            entered_class=entered_class, fielded_class=solo["soloClass"],
        )
    return evaluate_hire(competitor_doc, chain[0], entered_class)


def evaluate_hire(competitor_doc: dict, merc_doc: dict, entered_class: str) -> DraftResult:
    """Decide whether a competitor may hire a specialist without breaching its class."""
    solo = weigh(competitor_doc)
    merc = weigh(merc_doc)
    fielded = weigh_competitor(competitor_doc, [merc_doc])
    delta = fielded["fieldedAU"] - solo["soloAU"]
    price = advertised_price(merc_doc)

    ceilings = dict(CLASSES)
    entered_ceiling = ceilings.get(entered_class, 0)
    breaches = fielded["fieldedAU"] > entered_ceiling

    if breaches:
        return DraftResult(
            allowed=False,
            reason=(f"hire adds {delta} AU -> {fielded['fieldedAU']} AU, breaching "
                    f"{entered_class} ceiling {entered_ceiling}. Enter a heavier class "
                    f"or drop the hire."),
            solo_au=solo["soloAU"], fielded_au=fielded["fieldedAU"],
            entered_class=entered_class, fielded_class=fielded["fieldedClass"],
            price=price, au_delta=delta,
        )
    return DraftResult(
        allowed=True,
        reason=f"hire adds {delta} AU; still legal in {entered_class}.",
        solo_au=solo["soloAU"], fielded_au=fielded["fieldedAU"],
        entered_class=entered_class, fielded_class=fielded["fieldedClass"],
        price=price, au_delta=delta,
    )


# --------------------------------------------------------------------------
# Vault match engine — deterministic simulation
# --------------------------------------------------------------------------
# A bot's play is read from its x-arena.strategy block (attack/defend profiles),
# NOT from a live model. Two numbers per bot: attack (0-100) and defense (0-100).
# A hired source-auditor grants a defense bonus (it catches untrusted-source
# citation traps), modelling the real capability the mercenary declares.

def _strategy(doc: dict) -> dict:
    xa = (doc.get("extensions") or {}).get("x-arena") or {}
    strat = xa.get("strategy") or {}
    return {"attack": int(strat.get("attack", 50)), "defense": int(strat.get("defense", 50))}


def _fuel_cap(doc: dict) -> int:
    reqs = (doc.get("model") or {}).get("requirements") or {}
    # Antweight fuel model: contextWindow tokens are the cap, minimum 2000.
    return max(int(reqs.get("contextWindow", 8000)), 2000)


@dataclass
class Turn:
    n: int
    attacker: str
    strategy: str
    probe_strength: int
    defense_strength: int
    fuel_spent: int
    outcome: str  # "held" | "extracted"


def run_vault_match(bot_a: dict, bot_b: dict, seed: int = 0,
                    hire_a: dict | None = None, hire_b: dict | None = None,
                    max_turns: int = 12,
                    cert_a: dict | None = None, cert_b: dict | None = None) -> dict:
    """
    Deterministic Vault match. Given identical inputs and seed, always returns
    an identical result and trace. This is the substrate the replay renders.
    """
    names = [bot_a["metadata"]["name"], bot_b["metadata"]["name"]]
    strat = [_strategy(bot_a), _strategy(bot_b)]
    fuel = [_fuel_cap(bot_a), _fuel_cap(bot_b)]

    # B1: every capability use in the match routes through each bot's bounded
    # execution lane — declared, policy-matched, locally bound, or refused.
    # Lane decisions are recorded as evidence; they never alter the seeded
    # strategy outcome (which is simulation, not capability execution).
    #
    # E1I: each lane is bound to the capability hash that was WEIGHED IN
    # (cert_a/cert_b from the draft; self-weighed when not provided). A
    # fielded document that no longer matches its certificate is an escape
    # attempt: the escaping bot forfeits before any turn runs (T-078), with
    # the binding refusal recorded as evidence.
    live_certs = [weigh(bot_a), weigh(bot_b)]
    bound_certs = [cert_a or live_certs[0], cert_b or live_certs[1]]
    bound_hashes = [c["capabilityHash"] for c in bound_certs]
    lanes = [ExecutionLane(bot_a, bound_hashes[0], live_certs[0]["capabilityHash"]),
             ExecutionLane(bot_b, bound_hashes[1], live_certs[1]["capabilityHash"])]
    if lanes[0].escaped or lanes[1].escaped:
        if lanes[0].escaped and lanes[1].escaped:
            winner, reason = -1, ("both fielded documents differ from their "
                                  "weighed certificates; match void")
        else:
            escapee = 0 if lanes[0].escaped else 1
            winner = 1 - escapee
            reason = (f"{names[escapee]} forfeits: fielded document does not "
                      f"match its weighed certificate (binding escape)")
        return _finalize(names, [], winner, reason, [True, True], fuel,
                         list(fuel), seed, lanes, bound_hashes)
    probe_tool = [find_tool(bot_a, "probe"), find_tool(bot_b, "probe")]
    seal_tool = [find_tool(bot_a, "seal"), find_tool(bot_b, "seal")]

    # A hired source-auditor raises defense: it flags untrusted-source citation
    # traps the opponent would otherwise land. Bounded, declared, honest.
    defense_bonus = [0, 0]
    for i, hire in enumerate([hire_a, hire_b]):
        if hire and "source-auditor" in hire["metadata"]["name"]:
            defense_bonus[i] = 15

    # Deterministic pseudo-random stream from the seed (LCG; not for crypto).
    state = (seed * 2654435761 + 40503) & 0xFFFFFFFF

    def nxt(mod: int) -> int:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state % mod

    turns: list[Turn] = []
    secret_held = [True, True]
    fuel_left = list(fuel)
    turn_fuel = 60  # flat cost per turn in this reference model

    # Who opens is decided by seed parity, not by slot position. Previously
    # `attacker = n % 2` meant bot B always struck first, and since matches
    # resolve in ~3.6 turns the opener won ~92% of the time. Alternating by
    # seed keeps the match deterministic while removing the systematic bias.
    # Caught by tools/simulate.py; see docs/BALANCE-REPORT.md.
    opener = seed % 2
    for n in range(1, max_turns + 1):
        attacker = (opener + n - 1) % 2
        defender = 1 - attacker

        if fuel_left[attacker] < turn_fuel:
            # Attacker sputters — out of fuel. Defender wins.
            turns.append(Turn(n, names[attacker], "sputter", 0, 0, 0, "held"))
            winner = defender
            reason = f"{names[attacker]} ran out of fuel (sputter)"
            return _finalize(names, turns, winner, reason, secret_held, fuel, fuel_left, seed, lanes, bound_hashes)

        probe = strat[attacker]["attack"] + nxt(20) - 10
        defense = strat[defender]["defense"] + defense_bonus[defender] + nxt(20) - 10
        fuel_left[attacker] -= turn_fuel

        # Capability use goes through the lane or it does not happen (B1).
        if probe_tool[attacker]:
            lanes[attacker].invoke(probe_tool[attacker])

        if probe > defense:
            secret_held[defender] = False
            turns.append(Turn(n, names[attacker], "extract", probe, defense, turn_fuel, "extracted"))
            winner = attacker
            reason = f"{names[attacker]} extracted {names[defender]}'s secret on turn {n}"
            return _finalize(names, turns, winner, reason, secret_held, fuel, fuel_left, seed, lanes, bound_hashes)

        if seal_tool[defender]:
            lanes[defender].invoke(seal_tool[defender])
        turns.append(Turn(n, names[attacker], "probe", probe, defense, turn_fuel, "held"))

    # Turn limit reached, both secrets held -> tie-break on fuel efficiency.
    if fuel_left[0] != fuel_left[1]:
        winner = 0 if fuel_left[0] > fuel_left[1] else 1
        reason = f"turn limit; {names[winner]} won on fuel efficiency"
    else:
        winner = -1
        reason = "turn limit; both secrets held; draw"
    return _finalize(names, turns, winner, reason, secret_held, fuel, fuel_left, seed, lanes, bound_hashes)


def _finalize(names, turns, winner, reason, secret_held, fuel, fuel_left, seed,
              lanes=None, bound_hashes=None) -> dict:
    trace = {
        "format": "vault",
        "seed": seed,
        "competitors": names,
        "turns": [asdict(t) for t in turns],
        "secretsHeld": secret_held,
        "fuelStart": fuel,
        "fuelLeft": fuel_left,
        "winner": names[winner] if winner >= 0 else None,
        "result": "draw" if winner < 0 else "decisive",
        "reason": reason,
        "rail": ARENA_RAIL,
        "prizeCurrency": ARENA_CURRENCY,
    }
    if lanes is not None:
        trace["laneEvents"] = {names[i]: lanes[i].events for i in range(2)}
    if bound_hashes is not None:
        # E1I / T-079: every trace records the exact hash each lane was bound
        # to, so a trace is auditable against its weigh-in certificates.
        trace["boundHash"] = {names[i]: bound_hashes[i] for i in range(2)}
    trace["traceHash"] = _hash({k: v for k, v in trace.items() if k != "traceHash"})
    return trace


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("bot_a")
    ap.add_argument("bot_b")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    r = run_vault_match(load_adl(a.bot_a), load_adl(a.bot_b), seed=a.seed)
    print(json.dumps(r, indent=2))
