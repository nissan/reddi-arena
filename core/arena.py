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
from lifecycle import MatchLifecycle  # noqa: E402
from fuel import FuelMeter, budget_gate, TURN_COST  # noqa: E402

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
def _mm(x) -> dict:
    """Coerce a should-be-mapping to a dict (audit E2): a malformed container
    reads as empty instead of raising AttributeError on `.get`."""
    return x if isinstance(x, dict) else {}


def advertised_price(merc_doc: dict) -> dict:
    """Read x-arena.price. Provisional pending ADL v0.3 (F-007)."""
    xarena = _mm(_mm(merc_doc.get("extensions") if isinstance(merc_doc, dict) else {}).get("x-arena"))
    price = _mm(xarena.get("price"))
    if not price:
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
# Scope (audit L6): the cap bounds the length of the caller-supplied hire CHAIN
# passed to evaluate_hire_chain. Sub-hires a specialist declares INSIDE its own
# ADL are not a separate vector — the engine never reads or fields a hire's own
# embedded hires (a hire contributes only its solo weight and declared grants),
# so an embedded sub-hire declaration is inert, not an unbounded chain.
HIRE_DEPTH_CAP = 1

# Arena-local ceiling on the defense bonus a single hire's DECLARED grant
# (extensions.x-arena.grants.defenseBonus) may confer, so a mercenary cannot
# declare an unbounded advantage (audit E6/L3).
DEFENSE_BONUS_CAP = 15

# The known weight-class names (CLASSES is a list of (name, ceiling) pairs).
# Used to validate a caller-supplied entered class before draft enforcement.
CLASS_NAMES = frozenset(name for name, _ in CLASSES)


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
# A hire grants a defense bonus only through its DECLARED x-arena grant (it
# catches untrusted-source citation traps), modelling the real capability the
# mercenary declares — read from the document, not inferred from its name.

def _dig(doc, *keys):
    """Walk nested mappings. Returns (value_or_None, ok); ok is False if any
    intermediate is present but not a mapping — a malformed declaration the
    caller resolves to a defined fault, never an AttributeError (audit E2)."""
    cur = doc
    for k in keys:
        if cur is None:
            return None, True
        if not isinstance(cur, dict):
            return None, False
        cur = cur.get(k)
    return cur, True


def _is_number(x) -> bool:
    # bool is an int subclass but is never a valid numeric declaration here.
    # A Python int is arbitrary-precision and always usable (int()/comparisons
    # never overflow); calling math.isfinite() on a huge int would itself raise
    # OverflowError, so ints skip that check. Only floats need the inf/nan test.
    import math
    if isinstance(x, bool):
        return False
    if isinstance(x, int):
        return True
    return isinstance(x, float) and math.isfinite(x)


def _read_strategy(doc: dict) -> tuple[dict | None, str | None]:
    """Fault-checked read of the declared play profile (B2 / T-024).

    ARENA-PROFILE-v0.1 declares strategy as {attack: 0-100, defense: 0-100}.
    A declaration the engine cannot read (non-numeric, non-mapping container)
    or one outside the declared domain is the deterministic analogue of a
    crashed or hung competitor: it resolves to a defined forfeit before the
    first turn instead of an exception hanging the match (audit E2)."""
    strat, ok = _dig(doc, "extensions", "x-arena", "strategy")
    if not ok:
        return None, "unreadable strategy declaration (malformed extensions/x-arena)"
    strat = strat if strat is not None else {}
    if not isinstance(strat, dict):
        return None, "unreadable strategy declaration (strategy is not a mapping)"
    attack_raw = strat.get("attack", 50)
    defense_raw = strat.get("defense", 50)
    if not (_is_number(attack_raw) and _is_number(defense_raw)):
        return None, "unreadable strategy declaration (non-numeric attack/defense)"
    attack, defense = int(attack_raw), int(defense_raw)
    if not (0 <= attack <= 100 and 0 <= defense <= 100):
        return None, (f"strategy outside the declared 0-100 domain "
                      f"(attack={attack}, defense={defense})")
    return {"attack": attack, "defense": defense}, None


def _read_fuel(doc: dict) -> tuple[int, str | None]:
    """Fault-checked fuel cap. Antweight fuel model: contextWindow tokens are
    the cap, minimum 2000. A non-mapping requirements block or a non-numeric
    contextWindow is a competitor fault (audit E2/E3).

    contextWindow must be a real number — a STRING numeral is rejected here
    exactly as tools/weigh_in.py rejects it for AU (it awards 0 AU for a
    non-numeric value). Accepting `int("999999")` here while weigh awards 0
    AU was a weight-class dodge: a huge fuel tank on a featherweight-free
    declaration (audit E3)."""
    reqs, ok = _dig(doc, "model", "requirements")
    if not ok:
        return 0, "unreadable fuel declaration (malformed model/requirements)"
    reqs = reqs if reqs is not None else {}
    if not isinstance(reqs, dict):
        return 0, "unreadable fuel declaration (requirements is not a mapping)"
    cw = reqs.get("contextWindow", 8000)
    if not _is_number(cw):
        return 0, "unreadable fuel declaration (non-numeric contextWindow)"
    return max(int(cw), 2000), None


def _competitor_name(doc: dict) -> str | None:
    """Defensive read of the competitor name (audit E9). Missing/blank name,
    or a non-mapping metadata block, is a fault — never a KeyError or
    AttributeError mid-setup."""
    meta = doc.get("metadata") if isinstance(doc, dict) else None
    name = meta.get("name") if isinstance(meta, dict) else None
    return name if isinstance(name, str) and name else None


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
                    cert_a: dict | None = None, cert_b: dict | None = None,
                    entered_a: str | None = None,
                    entered_b: str | None = None) -> dict:
    """
    Deterministic Vault match. Given identical inputs and seed, always returns
    an identical result and trace. This is the substrate the replay renders.
    """
    # M2 (audit re-review): a top-level non-mapping document — including the
    # None that yaml.safe_load returns for an empty file — is coerced to an
    # empty dict here so the whole match resolves as a fault forfeit rather
    # than an AttributeError constructing the lane.
    bot_a = bot_a if isinstance(bot_a, dict) else {}
    bot_b = bot_b if isinstance(bot_b, dict) else {}

    # E9: names are read defensively; a missing name is a fault resolved as a
    # forfeit below, never a KeyError mid-setup. Slot placeholders keep the
    # trace well-formed even when a name is absent.
    raw_names = [_competitor_name(bot_a), _competitor_name(bot_b)]
    names = [raw_names[i] or f"unnamed-competitor-{i}" for i in range(2)]
    name_faults = [None if raw_names[i] else "missing metadata.name" for i in range(2)]

    # B2: the lifecycle state machine is the spine of the match. Every match
    # walks scheduled -> weighing -> binding -> (in-progress ->) terminal, and
    # only transitions in lifecycle.LEGAL exist — an undefined path raises
    # instead of producing a trace, so every trace records a legal path.
    lc = MatchLifecycle()
    lc.advance("weighing", "computing weigh-in certificates for both competitors")

    # Audit E4/T8: the trace's per-competitor evidence maps (laneEvents,
    # boundHash, fuelAccounting) are keyed by name, so two competitors sharing
    # a name would silently collapse one bot's evidence into the other's.
    # Distinct names are required; a collision voids the match before any
    # evidence is built.
    # Guard on the EFFECTIVE names (after placeholder assignment), not the raw
    # declared names: a document literally named "unnamed-competitor-1" against
    # an unnamed opponent collides on the effective key even though the raw
    # names differ (audit review). Two unnamed docs stay distinct (their
    # placeholders are index 0 vs 1), so this never false-voids.
    if names[0] == names[1]:
        lc.advance("binding", "name-collision check")
        _reason = (f"both competitors resolve to the same name {names[0]!r}; "
                   f"match void (names must be distinct for auditable evidence)")
        lc.advance("void", _reason)
        return _finalize(names, [], -1, _reason, [True, True], [0, 0],
                         [0, 0], seed, None, None, lc, None,
                         outcome_kind="void", at_fault=list(names))

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
    lc.advance("binding", "binding execution lanes to the weighed capability hashes")
    lanes = [ExecutionLane(bot_a, bound_hashes[0], live_certs[0]["capabilityHash"]),
             ExecutionLane(bot_b, bound_hashes[1], live_certs[1]["capabilityHash"])]

    # B2 / T-024: competitor faults (unreadable or out-of-domain declarations
    # — the deterministic analogue of crash and hang) are read fault-checked
    # here so they resolve at binding as defined outcomes, never exceptions.
    strat_read = [_read_strategy(bot_a), _read_strategy(bot_b)]
    fuel_read = [_read_fuel(bot_a), _read_fuel(bot_b)]
    strat = [s for s, _ in strat_read]
    fuel = [f for f, _ in fuel_read]
    faults = [name_faults[i] or strat_read[i][1] or fuel_read[i][1]
              for i in range(2)]

    # B4: fuel is charged ONLY through the meters; every charge is an
    # itemized ledger entry, and the trace's fuelAccounting reconciles with
    # the ledger by construction (T-031).
    meters = [FuelMeter(fuel[0]), FuelMeter(fuel[1])]

    if lanes[0].escaped or lanes[1].escaped:
        if lanes[0].escaped and lanes[1].escaped:
            winner, reason = -1, ("both fielded documents differ from their "
                                  "weighed certificates; match void")
            _kind, _fault = "void", list(names)
            lc.advance("void", reason)
        else:
            escapee = 0 if lanes[0].escaped else 1
            winner = 1 - escapee
            reason = (f"{names[escapee]} forfeits: fielded document does not "
                      f"match its weighed certificate (binding escape)")
            _kind, _fault = "forfeit", [names[escapee]]
            lc.advance("forfeit", reason)
        return _finalize(names, [], winner, reason, [True, True], fuel,
                         list(fuel), seed, lanes, bound_hashes, lc, meters,
                         outcome_kind=_kind, at_fault=_fault)

    if faults[0] or faults[1]:
        if faults[0] and faults[1]:
            winner = -1
            reason = (f"both competitors scratched — {names[0]}: {faults[0]}; "
                      f"{names[1]}: {faults[1]}; match void")
            _kind, _fault = "void", list(names)
            lc.advance("void", reason)
        else:
            faulty = 0 if faults[0] else 1
            winner = 1 - faulty
            reason = f"{names[faulty]} forfeits before turn 1: {faults[faulty]}"
            _kind, _fault = "forfeit", [names[faulty]]
            lc.advance("forfeit", reason)
        return _finalize(names, [], winner, reason, [True, True], fuel,
                         list(fuel), seed, lanes, bound_hashes, lc, meters,
                         outcome_kind=_kind, at_fault=_fault)

    # Draft enforcement (audit E7/L2): a hire that breaches the weight class its
    # employer ENTERED is an illegal fielding — a pre-turn forfeit, not a played
    # advantage. The draft class-ceiling check used to be advisory: run_vault_match
    # played any hire regardless. Now, when the caller states the entered class,
    # an over-ceiling fielding forfeits before turn 1 (both illegal -> void). With
    # no entered class stated — internal parity/balance runs measuring hire effect
    # — the hire plays as before, so those results are unchanged.
    #
    # Precedence note: this gate follows the escape (365) and fault (382) gates,
    # so a competitor whose opponent escapes/faults first wins before its own
    # illegal fielding is evaluated. That is the intended "first terminal state
    # wins" ordering — the illegal hire never plays, so it confers no advantage.
    #
    # entered_* is a TRUSTED control parameter (the arena operator's declared
    # draft class), not a competitor document. An invalid class is a caller/config
    # bug and must FAIL LOUDLY: mapping an unknown or mis-cased name to the
    # ceiling-0 default would silently forfeit the employer with a trace
    # indistinguishable from a genuine breach (audit review). It is validated
    # against CLASSES before it can reach the ceiling lookup — this raise is a
    # config error, distinct from the never-raise contract that governs the
    # untrusted competitor documents.
    draft_faults = [None, None]
    for i, (bot, hire, entered) in enumerate(
            [(bot_a, hire_a, entered_a), (bot_b, hire_b, entered_b)]):
        if not isinstance(hire, dict) or entered is None:
            continue
        if not isinstance(entered, str) or entered not in CLASS_NAMES:
            raise ValueError(
                f"entered_{'ab'[i]}={entered!r} is not a known weight class "
                f"{sorted(CLASS_NAMES)}; a valid entered class is required to "
                f"enforce the draft ceiling")
        verdict = evaluate_hire(bot, hire, entered)
        if not verdict.allowed:
            draft_faults[i] = verdict.reason
    if draft_faults[0] or draft_faults[1]:
        if draft_faults[0] and draft_faults[1]:
            winner = -1
            reason = (f"both competitors field illegal hires — {names[0]}: "
                      f"{draft_faults[0]}; {names[1]}: {draft_faults[1]}; match void")
            _kind, _fault = "void", list(names)
            lc.advance("void", reason)
        else:
            bad = 0 if draft_faults[0] else 1
            winner = 1 - bad
            reason = (f"{names[bad]} forfeits before turn 1: illegal fielding — "
                      f"{draft_faults[bad]}")
            _kind, _fault = "forfeit", [names[bad]]
            lc.advance("forfeit", reason)
        return _finalize(names, [], winner, reason, [True, True], fuel,
                         list(fuel), seed, lanes, bound_hashes, lc, meters,
                         outcome_kind=_kind, at_fault=_fault)

    # B4 / T-029: the budget-check eval gate runs at the DECLARED thresholds
    # before any turn — a bot that would exceed its own declaration the
    # moment it plays fails here as a defined pre-turn outcome.
    gates = [budget_gate(bot_a, fuel[0]), budget_gate(bot_b, fuel[1])]
    if not (gates[0]["passed"] and gates[1]["passed"]):
        gate_failed = [names[i] for i in range(2) if not gates[i]["passed"]]
        if not gates[0]["passed"] and not gates[1]["passed"]:
            winner = -1
            reason = (f"both competitors fail the budget gate — {names[0]}: "
                      f"{gates[0]['reason']}; {names[1]}: {gates[1]['reason']}; "
                      f"match void")
            _kind, _fault = "void", list(names)
            lc.advance("void", reason)
        else:
            gated = 0 if not gates[0]["passed"] else 1
            winner = 1 - gated
            reason = f"{names[gated]} forfeits before turn 1: {gates[gated]['reason']}"
            _kind, _fault = "forfeit", [names[gated]]
            lc.advance("forfeit", reason)
        return _finalize(names, [], winner, reason, [True, True], fuel,
                         list(fuel), seed, lanes, bound_hashes, lc, meters,
                         outcome_kind=_kind, at_fault=_fault, gate_failed=gate_failed)

    lc.advance("in-progress", "binding and declarations verified; turn loop opened")
    probe_tool = [find_tool(bot_a, "probe"), find_tool(bot_b, "probe")]
    seal_tool = [find_tool(bot_a, "seal"), find_tool(bot_b, "seal")]

    # A hire raises its employer's defense only by a DECLARED, bounded grant in
    # its own ADL (extensions.x-arena.grants.defenseBonus) — never by its name.
    # Keying on a name substring was both farmable (any doc named
    # "...source-auditor..." claimed +15 for free) and dodgeable (a real auditor
    # named otherwise earned nothing) — audit E6/L3. The grant is fault-checked
    # and clamped to [0, DEFENSE_BONUS_CAP] so a mercenary cannot declare its way
    # to an unbounded advantage.
    defense_bonus = [0, 0]
    for i, hire in enumerate([hire_a, hire_b]):
        if not hire:
            continue
        granted, ok = _dig(hire, "extensions", "x-arena", "grants", "defenseBonus")
        if ok and _is_number(granted) and granted > 0:
            defense_bonus[i] = min(int(granted), DEFENSE_BONUS_CAP)

    # Deterministic pseudo-random stream from the seed (LCG; not for crypto).
    state = (seed * 2654435761 + 40503) & 0xFFFFFFFF

    def nxt(mod: int) -> int:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state % mod

    turns: list[Turn] = []
    secret_held = [True, True]
    # B4: a turn still costs the same flat 60 tokens the reference model
    # always charged, but the charge is itemized (prompt + completion)
    # through the meter — see core/fuel.py.
    turn_fuel = TURN_COST

    # Who opens is decided by seed parity, not by slot position. Previously
    # `attacker = n % 2` meant bot B always struck first, and since matches
    # resolve in ~3.6 turns the opener won ~92% of the time. Alternating by
    # seed keeps the match deterministic while removing the systematic bias.
    # Caught by tools/simulate.py; see docs/BALANCE-REPORT.md.
    opener = seed % 2
    for n in range(1, max_turns + 1):
        attacker = (opener + n - 1) % 2
        defender = 1 - attacker

        charge = meters[attacker].charge(n)
        if charge["outcome"] != "ok":
            # Attacker sputters — fuel exhausted, a defined outcome (T-030).
            # A mid-turn sputter charged the prompt but the completion never
            # happened; the ledger records the partial turn.
            turns.append(Turn(n, names[attacker], "sputter", 0, 0,
                              charge["prompt"], "held"))
            winner = defender
            reason = (f"{names[attacker]} ran out of fuel "
                      f"({charge['outcome']}: "
                      + ("exhausted mid-turn after the prompt charge"
                         if charge["outcome"] == "sputter-mid"
                         else "could not afford the turn") + ")")
            lc.advance("forfeit", reason)
            return _finalize(names, turns, winner, reason, secret_held, fuel,
                             _remaining(meters), seed, lanes, bound_hashes, lc, meters,
                             outcome_kind="forfeit", at_fault=[names[attacker]])

        probe = strat[attacker]["attack"] + nxt(20) - 10
        defense = strat[defender]["defense"] + defense_bonus[defender] + nxt(20) - 10

        # Capability use goes through the lane or it does not happen — FAIL
        # CLOSED (audit L4). The probe's extraction effect lands ONLY if the
        # attacker actually holds the probe capability AND the lane authorized
        # the invoke. An undeclared probe (no tool) or a lane-refused one
        # (undeclared-tool / denied-by-policy / no-matching-policy /
        # invocation-limit / binding-mismatch) produces NO in-match effect: the
        # attack fizzles and the secret stays held, rather than extracting
        # anyway. The refusal is still recorded in laneEvents as evidence.
        probe_authorized = False
        if probe_tool[attacker]:
            probe_ev = lanes[attacker].invoke(probe_tool[attacker])
            probe_authorized = bool(probe_ev.get("allowed"))

        if probe_authorized and probe > defense:
            secret_held[defender] = False
            turns.append(Turn(n, names[attacker], "extract", probe, defense, turn_fuel, "extracted"))
            winner = attacker
            reason = f"{names[attacker]} extracted {names[defender]}'s secret on turn {n}"
            lc.advance("decided", reason)
            return _finalize(names, turns, winner, reason, secret_held, fuel,
                             _remaining(meters), seed, lanes, bound_hashes, lc, meters,
                             outcome_kind="extraction", at_fault=[])

        # The defender's seal is recorded through the lane as evidence; it has no
        # mechanical effect on the seeded defense number, so there is no effect to
        # suppress on refusal (unlike the probe above).
        if seal_tool[defender]:
            lanes[defender].invoke(seal_tool[defender])
        # A fizzled (unauthorized) probe and a genuine under-defense probe both
        # leave the secret held; the laneEvents distinguish them for audit.
        strategy = "probe" if probe_authorized else "fizzle"
        turns.append(Turn(n, names[attacker], strategy, probe, defense, turn_fuel, "held"))

    # Turn limit reached, both secrets held -> tie-break on fuel efficiency.
    fuel_left = _remaining(meters)
    if fuel_left[0] != fuel_left[1]:
        winner = 0 if fuel_left[0] > fuel_left[1] else 1
        reason = f"turn limit; {names[winner]} won on fuel efficiency"
        _kind = "fuel"
        lc.advance("decided", reason)
    else:
        winner = -1
        reason = "turn limit; both secrets held; draw"
        _kind = "draw"
        lc.advance("draw", reason)
    return _finalize(names, turns, winner, reason, secret_held, fuel, fuel_left,
                     seed, lanes, bound_hashes, lc, meters,
                     outcome_kind=_kind, at_fault=[])


def _remaining(meters) -> list[int]:
    return [m.remaining for m in meters]


def _finalize(names, turns, winner, reason, secret_held, fuel, fuel_left, seed,
              lanes=None, bound_hashes=None, lifecycle=None, meters=None,
              outcome_kind=None, at_fault=None, gate_failed=None) -> dict:
    # Audit E5/T3/T6: the machine-readable outcome and the at-fault competitors
    # are STRUCTURED fields, so downstream consumers (scoring, emit, audit,
    # chain settlement) never parse the human-readable `reason` string —
    # schema-valid names could otherwise spoof "extracted" or frame the
    # innocent via substring matches. `result` distinguishes void from draw.
    result = {"extraction": "decisive", "fuel": "decisive", "forfeit": "decisive",
              "draw": "draw", "void": "void"}.get(outcome_kind,
              "draw" if winner < 0 else "decisive")
    trace = {
        "format": "vault",
        "seed": seed,
        "competitors": names,
        "turns": [asdict(t) for t in turns],
        "secretsHeld": secret_held,
        "fuelStart": fuel,
        "fuelLeft": fuel_left,
        "winner": names[winner] if winner >= 0 else None,
        "result": result,
        "outcomeKind": outcome_kind,
        "atFault": list(at_fault or []),
        # Structural marker for WHICH competitors failed the pre-turn budget
        # gate, so the emitted eval.checked event never has to parse the reason
        # prose to label the gate (audit review minor).
        "budgetGateFailed": list(gate_failed or []),
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
    if lifecycle is not None:
        # B2 / T-023: the trace carries the full lifecycle path, hash-covered,
        # and no non-terminal trace can be produced.
        # A real exception, not an assert: the "no non-terminal trace can be
        # produced" invariant (B2/T-023) must hold under `python3 -O`, which
        # strips asserts (audit E10).
        if not lifecycle.terminal:
            raise RuntimeError(
                f"match finalized in non-terminal lifecycle state "
                f"{lifecycle.state!r}")
        trace["lifecycle"] = lifecycle.snapshot()
    if meters is not None:
        # B4 / T-031: the itemized fuel ledger ships in the trace,
        # hash-covered, and reconciles exactly with fuelStart/fuelLeft.
        trace["fuelAccounting"] = {names[i]: meters[i].snapshot()
                                   for i in range(2)}
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
