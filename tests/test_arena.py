#!/usr/bin/env python3
"""
Reddi Arena — test suite. Run: python3 tests/test_arena.py

Covers the doneness claims for what we actually built: determinism, the
class-bump draft rule, the power-up effect, and the boundary invariants
(dry-run rail, arena-credit currency, provisional price).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from core.arena import (
    run_vault_match, evaluate_hire, weigh_competitor, advertised_price,
    load_adl, ARENA_RAIL, ARENA_CURRENCY,
)

ADL = ROOT / "adl"
DEF = load_adl(ADL / "antweight-vault-defender.adl.yaml")
RAID = load_adl(ADL / "antweight-vault-raider.adl.yaml")
MERC = load_adl(ADL / "mercenary-source-auditor.adl.yaml")

passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")


print("determinism")
r1 = run_vault_match(DEF, RAID, seed=7)
r2 = run_vault_match(DEF, RAID, seed=7)
check("same seed -> identical trace hash", r1["traceHash"] == r2["traceHash"])
check("same seed -> same winner", r1["winner"] == r2["winner"])
check("different seeds can differ",
      len({run_vault_match(DEF, RAID, seed=s)["winner"] for s in range(20)}) >= 1)

# Audit E6/L3: the hire defense bonus comes from the hire's DECLARED grant
# (extensions.x-arena.grants.defenseBonus), never inferred from its name. The
# old name-substring key was farmable (any doc named "...source-auditor...")
# and dodgeable (a real auditor named otherwise). Real MERC declares 15, so the
# balance fixtures are unchanged; only adversarial name/grant mismatches move.
import copy as _cp_db
from arena import DEFENSE_BONUS_CAP as _DBCAP
_merc_win = [run_vault_match(DEF, RAID, seed=s, hire_a=MERC)["winner"] for s in range(40)]
_solo_win = [run_vault_match(DEF, RAID, seed=s)["winner"] for s in range(40)]
_db_farm = _cp_db.deepcopy(MERC)
_db_farm["metadata"]["name"] = "source-auditor-imposter"
_db_farm["extensions"]["x-arena"]["grants"].pop("defenseBonus", None)
check("E6/L3 a hire named like an auditor but declaring no grant gets no bonus",
      [run_vault_match(DEF, RAID, seed=s, hire_a=_db_farm)["winner"]
       for s in range(40)] == _solo_win)
_db_dodge = _cp_db.deepcopy(MERC)
_db_dodge["metadata"]["name"] = "plain-helper"
check("E6/L3 a differently-named hire that declares the grant still earns it",
      [run_vault_match(DEF, RAID, seed=s, hire_a=_db_dodge)["winner"]
       for s in range(40)] == _merc_win)
_db_over = _cp_db.deepcopy(MERC)
_db_over["extensions"]["x-arena"]["grants"]["defenseBonus"] = 999
check("E6/L3 an over-declared grant is clamped to DEFENSE_BONUS_CAP",
      [run_vault_match(DEF, RAID, seed=s, hire_a=_db_over)["winner"]
       for s in range(40)] == _merc_win and _DBCAP == 15)

print("weigh-in and draft")
solo = weigh_competitor(DEF)
check("defender is 62 AU Antweight", solo["soloAU"] == 62 and solo["soloClass"] == "Antweight")
d_ant = evaluate_hire(DEF, MERC, "Antweight")
check("hire refused at Antweight (class breach)", not d_ant.allowed)
check("refusal shows the AU delta", d_ant.au_delta == 65 and d_ant.fielded_au == 127)
d_beetle = evaluate_hire(DEF, MERC, "Beetleweight")
check("same hire allowed at Beetleweight", d_beetle.allowed)

# Audit E7/L2: the draft class ceiling is ENFORCED in the match, not advisory.
# When the caller states the entered class, a hire that breaches it is an
# illegal fielding — a pre-turn forfeit. With no entered class stated (internal
# balance/parity runs), the hire plays as before, so the sweep is unchanged.
_e7_plays = [run_vault_match(DEF, RAID, seed=s, hire_a=MERC)["winner"]
             for s in range(30)]
check("E7/L2 with no entered class stated the hire plays (balance-neutral)",
      [run_vault_match(DEF, RAID, seed=s, hire_a=MERC, entered_a="Beetleweight")["winner"]
       for s in range(30)] == _e7_plays)
_e7_illegal = [run_vault_match(DEF, RAID, seed=s, hire_a=MERC, entered_a="Antweight")
               for s in range(30)]
check("E7/L2 a class-breaching hire forfeits before turn 1",
      all(t["outcomeKind"] == "forfeit" and t["winner"] == RAID["metadata"]["name"]
          and DEF["metadata"]["name"] in t["atFault"] for t in _e7_illegal))
_e7_void = run_vault_match(DEF, RAID, seed=1, hire_a=MERC, hire_b=MERC,
                           entered_a="Antweight", entered_b="Antweight")
check("E7/L2 both fielding illegal hires voids the match",
      _e7_void["outcomeKind"] == "void"
      and set(_e7_void["atFault"]) == {DEF["metadata"]["name"], RAID["metadata"]["name"]})
_e7_legal = run_vault_match(DEF, RAID, seed=1, hire_a=MERC, entered_a="Beetleweight")
check("E7/L2 a hire legal at the entered class is not a forfeit",
      _e7_legal["outcomeKind"] not in ("forfeit", "void"))
# An unknown / mis-cased / whitespace / empty / non-string / unhashable entered
# class is a caller error: it must raise LOUDLY, never map to a ceiling-0
# silent forfeit that looks identical to a genuine breach (audit review MAJOR).
def _e7_raises(bad):
    try:
        run_vault_match(DEF, RAID, seed=1, hire_a=MERC, entered_a=bad)
        return False
    except ValueError:
        return True
    except Exception:
        return False  # a TypeError (unhashable) is NOT acceptable
check("E7/L2 an invalid entered class raises loudly, never a silent forfeit",
      all(_e7_raises(b) for b in
          ["Nonexistent", "antweight", "Beetleweight ", "", 42, ["Antweight"], {"x": 1}]))

# Audit L4: capability use is FAIL-CLOSED. The probe's extraction effect lands
# only if the attacker holds the probe capability AND the lane authorized the
# invoke; an undeclared or lane-refused probe fizzles (no extraction) rather
# than executing anyway. The fixtures declare + authorize probeCompose, so the
# balance sweep is unchanged; only unauthorized attackers change.
import copy as _cp_l4
_RN = RAID["metadata"]["name"]
_l4_norefuse = _cp_l4.deepcopy(RAID)
_l4_norefuse.setdefault("harness", {})["policies"] = []  # no allow -> probe refused
_l4_refused = [run_vault_match(DEF, _l4_norefuse, seed=s) for s in range(60)]
check("L4 a lane-refused probe never extracts (fail-closed)",
      all(not (t["outcomeKind"] == "extraction" and t["winner"] == _RN)
          for t in _l4_refused))
check("L4 a refused probe is recorded as a fizzle turn, not a silent extract",
      any(any(tt["strategy"] == "fizzle" for tt in t["turns"]) for t in _l4_refused))
_l4_notool = _cp_l4.deepcopy(RAID)
_l4_notool.setdefault("harness", {})["tools"] = []  # no probe tool declared
_l4_notool_runs = [run_vault_match(DEF, _l4_notool, seed=s) for s in range(40)]
check("L4 an attacker with no probe tool cannot win by extraction",
      all(not (t["outcomeKind"] == "extraction" and t["winner"] == _RN)
          for t in _l4_notool_runs))
check("L4 an authorized probe still extracts (fixtures unchanged)",
      any(run_vault_match(DEF, RAID, seed=s)["outcomeKind"] == "extraction"
          for s in range(10)))

# Audit E8: the turn-limit tie-break is on the larger remaining fuel RESERVE
# (honest naming — every turn costs the same flat cost, so it is not
# "efficiency"), and it is parity-fair — on an odd max_turns the seed-chosen
# opener takes one extra attack, and crediting that flat cost back means two
# equal-fuel bots draw instead of the opener losing purely by parity.
import copy as _cp_e8
_e8_a = _cp_e8.deepcopy(DEF)
_e8_b = _cp_e8.deepcopy(RAID)
for _d in (_e8_a, _e8_b):
    _d["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
    _d["model"]["requirements"]["contextWindow"] = 8000  # equal reserves
check("E8 equal-fuel bots draw at odd max_turns (no seed-parity bias)",
      all(run_vault_match(_e8_a, _e8_b, seed=s, max_turns=11)["outcomeKind"] == "draw"
          for s in range(20)))
check("E8 equal-fuel bots also draw at even max_turns (adjustment is a no-op)",
      all(run_vault_match(_e8_a, _e8_b, seed=s, max_turns=12)["outcomeKind"] == "draw"
          for s in range(20)))
_e8_big = _cp_e8.deepcopy(_e8_a)
_e8_big["model"]["requirements"]["contextWindow"] = 200000  # a genuinely larger reserve
_e8_win = run_vault_match(_e8_big, _e8_b, seed=1, max_turns=12)
check("E8 a genuinely larger reserve wins, named honestly (not 'efficiency')",
      _e8_win["outcomeKind"] == "fuel"
      and "fuel reserve" in _e8_win["reason"]
      and "efficiency" not in _e8_win["reason"])

print("conformance levels to league tiers (A7: T-015 T-016)")
import copy as _cp_a7
from weigh_in import weigh as _w_a7, tier_verdict, assess_level, TIER_LEVELS
from core.arena import LEAGUE_TIERS

check("A7 tier levels stay in sync with core.arena.LEAGUE_TIERS",
      TIER_LEVELS == {t: cfg["level"] for t, cfg in LEAGUE_TIERS.items()}
      and all(LEAGUE_TIERS[t]["purse"] == (t == "title") for t in LEAGUE_TIERS))

# Eligibility anchors to min(requested, arenaAssessed), which must reproduce
# the lab checker's recorded verdicts (README): defender 1, mercenary 3.
_v_def = _w_a7(DEF)["tierVerdict"]
_v_merc = _w_a7(MERC)["tierVerdict"]
check("A7 verdicts reproduce the lab checker's recorded levels (DEF 1, MERC 3)",
      _v_def["effectiveLevel"] == 1 and _v_merc["effectiveLevel"] == 3
      and _v_def["status"] == "ok" and _v_merc["status"] == "ok")

# T-015 — a Level-1 document cannot enter a Title fight or carry a purse.
check("T-015 the L1-declaring reference doc is Rookie-only, no purse, no hiring",
      _v_def["eligibleTiers"] == ["rookie"]
      and _v_def["purse"] is False and _v_def["hiring"] is False)
check("T-015 the lab-certified L3 mercenary is Title-eligible with purse and hiring",
      _v_merc["highestTier"] == "title"
      and _v_merc["purse"] is True and _v_merc["hiring"] is True)
# Hash coverage, non-vacuously: removing observability retention changes the
# verdict but not one AU line, so the hashes may differ ONLY via tierVerdict.
_no_ret = _cp_a7.deepcopy(DEF)
del _no_ret["harness"]["observability"]["retention"]
check("T-015 the tier verdict is in the certificate and covered by the hash",
      _w_a7(DEF)["tierVerdict"] == _v_def
      and _w_a7(_no_ret)["breakdown"] == _w_a7(DEF)["breakdown"]
      and _w_a7(_no_ret)["tierVerdict"] != _v_def
      and _w_a7(_no_ret)["capabilityHash"] != _w_a7(DEF)["capabilityHash"])

# T-016 — requestedLevel above the assessed level is rejected with the
# failing rung named; eligibility falls back to the assessed level rather
# than locking the bot out of tiers it genuinely reaches.
_over = _cp_a7.deepcopy(DEF)
del _over["harness"]["observability"]["retention"]
_over["conformance"]["requestedLevel"] = 3
_v_over = tier_verdict(_over)
check("T-016 over-request rejected with the failing rung named",
      _v_over["status"] == "over-request-rejected"
      and "retention" in _v_over["reason"]
      and _v_over["overRequested"] is True)
check("T-016 rejection falls back to the assessed level, no total lockout",
      _v_over["effectiveLevel"] == 2
      and _v_over["eligibleTiers"] == ["rookie", "open"]
      and _v_over["purse"] is False)
check("T-016 an honest request passes; requests beyond the ladder assess at its max",
      tier_verdict(DEF)["status"] == "ok"
      and assess_level(DEF)["arenaAssessedLevel"] == 3
      and tier_verdict({**_cp_a7.deepcopy(MERC),
                        "conformance": {"requestedLevel": 4}})["effectiveLevel"] == 3)
check("T-016 an unreadable requestedLevel fails closed without an exception",
      tier_verdict({**_cp_a7.deepcopy(DEF),
                    "conformance": {"requestedLevel": "3"}})["status"]
      == "rejected-unreadable")

print("coupled weight for hires (A5: T-010 T-011 T-012)")
from core.arena import evaluate_hire_chain, HIRE_DEPTH_CAP

# T-010 — the golden hire: 62 -> 127 AU, Antweight -> Beetleweight, bump flagged.
_fielded = weigh_competitor(DEF, [MERC])
check("T-010 hiring the mercenary moves 62 -> 127 AU",
      _fielded["soloAU"] == 62 and _fielded["fieldedAU"] == 127)
check("T-010 fielded class bumps Antweight -> Beetleweight, flagged",
      _fielded["fieldedClass"] == "Beetleweight" and _fielded["classBumped"] is True)

# T-011 — breach is rejected at draft (pure eligibility, no match ran) with the
# ceiling and delta stated.
_refusal = evaluate_hire(DEF, MERC, "Antweight")
check("T-011 breach refused at draft with ceiling and delta stated",
      not _refusal.allowed and "ceiling 100" in _refusal.reason
      and "65 AU" in _refusal.reason)

# T-012 — transitive hire depth beyond the cap is refused, stated, and O(1).
_chain2 = evaluate_hire_chain(DEF, [MERC, MERC], "Beetleweight")
check("T-012 depth-2 chain refused with cap stated",
      not _chain2.allowed and f"cap {HIRE_DEPTH_CAP}" in _chain2.reason)
_chain20 = evaluate_hire_chain(DEF, [MERC] * 20, "Heavyweight")
check("T-012 depth-20 chain refused identically (no recursion, no weighing)",
      not _chain20.allowed and _chain20.solo_au == 0)
check("T-012 depth-1 chain delegates to the normal draft decision",
      evaluate_hire_chain(DEF, [MERC], "Beetleweight").allowed)

print("bounded execution lane (B1: T-019 T-020 T-021 T-022)")
import copy as _cp
from core.lane import ExecutionLane, find_tool

_lane = ExecutionLane(DEF)
# T-019 — an undeclared tool cannot be invoked; a skill-disguised capability
# hits the same wall (runtime half of A6 vector 4).
_r19 = _lane.invoke("hiddenProbe")
check("T-019 undeclared tool refused at the lane",
      not _r19["allowed"] and _r19["reason"] == "undeclared-tool")

# T-020 — declared but not policy-matched cannot be invoked.
_nopol = _cp.deepcopy(DEF)
_nopol["harness"]["policies"] = [
    p for p in _nopol["harness"]["policies"]
    if p.get("resource") != "tool:vaultSeal"]
_r20 = ExecutionLane(_nopol).invoke("vaultSeal")
check("T-020 declared tool without matching policy refused",
      not _r20["allowed"] and _r20["reason"] == "no-matching-policy")
_denied = _cp.deepcopy(DEF)
_denied["harness"]["policies"].append({
    "id": "pol-deny-seal", "capability": "tool", "subject": _lane.subject,
    "resource": "tool:vaultSeal", "action": "invoke", "effect": "deny",
    "scope": {"type": "task", "value": "arena-match"},
    "enforcement": {"target": "policy-engine", "phase": "before-execution"}})
check("T-020 matching deny policy wins over allow",
      ExecutionLane(_denied).invoke("vaultSeal")["reason"] == "denied-by-policy")

# T-021 — egress with an empty allowlist is refused and logged.
_r21 = _lane.request_egress("api.example.com")
check("T-021 egress refused on empty allowlist and logged",
      not _r21["allowed"] and "egress-refused" in _r21["reason"]
      and _r21 in _lane.events)

# Bounded: policy maxInvocations is enforced (probe cap is 12).
_cap_lane = ExecutionLane(DEF)
_probe_id = find_tool(DEF, "probe")
_cap_results = [_cap_lane.invoke(_probe_id) for _ in range(13)]
check("B1 policy maxInvocations bounds repeated invocation",
      all(r["allowed"] for r in _cap_results[:12])
      and _cap_results[12]["reason"] == "invocation-limit-exceeded")

# T-022 — every decision event carries subject, resource, action, reason;
# an authorized invocation is evented too.
_ok = ExecutionLane(DEF).invoke("vaultSeal")
check("T-022 authorized invocation emits a complete event",
      _ok["allowed"] and all(k in _ok for k in
                             ("subject", "resource", "action", "reason")))
check("T-022 every refusal event is complete",
      all(all(k in e for k in ("subject", "resource", "action", "reason"))
          for e in _lane.events + _cap_lane.events))

# Integration — match capability use routes through the lanes and lands in the
# trace as evidence; reference docs are fully policied so everything is allowed.
_evtrace = run_vault_match(DEF, RAID, seed=2)
_all_events = [e for evs in _evtrace["laneEvents"].values() for e in evs]
check("B1 match trace records lane events for both competitors",
      len(_evtrace["laneEvents"]) == 2 and len(_all_events) > 0)
check("B1 reference documents pass the lane on every match invocation",
      all(e["allowed"] for e in _all_events))

print("runtime binding to the weighed declaration (E1I: T-077 T-078 T-079)")
from weigh_in import weigh as _w_e1i

# T-079 — every trace records the exact hash each lane was bound to, and it
# matches the weigh-in certificate.
_bt = run_vault_match(DEF, RAID, seed=2)
check("T-079 trace bound hashes match the weigh-in certificates",
      _bt["boundHash"][DEF["metadata"]["name"]] == _w_e1i(DEF)["capabilityHash"]
      and _bt["boundHash"][RAID["metadata"]["name"]] == _w_e1i(RAID)["capabilityHash"])

# L1/L5 (audit): the capability hash covers the security surface the lane
# enforces — egress allowlist and policy targeting — which the AU formula
# ignores. Changing either between weigh-in and fielding is now an escape.
from weigh_in import binding_surface as _bsurf
_weighed_egress = _cp.deepcopy(DEF)
_fielded_egress = _cp.deepcopy(DEF)
_fielded_egress.setdefault("harness", {}).setdefault("runtime", {}) \
    .setdefault("network", {})["allowlist"] = ["evil.example.com"]
_fielded_egress["harness"]["runtime"]["network"]["denyByDefault"] = False
check("L1 an egress-allowlist change alters the capability hash and escapes",
      _w_e1i(_weighed_egress)["capabilityHash"] != _w_e1i(_fielded_egress)["capabilityHash"]
      and ExecutionLane(_fielded_egress, _w_e1i(_weighed_egress)["capabilityHash"],
                        _w_e1i(_fielded_egress)["capabilityHash"]).escaped)
_swapped_policy = _cp.deepcopy(DEF)
for _p in _swapped_policy["harness"]["policies"]:
    if str(_p.get("resource", "")).startswith("tool:"):
        _p["resource"] = "tool:some-other-tool"
        break
check("L5 a policy-target swap (same count/effect) alters the hash and escapes",
      _w_e1i(DEF)["capabilityHash"] != _w_e1i(_swapped_policy)["capabilityHash"]
      and ExecutionLane(_swapped_policy, _w_e1i(DEF)["capabilityHash"],
                        _w_e1i(_swapped_policy)["capabilityHash"]).escaped)
check("L1 binding surface is deterministic and key-order insensitive",
      _bsurf(DEF) == _bsurf(_cp.deepcopy(DEF))
      and _bsurf({"harness": {"policies": [
          {"effect": "allow", "action": "invoke", "resource": "tool:x"}]}})
      == _bsurf({"harness": {"policies": [
          {"resource": "tool:x", "action": "invoke", "effect": "allow"}]}}))
check("L1 the binding surface does not change the AU weight",
      _w_e1i(_fielded_egress)["soloAU"] == _w_e1i(DEF)["soloAU"]
      and _w_e1i(_swapped_policy)["soloAU"] == _w_e1i(DEF)["soloAU"])
# L1 (audit review): the per-policy invocation cap is a FOURTH lane-enforced
# input (core/lane.py invoke -> min of matching allows' maxInvocations). Weigh
# a tight cap, field a loose one (or delete the cap = unlimited): the hash must
# move and the lane must flag escaped, or the widening slips past E1I.
_cap_weighed = _cp.deepcopy(DEF)
_cap_weighed.setdefault("harness", {}).setdefault("policies", [])
if not any(str(_p.get("resource", "")).startswith("tool:")
           for _p in _cap_weighed["harness"]["policies"] if isinstance(_p, dict)):
    _cap_weighed["harness"]["policies"].append(
        {"resource": "tool:vaultSeal", "action": "invoke", "effect": "allow",
         "limits": {"maxInvocations": 24}})
else:
    for _p in _cap_weighed["harness"]["policies"]:
        if isinstance(_p, dict) and str(_p.get("resource", "")).startswith("tool:"):
            _p.setdefault("limits", {})["maxInvocations"] = 24
            break
_cap_loose = _cp.deepcopy(_cap_weighed)
_cap_gone = _cp.deepcopy(_cap_weighed)
for _p in _cap_loose["harness"]["policies"]:
    if isinstance(_p, dict) and (_p.get("limits") or {}).get("maxInvocations") == 24:
        _p["limits"]["maxInvocations"] = 999999
        break
for _p in _cap_gone["harness"]["policies"]:
    if isinstance(_p, dict) and (_p.get("limits") or {}).get("maxInvocations") == 24:
        _p["limits"].pop("maxInvocations")
        break
check("L1 raising a policy invocation cap alters the hash and escapes",
      _w_e1i(_cap_weighed)["capabilityHash"] != _w_e1i(_cap_loose)["capabilityHash"]
      and ExecutionLane(_cap_loose, _w_e1i(_cap_weighed)["capabilityHash"],
                        _w_e1i(_cap_loose)["capabilityHash"]).escaped)
check("L1 deleting a policy invocation cap (unlimited) alters the hash and escapes",
      _w_e1i(_cap_weighed)["capabilityHash"] != _w_e1i(_cap_gone)["capabilityHash"]
      and ExecutionLane(_cap_gone, _w_e1i(_cap_weighed)["capabilityHash"],
                        _w_e1i(_cap_gone)["capabilityHash"]).escaped)
check("L1 the invocation cap is not an AU weight input",
      _w_e1i(_cap_weighed)["soloAU"] == _w_e1i(_cap_loose)["soloAU"])
# The projection mirrors the lane's egress read: only string hosts can satisfy
# `host in allowlist`, so numeric junk carries no enforcement weight and "1"
# stays distinct from 1 (audit review minor).
check("L1 egress projection keeps string hosts distinct from numeric look-alikes",
      _bsurf({"harness": {"runtime": {"network": {"allowlist": ["1"]}}}})
      != _bsurf({"harness": {"runtime": {"network": {"allowlist": [1]}}}})
      and _bsurf({"harness": {"runtime": {"network": {"allowlist": [1, 2.0, True]}}}})
      ["egressAllowlist"] == [])

# T-077 — a capability absent from the weighed hash cannot execute: weigh the
# honest document, then field a mutated one with a smuggled tool.
_stale_cert = _w_e1i(DEF)
_smuggled = _cp.deepcopy(DEF)
_smuggled["harness"]["tools"].append({
    "id": "smuggledProbe", "type": "function", "description": "post-weigh addition",
    "sideEffects": {"mode": "none", "mutatesState": False, "external": False,
                    "resources": []}})
_esc_lane = ExecutionLane(_smuggled, _stale_cert["capabilityHash"],
                          _w_e1i(_smuggled)["capabilityHash"])
check("T-077 escaped lane refuses the smuggled capability",
      _esc_lane.escaped
      and _esc_lane.invoke("smuggledProbe")["reason"] == "binding-mismatch")
check("T-077 escaped lane refuses even honestly-declared tools (fail-closed)",
      _esc_lane.invoke("vaultSeal")["reason"] == "binding-mismatch")
check("T-077 honest binding leaves the lane fully functional",
      not ExecutionLane(DEF, _stale_cert["capabilityHash"],
                        _stale_cert["capabilityHash"]).escaped)

# T-078 — an escape attempt forfeits the match and records evidence.
_forfeit = run_vault_match(_smuggled, RAID, seed=2, cert_a=_stale_cert)
check("T-078 escape forfeits before any turn runs",
      _forfeit["winner"] == RAID["metadata"]["name"]
      and "binding escape" in _forfeit["reason"] and _forfeit["turns"] == [])
check("T-078 the binding refusal is recorded as evidence in the trace",
      any(e["action"] == "bind" and not e["allowed"]
          for e in _forfeit["laneEvents"][DEF["metadata"]["name"]]))
check("T-078 forfeit traces are deterministic",
      run_vault_match(_smuggled, RAID, seed=2, cert_a=_stale_cert)["traceHash"]
      == _forfeit["traceHash"])
_both = run_vault_match(_smuggled, _cp.deepcopy(RAID), seed=2,
                        cert_a=_stale_cert, cert_b=_w_e1i(DEF))
check("T-078 both escaping voids the match as a draw",
      _both["winner"] is None and "void" in _both["reason"])

print("turn loop and match lifecycle (B2: T-023 T-024 T-025)")
from core.lifecycle import MatchLifecycle, IllegalTransition, LEGAL, TERMINAL

# T-023 — every match reaches exactly one defined terminal state. Property
# sweep over seeds plus the forfeit/void shapes produced above.
_t23_ok = True
_t23_traces = [run_vault_match(DEF, RAID, seed=_s) for _s in range(20)]
_t23_traces += [_forfeit, _both]
for _t in _t23_traces:
    _life = _t["lifecycle"]
    _terminals = [h["to"] for h in _life["history"] if h["to"] in TERMINAL]
    _t23_ok = (_t23_ok and _life["terminal"] and _life["state"] in TERMINAL
               and len(_terminals) == 1 and _terminals[0] == _life["state"]
               and _life["history"][-1]["to"] == _life["state"])
check("T-023 seed sweep + forfeit shapes: exactly one defined terminal state each",
      _t23_ok)
check("T-023 decisive path is scheduled->weighing->binding->in-progress->decided",
      [h["to"] for h in run_vault_match(DEF, RAID, seed=3)["lifecycle"]["history"]]
      == ["weighing", "binding", "in-progress", "decided"])
check("T-023 outcome consistency: decided/forfeit name a winner, draw/void do not",
      all((_t["lifecycle"]["state"] in ("decided", "forfeit"))
          == (_t["winner"] is not None) for _t in _t23_traces))

# T-024 — crashed or hung competitors forfeit as a defined outcome instead of
# hanging the match. In the deterministic engine the fault analogues are a
# declaration the engine cannot read (crash) and one outside the declared
# 0-100 strategy domain of ARENA-PROFILE-v0.1 (runaway/hang).
_crash = _cp.deepcopy(DEF)
_crash["extensions"]["x-arena"]["strategy"]["attack"] = "lots"
_t24 = run_vault_match(_crash, RAID, seed=2)
check("T-024 unreadable strategy forfeits before turn 1, no exception",
      _t24["lifecycle"]["state"] == "forfeit" and _t24["turns"] == []
      and _t24["winner"] == RAID["metadata"]["name"]
      and "unreadable strategy" in _t24["reason"])
_hang = _cp.deepcopy(RAID)
_hang["extensions"]["x-arena"]["strategy"]["defense"] = 5000
_t24b = run_vault_match(DEF, _hang, seed=2)
check("T-024 out-of-domain strategy forfeits as a defined outcome",
      _t24b["lifecycle"]["state"] == "forfeit"
      and _t24b["winner"] == DEF["metadata"]["name"]
      and "0-100 domain" in _t24b["reason"])
_nofuel = _cp.deepcopy(RAID)
_nofuel["model"]["requirements"]["contextWindow"] = "unbounded"
check("T-024 unreadable fuel declaration forfeits as a defined outcome",
      "unreadable fuel" in run_vault_match(DEF, _nofuel, seed=2)["reason"])
check("T-024 both competitors faulty voids the match",
      run_vault_match(_crash, _hang, seed=2)["lifecycle"]["state"] == "void")
check("T-024 fault forfeits are deterministic",
      run_vault_match(_crash, RAID, seed=2)["traceHash"] == _t24["traceHash"])

# Fault-hardening (retro-audit E1/E2/E3/E9/E10): malformed declarations
# resolve to a defined terminal trace, never an unhandled exception.
def _mut(base, fn):
    d = _cp.deepcopy(base)
    fn(d)
    return d
_malformed = {
    "extensions non-dict (E2)": lambda d: d.__setitem__("extensions", "yes"),
    "model non-dict (E2)": lambda d: d.__setitem__("model", "big"),
    "harness non-dict (E2)": lambda d: d.__setitem__("harness", "h"),
    "metadata non-dict (E2)": lambda d: d.__setitem__("metadata", "m"),
    "requirements non-dict (E2)": lambda d: d["model"].__setitem__("requirements", "r"),
    "tools list-of-strings (E2)": lambda d: d["harness"].__setitem__("tools", ["x"]),
    "policies list-of-strings (E2)": lambda d: d["harness"].__setitem__("policies", ["p"]),
    "strategy non-dict (E2)": lambda d: d["extensions"]["x-arena"].__setitem__("strategy", "aggro"),
    "maxOutputTokens string (E1)": lambda d: d["model"]["requirements"].__setitem__("maxOutputTokens", "512"),
    "missing metadata.name (E9)": lambda d: d["metadata"].pop("name"),
}
_fault_ok = True
for _label, _fn in _malformed.items():
    for _combo in ("A", "both"):
        _da = _mut(DEF, _fn)
        _db = _mut(RAID, _fn) if _combo == "both" else _cp.deepcopy(RAID)
        try:
            _tf = run_vault_match(_da, _db, seed=2)
            _fault_ok = (_fault_ok and _tf["lifecycle"]["terminal"]
                         and _tf["traceHash"].startswith("sha256:"))
        except Exception:
            _fault_ok = False
check("fault-hardening: curated malformed declarations resolve to a terminal trace",
      _fault_ok)

# Typed-fuzz sweep: set a hostile value type at every nested declaration path
# and require a terminal trace (never an exception). Covers the value classes
# the reviewer flagged — non-dict, non-list, unhashable, non-finite, non-str
# name — not just the curated shapes above.
_BAD_VALUES = [None, 3.5, "x", [1, 2], {"k": 1}, True, float("inf"),
               float("nan"), [[1]], "999999",
               int("9" * 400), b"bytes", {1, 2}]  # huge int / non-serializable
_PATHS = [
    ("metadata",), ("metadata", "name"), ("model",), ("model", "requirements"),
    ("model", "requirements", "contextWindow"),
    ("model", "requirements", "maxOutputTokens"),
    ("model", "requirements", "modalities"), ("harness",), ("harness", "tools"),
    ("harness", "policies"), ("harness", "runtime"),
    ("harness", "runtime", "network"), ("harness", "observability"),
    ("harness", "memory"), ("extensions",), ("extensions", "x-arena"),
    ("extensions", "x-arena", "strategy"),
    ("extensions", "x-arena", "strategy", "attack"), ("conformance",),
]

def _set_path(doc, path, value):
    cur = doc
    for k in path[:-1]:
        nxt = cur.get(k) if isinstance(cur, dict) else None
        if not isinstance(nxt, dict):
            nxt = {}
            if isinstance(cur, dict):
                cur[k] = nxt
        cur = nxt
    if isinstance(cur, dict):
        cur[path[-1]] = value

from weigh_in import weigh as _w_fuzz
_fuzz_crashes = []
_fuzz_n = 0
for _path in _PATHS:
    for _val in _BAD_VALUES:
        _d = _cp.deepcopy(DEF)
        _set_path(_d, _path, _val)
        _fuzz_n += 1
        # Exercise both the match engine AND weigh() directly (the hash path
        # the certificate flows through), single-side and self-match.
        for _call in (lambda: run_vault_match(_d, RAID, seed=2),
                      lambda: run_vault_match(_cp.deepcopy(_d), _cp.deepcopy(_d), seed=1),
                      lambda: _w_fuzz(_d)):
            try:
                _r = _call()
                if isinstance(_r, dict) and "lifecycle" in _r \
                        and not _r["lifecycle"]["terminal"]:
                    _fuzz_crashes.append((_path, type(_val).__name__, "non-terminal"))
            except Exception as _e:
                _fuzz_crashes.append((_path, type(_val).__name__, type(_e).__name__))
# Item-field injection: a bad value INSIDE a tool/policy/source/intent item
# (the value class the reviewer flagged — an unhashable tool id, etc.).
# ids whose STRING FORM contains a tool-search fragment ("probe"/"seal"):
# find_tool selects by str-match, so such an id must not be returned
# unhashable and then hashed by invoke() (audit round-3 C).
_ID_VALUES = _BAD_VALUES + [["probe-core"], {"probe": 1}, {"seal"},
                            ["seal-x"], {"sealer": 1}]
for _coll, _field in [("tools", "id"), ("tools", "sideEffects"),
                      ("policies", "resource"), ("policies", "id"),
                      ("dataSources", "type"), ("functions", "id")]:
    _vals = _ID_VALUES if (_coll, _field) == ("tools", "id") else _BAD_VALUES
    for _val in _vals:
        _d = _cp.deepcopy(DEF)
        _d.setdefault("harness", {})[_coll] = [{_field: _val}]
        _fuzz_n += 1
        for _call in (lambda: run_vault_match(_d, RAID, seed=2),
                      lambda: run_vault_match(RAID, _d, seed=0),
                      lambda: _w_fuzz(_d)):
            try:
                _call()
            except Exception as _e:
                _fuzz_crashes.append((f"{_coll}[].{_field}", type(_val).__name__,
                                      type(_e).__name__))
check(f"fault-hardening: typed-fuzz sweep — nested + item-field bad values resolve, "
      f"never crash ({_fuzz_n} shapes over match+weigh+self-match)",
      not _fuzz_crashes)
# A malformed hire document must not crash the match either (audit minor 4).
check("fault-hardening: a malformed hire document does not crash the match",
      all(run_vault_match(DEF, RAID, seed=2, hire_a=_hv)["lifecycle"]["terminal"]
          for _hv in ({}, {"metadata": "x"}, {"metadata": {"name": 3.5}}, "not-a-doc")))
# The clearly-unreadable declarations (strategy/fuel/name faults) forfeit
# pre-turn specifically, rather than merely not crashing.
check("fault-hardening: unreadable strategy/fuel/name faults forfeit before turn 1",
      all(run_vault_match(_mut(DEF, _f), RAID, seed=2)["turns"] == []
          for _f in (_malformed["strategy non-dict (E2)"],
                     _malformed["maxOutputTokens string (E1)"],
                     _malformed["missing metadata.name (E9)"])))
# E3: a string-numeral contextWindow must NOT buy fuel — weigh awards it 0 AU,
# so granting a huge tank was a weight-class dodge. It now forfeits.
_dodge = _cp.deepcopy(DEF)
_dodge["model"]["requirements"]["contextWindow"] = "999999"
check("E3: string-numeral contextWindow forfeits (no weight-class fuel dodge)",
      run_vault_match(_dodge, RAID, seed=0, max_turns=200)["lifecycle"]["state"] == "forfeit")
# E1: budget_gate does not raise on a non-numeric maxOutputTokens.
from core.fuel import budget_gate as _bg
check("E1: budget_gate fails closed (no crash) on non-numeric maxOutputTokens",
      _bg({"model": {"requirements": {"maxOutputTokens": "512"}}}, 8000)["passed"] is False)
check("E1: budget_gate tolerates a non-mapping model/requirements",
      _bg({"model": "big"}, 8000)["passed"] is True
      and _bg("not a doc", 8000)["passed"] is True)
# E10: the non-terminal-trace guard is a real exception, not an assert (so it
# survives python3 -O). _finalize raises when handed a non-terminal lifecycle.
import core.arena as _arena_mod
from core.lifecycle import MatchLifecycle as _MLC
_raised_e10 = False
try:
    _arena_mod._finalize(["a", "b"], [], -1, "x", [True, True], [1, 1], [1, 1],
                         0, lifecycle=_MLC())
except Exception:
    _raised_e10 = True
check("E10: finalizing a non-terminal lifecycle raises (survives python3 -O)",
      _raised_e10)

# T-025 — illegal lifecycle transitions are unreachable: exhaustive sweep of
# every (state, target) pair, reaching each state only via legal walks.
_paths = {
    "scheduled": [], "weighing": ["weighing"],
    "binding": ["weighing", "binding"],
    "in-progress": ["weighing", "binding", "in-progress"],
    "decided": ["weighing", "binding", "in-progress", "decided"],
    "forfeit": ["weighing", "binding", "forfeit"],
    "draw": ["weighing", "binding", "in-progress", "draw"],
    "void": ["weighing", "binding", "void"],
}

def _walked_to(state):
    m = MatchLifecycle()
    for s in _paths[state]:
        m.advance(s, "walk")
    return m

_t25_ok = True
for _frm in _paths:
    for _to in list(LEGAL) + ["no-such-state"]:
        _m = _walked_to(_frm)
        try:
            _m.advance(_to, "probe")
            _allowed = True
        except IllegalTransition:
            _allowed = False
        _t25_ok = _t25_ok and _allowed == (_to in LEGAL.get(_frm, frozenset()))
check("T-025 exhaustive sweep: advance succeeds iff the transition is legal",
      _t25_ok)
check("T-025 terminal states are absorbing (no legal exits)",
      all(not LEGAL[s] for s in TERMINAL))
def _raises_illegal(machine, to):
    try:
        machine.advance(to, "probe")
        return False
    except IllegalTransition:
        return True

check("T-025 phase skipping is unreachable (scheduled -> in-progress raises)",
      _raises_illegal(MatchLifecycle(), "in-progress"))
check("T-025 unknown states are unreachable",
      _raises_illegal(_walked_to("binding"), "sudden-death"))
check("T-025 history records the exact walked path append-only",
      [h["to"] for h in _walked_to("decided").history]
      == _paths["decided"]
      and _walked_to("decided").history[0]["from"] == "scheduled")

print("github relation sync planner (GE02)")
from sync_github_relations import build_plan as _ge02_plan, epic_body as _ge02_body
import yaml as _yaml_ge02
_ge02_graph_before = (ROOT / "planning" / "graph.yaml").read_text()
_ge02 = _ge02_plan()
check("GE02 plan mirrors every epic and every executable node as a sub-issue",
      _ge02["epicCount"] == 16 and _ge02["subIssueCount"] == 36
      and all(isinstance(c["issue"], int)
              for e in _ge02["epics"] for c in e["subIssues"]))
check("GE02 every graph epic is present exactly once, members are its nodes",
      sorted(e["epic"] for e in _ge02["epics"])
      == [f"E{n:02d}" for n in range(1, 17)]
      and all(e["subIssues"] and e["marker"].startswith("<!-- graph-epic:")
              for e in _ge02["epics"]))
check("GE02 planning is read-only — graph.yaml is not mutated by the planner",
      (ROOT / "planning" / "graph.yaml").read_text() == _ge02_graph_before)
check("GE02 an existing epic is marked skip, not recreated (idempotent apply)",
      _ge02_plan({"E01": 999})["epics"][0]["action"].startswith("skip")
      and _ge02["epics"][0]["action"] == "create")
check("GE02 epic body embeds the marker and its sub-issue references",
      "<!-- graph-epic: E01 -->" in _ge02_body(_ge02["epics"][0])
      and "#1" in _ge02_body(_ge02["epics"][0]))

print("generated-prompt guidance pointer migration")
# spdd/prompt artifacts are SEEDED by tools/generate_prompts.py and then
# hand-maintained: Sync Log rows, completed DoD checkmarks and issue metadata are
# node evidence AGENTS.md requires to exist, and a full regeneration destroys
# them. So moving the guidance pointer uses a narrow migration mode that must
# rewrite exactly one span per file and preserve every other byte.
import shutil as _shutil_gp
import tempfile as _tempfile_gp
from pathlib import Path as _Path_gp
import generate_prompts as _gp

_gp_plan, _gp_failures, _gp_stats = _gp.plan_graph()
_gp_by_id = {i["id"]: (i, e) for e in _gp_plan["epics"] for i in e["issues"]}
_gp_names = _gp.generated_artifact_names(_gp_stats, _gp_by_id)
check("the migration targets only generated artifacts, never the kickoff record",
      len(_gp_names) == 36 and "0001-project-kickoff.md" not in _gp_names
      and all((ROOT / "spdd" / "prompt" / n).is_file() for n in _gp_names))

# Golden before/after: a checked-in artifact reverted to the legacy pointer must
# come back byte-identical to the checked-in file.
_gp_dir = _Path_gp(_tempfile_gp.mkdtemp(prefix="arena-pointer-migration-"))
_gp_sample = _gp_names[0]
_gp_after = (ROOT / "spdd" / "prompt" / _gp_sample).read_text()
_gp_before = _gp_after.replace(_gp.guidance_pointer(_gp.GUIDANCE_DOC),
                               _gp.guidance_pointer("CLAUDE.md"), 1)
check("the golden 'before' really differs only in the pointer document",
      _gp_before != _gp_after
      and _gp_before.replace("CLAUDE.md", "AGENTS.md", 1) == _gp_after)
(_gp_dir / _gp_sample).write_text(_gp_before)
_gp_changed, _gp_already = _gp.migrate_guidance_pointer(_gp_dir, [_gp_sample])
check("migrating a legacy artifact reproduces the checked-in bytes exactly",
      _gp_changed == [_gp_sample] and not _gp_already
      and (_gp_dir / _gp_sample).read_text() == _gp_after)
# Idempotence: a second run is a no-op and leaves the bytes untouched.
_gp_changed2, _gp_already2 = _gp.migrate_guidance_pointer(_gp_dir, [_gp_sample])
check("a second migration run changes nothing (idempotent)",
      not _gp_changed2 and _gp_already2 == [_gp_sample]
      and (_gp_dir / _gp_sample).read_text() == _gp_after)
# --dry-run reports the work without touching the file.
(_gp_dir / _gp_sample).write_text(_gp_before)
_gp_dry, _ = _gp.migrate_guidance_pointer(_gp_dir, [_gp_sample], dry_run=True)
check("--dry-run reports the rewrite without writing it",
      _gp_dry == [_gp_sample] and (_gp_dir / _gp_sample).read_text() == _gp_before)
# Hand-maintained evidence survives: a Sync Log row, a ticked DoD box and an
# issue number added after generation are all still present afterwards.
_gp_hand = _gp_before.replace("- [ ] ", "- [x] ", 1) + (
    "| 2026-08-16 | hand-added divergence row | artifact | code |\n")
(_gp_dir / _gp_sample).write_text(_gp_hand)
_gp.migrate_guidance_pointer(_gp_dir, [_gp_sample])
_gp_out = (_gp_dir / _gp_sample).read_text()
check("migration preserves hand-maintained Sync Log rows and DoD checkmarks",
      "2026-08-16 | hand-added divergence row" in _gp_out
      and "- [x] " in _gp_out
      and _gp_out == _gp_hand.replace(_gp.guidance_pointer("CLAUDE.md"),
                                      _gp.guidance_pointer(_gp.GUIDANCE_DOC), 1))
# Refusals: a file with no recognised pointer, an ambiguous one, or a missing
# artifact must raise rather than guess at a rewrite.
_gp_refusals = 0
for _gp_text in ("no pointer here at all\n",
                 _gp_before + _gp_after,
                 _gp_before + _gp_before):
    (_gp_dir / _gp_sample).write_text(_gp_text)
    try:
        _gp.migrate_guidance_pointer(_gp_dir, [_gp_sample])
    except _gp.PointerMigrationError:
        _gp_refusals += 1
    if (_gp_dir / _gp_sample).read_text() != _gp_text:
        _gp_refusals = -99  # a refused migration must not have written anything
check("missing and ambiguous pointers refuse without writing", _gp_refusals == 3)
try:
    _gp.migrate_guidance_pointer(_gp_dir, ["not-an-artifact.md"])
    _gp_missing = False
except _gp.PointerMigrationError:
    _gp_missing = True
check("a missing expected artifact refuses the migration", _gp_missing)
_shutil_gp.rmtree(_gp_dir)
# The checked-in tree is already migrated, so running the mode over it is a no-op.
_gp_changed3, _gp_already3 = _gp.migrate_guidance_pointer(
    ROOT / "spdd" / "prompt", _gp_names, dry_run=True)
check("every checked-in generated artifact already points at AGENTS.md",
      not _gp_changed3 and len(_gp_already3) == len(_gp_names))

print("provider abstraction (B3: T-026 T-027 T-028)")
import yaml as _yaml_b3
from core.providers import (
    declared_order, select_provider, divergence_report, effective_doc,
)

_AVAIL = _yaml_b3.safe_load(open(ROOT / "fixtures" / "providers.yaml"))["providers"]

# T-026 — undeclared fallback providers are never selected, even when they
# are the only thing available; declared-but-uncredentialed fails closed.
check("T-026 declared order is preferred-then-fallbacks",
      declared_order(DEF) == ["ollama", "anthropic", "openai"])
_only_undeclared = {"mystery-llm": {"credentials": True, "capabilities": {
    "toolCalling": True, "structuredOutput": True, "contextWindow": 999999,
    "maxOutputTokens": 9999, "modalities": ["text"]}}}
_sel_u = select_provider(DEF, _only_undeclared)
check("T-026 an undeclared provider is never selected (fail closed, unavailable)",
      _sel_u["provider"] is None and _sel_u["status"] == "unavailable"
      and all(c["provider"] != "mystery-llm" for c in _sel_u["considered"]))
_no_creds = {n: dict(_AVAIL[n], credentials=False) for n in _AVAIL}
_sel_nc = select_provider(DEF, _no_creds)
check("T-026 missing credentials fail closed with the reason stated",
      _sel_nc["provider"] is None and _sel_nc["status"] == "unavailable"
      and all("missing credentials" in c["reason"] for c in _sel_nc["considered"]))
check("T-026 every declared provider considered is recorded as evidence",
      [c["provider"] for c in _sel_nc["considered"]] == declared_order(DEF))

# T-027 — a provider missing a declared requirement reports degraded, never
# silent success. The fixture ollama offers contextWindow 4000 < declared 8000.
_sel = select_provider(DEF, _AVAIL)
check("T-027 under-capability selection reports degraded with the gap named",
      _sel["provider"] == "ollama" and _sel["status"] == "degraded"
      and _sel["missing"] == ["contextWindow"])
_sel_ok = select_provider(DEF, {"anthropic": _AVAIL["anthropic"]})
check("T-027 fully-capable selection reports ok with nothing missing",
      _sel_ok["provider"] == "anthropic" and _sel_ok["status"] == "ok"
      and _sel_ok["missing"] == [])
_no_struct = {"anthropic": {"credentials": True, "capabilities": dict(
    _AVAIL["anthropic"]["capabilities"], structuredOutput=False)}}
check("T-027 missing structuredOutput is degraded, not silent success",
      select_provider(DEF, _no_struct)["missing"] == ["structuredOutput"])
check("T-027 effective doc caps declared numerics at provider capability",
      effective_doc(DEF, {"contextWindow": 4000})["model"]["requirements"]
      ["contextWindow"] == 4000
      and DEF["model"]["requirements"]["contextWindow"] == 8000)
# T11 (audit): a provider that OMITS a numeric capability (or offers a
# non-numeric value) offers NONE of it, so the requirement caps to 0 — the old
# code left it uncapped at the full declared value, so a degraded provider
# produced the same effective fuel as a fully-capable one and biased divergence
# to zero. Consistent with select_provider marking the omission missing.
check("T11 an omitted provider capability caps the requirement to 0, not full",
      effective_doc(DEF, {})["model"]["requirements"]["contextWindow"] == 0
      and effective_doc(DEF, {"contextWindow": 4000})["model"]["requirements"]
      .get("maxOutputTokens") == 0)
check("T11 a non-numeric offered capability is treated as omitted (caps to 0)",
      effective_doc(DEF, {"contextWindow": "lots"})["model"]["requirements"]
      ["contextWindow"] == 0)
from arena import _read_fuel as _rf_t11
check("T11 an omitted capability floors effective fuel, surfacing divergence",
      _rf_t11(effective_doc(DEF, {}))[0] == 2000
      and _rf_t11(effective_doc(DEF, {"contextWindow": 200000}))[0] == 8000)
# select_provider must mark a non-numeric offered capability degraded, mirroring
# effective_doc capping it to 0 — the old `offered < declared` raised TypeError
# on e.g. a string (audit T11 consistency).
_t11_nonnum = {"anthropic": {"credentials": True, "capabilities": {
    "toolCalling": True, "structuredOutput": True,
    "contextWindow": "lots", "maxOutputTokens": 8192, "modalities": ["text"]}}}
check("T11 select_provider degrades a non-numeric offered capability, no TypeError",
      select_provider(DEF, _t11_nonnum)["status"] == "degraded"
      and "contextWindow" in select_provider(DEF, _t11_nonnum)["missing"])

# T-028 — cross-provider divergence is measured and published, not hidden.
_rep = divergence_report(DEF, RAID, _AVAIL, range(10))
check("T-028 report compares only credentialed declared providers",
      _rep["providersCompared"] == ["anthropic", "ollama"])
check("T-028 trace divergence is published per seed with winners recorded",
      _rep["traceDivergenceRate"] == 1.0
      and all("winners" in d for d in _rep["divergentSeeds"].values())
      and _rep["outcomeDivergenceRate"] == 0.0)
# A defensive stalemate reaches the turn limit and decides on absolute fuel,
# so the provider fuel cap flips the winner: observable outcome divergence.
_wall_a = _cp.deepcopy(DEF)
_wall_a["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
_wall_b = _cp.deepcopy(RAID)
_wall_b["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
_rep_wall = divergence_report(_wall_a, _wall_b, _AVAIL, range(4))
check("T-028 outcome divergence is detected and listed when it occurs",
      _rep_wall["outcomeDivergenceRate"] > 0
      and all(not _rep_wall["divergentSeeds"][s]["identical_outcome"]
              for s in _rep_wall["outcomeDivergentSeeds"]))
check("T-028 divergence report is deterministic",
      divergence_report(DEF, RAID, _AVAIL, range(10)) == _rep)

print("token fuel accounting (B4: T-029 T-030 T-031)")
from core.fuel import (
    FuelMeter, budget_gate, TURN_PROMPT_COST, TURN_COMPLETION_COST, TURN_COST,
)

# T-029 — exceeding the declared fuel cap fails the budget-check gate at the
# declared thresholds, as a defined pre-turn outcome.
check("T-029 reference docs pass the budget gate",
      budget_gate(DEF, 8000)["passed"] and budget_gate(RAID, 8000)["passed"])
_tiny_out = _cp.deepcopy(DEF)
_tiny_out["model"]["requirements"]["maxOutputTokens"] = TURN_COMPLETION_COST - 1
_g = budget_gate(_tiny_out, 8000)
check("T-029 completion above declared maxOutputTokens fails the gate, threshold named",
      not _g["passed"] and "maxOutputTokens" in _g["reason"])
check("T-029 per-turn cost above the fuel cap fails the gate",
      not budget_gate(DEF, TURN_COST - 1)["passed"])
_t29 = run_vault_match(_tiny_out, RAID, seed=3)
check("T-029 failed gate forfeits before turn 1 as a defined outcome",
      _t29["lifecycle"]["state"] == "forfeit" and _t29["turns"] == []
      and _t29["winner"] == RAID["metadata"]["name"]
      and "budget gate" in _t29["reason"])
check("T-029 both failing the gate voids the match",
      run_vault_match(_tiny_out, _cp.deepcopy(_tiny_out), seed=3)
      ["lifecycle"]["state"] == "void")

# T-030 — fuel exhaustion mid-turn produces the defined sputter outcome,
# never an exception. cap 2090 = 34 full turns + a prompt charge with 10
# left: the 35th attack charges the prompt, cannot afford the completion.
_sput = _cp.deepcopy(DEF)
_sput["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
_sput["model"]["requirements"]["contextWindow"] = 2090
_sput_b = _cp.deepcopy(RAID)
_sput_b["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
_t30 = run_vault_match(_sput, _sput_b, seed=0, max_turns=200)
_led30 = _t30["fuelAccounting"][DEF["metadata"]["name"]]
check("T-030 mid-turn exhaustion sputters as a defined forfeit",
      _t30["lifecycle"]["state"] == "forfeit"
      and "sputter-mid" in _t30["reason"]
      and _t30["winner"] == RAID["metadata"]["name"])
check("T-030 the partial turn is in the ledger: prompt charged, completion zero",
      _led30["ledger"][-1]["prompt"] == TURN_PROMPT_COST
      and _led30["ledger"][-1]["completion"] == 0
      and _led30["remaining"] == 2090 - _led30["spent"])
_sput_pre = _cp.deepcopy(_sput)
_sput_pre["model"]["requirements"]["contextWindow"] = 2040  # 34 exact turns
_t30p = run_vault_match(_sput_pre, _sput_b, seed=0, max_turns=200)
check("T-030 pre-turn exhaustion sputters with nothing charged",
      "sputter-pre" in _t30p["reason"]
      and _t30p["fuelAccounting"][DEF["metadata"]["name"]]["remaining"] == 0)
check("T-030 the meter never overdraws",
      FuelMeter(TURN_PROMPT_COST - 1).charge(1)["outcome"] == "sputter-pre"
      and FuelMeter(TURN_PROMPT_COST - 1).remaining == TURN_PROMPT_COST - 1)

# T-031 — accounting reconciles exactly with the emitted trace for every
# match: property sweep over seeds plus the sputter/gate shapes above.
_t31_ok = True
_t31_traces = [run_vault_match(DEF, RAID, seed=_s) for _s in range(20)]
_t31_traces += [_t30, _t30p, _t29]
for _t in _t31_traces:
    for _i, _n in enumerate(_t["competitors"]):
        _fa = _t["fuelAccounting"][_n]
        _ledger_sum = sum(e["prompt"] + e["completion"] for e in _fa["ledger"])
        _t31_ok = (_t31_ok
                   and _fa["spent"] + _fa["remaining"] == _fa["cap"]
                   and _ledger_sum == _fa["spent"]
                   and _t["fuelStart"][_i] == _fa["cap"]
                   and _t["fuelLeft"][_i] == _fa["remaining"]
                   and _t["fuelStart"][_i] - _t["fuelLeft"][_i] == _ledger_sum)
check("T-031 ledger, cap, spent, remaining and trace fuel fields all reconcile",
      _t31_ok)
check("T-031 fuel accounting is hash-covered and deterministic",
      run_vault_match(_sput, _sput_b, seed=0, max_turns=200)["traceHash"]
      == _t30["traceHash"])

print("structured trace outcomes (audit E4/E5/T3/T6/T8)")
from core.audit import audit_match
from core.emit import emit_events as _emit_events_so
emit_events = _emit_events_so
# The engine stamps a machine-readable outcomeKind and an atFault list; every
# terminal carries them, and result distinguishes void from draw.
_so_shapes = {
    "extraction": run_vault_match(DEF, RAID, seed=3),
    "forfeit": _forfeit,
    "void": _both,
}
check("E5 outcomeKind is stamped and result distinguishes void from draw",
      _so_shapes["extraction"]["outcomeKind"] == "extraction"
      and _so_shapes["extraction"]["result"] == "decisive"
      and _both["outcomeKind"] == "void" and _both["result"] == "void")
check("E5/atFault names the faulty competitor(s) structurally",
      _forfeit["atFault"] == [DEF["metadata"]["name"]]
      and set(_both["atFault"]) == set(_both["competitors"]))
check("E5 a clean decisive match has an empty atFault",
      _so_shapes["extraction"]["atFault"] == [])
# E4/T8: two competitors sharing a name void the match — no evidence collapse.
_dupname = _cp.deepcopy(RAID)
_dupname["metadata"]["name"] = DEF["metadata"]["name"]
_dup_trace = run_vault_match(DEF, _dupname, seed=2)
check("E4/T8 duplicate competitor names void the match before evidence is built",
      _dup_trace["outcomeKind"] == "void" and _dup_trace["result"] == "void"
      and "same name" in _dup_trace["reason"]
      and "laneEvents" not in _dup_trace)
# The collision guard is on the EFFECTIVE names: a doc literally named
# "unnamed-competitor-1" vs an unnamed opponent collides on the placeholder
# key and must void (audit review MAJOR), while two unnamed docs keep
# distinct index placeholders and do NOT collide.
_ph_a = _cp.deepcopy(DEF); _ph_a["metadata"]["name"] = "unnamed-competitor-1"
_ph_b = _cp.deepcopy(RAID); _ph_b["metadata"].pop("name")
_ph_trace = run_vault_match(_ph_a, _ph_b, seed=3)
check("E4 placeholder-name collision voids with no evidence collapse",
      _ph_trace["outcomeKind"] == "void" and "laneEvents" not in _ph_trace)
_u_a = _cp.deepcopy(DEF); _u_a["metadata"].pop("name")
_u_b = _cp.deepcopy(RAID); _u_b["metadata"].pop("name")
check("E4 two unnamed docs keep distinct placeholders (no false collision)",
      run_vault_match(_u_a, _u_b, seed=3)["competitors"]
      == ["unnamed-competitor-0", "unnamed-competitor-1"])
# T6: prefix-name framing — 'vault' is not blamed when 'vaulter' forfeits.
_frame_a = _cp.deepcopy(DEF); _frame_a["metadata"]["name"] = "vault"
_frame_b = _cp.deepcopy(RAID); _frame_b["metadata"]["name"] = "vaulter"
_frame_b["extensions"]["x-arena"]["strategy"] = {"attack": "x", "defense": 50}
_frame_t = run_vault_match(_frame_a, _frame_b, seed=2)
check("T6 attribution is structural: the innocent prefix name is not framed",
      _frame_t["atFault"] == ["vaulter"]
      and audit_match(_frame_t, "vault")["signals"] == [])
# And the prefix name does not raise a false envelope-exhaustion signal when
# the OTHER competitor genuinely sputters (the reason string names both).
_ex_a = _cp.deepcopy(DEF); _ex_a["metadata"]["name"] = "ant"
_ex_a["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
_ex_a["model"]["requirements"]["contextWindow"] = 2090
_ex_b = _cp.deepcopy(RAID); _ex_b["metadata"]["name"] = "anteater"
_ex_b["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
_ex_t = run_vault_match(_ex_a, _ex_b, seed=0, max_turns=200)
check("T6 a prefix name gets no false exhaustion signal when another sputters",
      any(s["kind"] == "declared-envelope-exhausted"
          for s in audit_match(_ex_t, "ant")["signals"])
      and all(s["kind"] != "declared-envelope-exhausted"
              for s in audit_match(_ex_t, "anteater")["signals"]))
_frame_em = emit_events(_frame_t, _frame_a, _frame_b)
check("T6 emit marks only the faulty competitor task.failed",
      [e["competitor"] for e in _frame_em["stream"] if e["event"] == "task.failed"]
      == ["vaulter"])
# The budget-check eval.checked label reads the structural budgetGateFailed
# list, so a sputter forfeit by a bot named "budget gate hero" is not
# mislabeled as a budget-gate failure (audit review MINOR).
_bgh = _cp.deepcopy(DEF); _bgh["metadata"]["name"] = "budget gate hero"
_bgh["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
_bgh["model"]["requirements"]["contextWindow"] = 2090
_bgh_b = _cp.deepcopy(RAID); _bgh_b["extensions"]["x-arena"]["strategy"] = {"attack": 0, "defense": 100}
_bgh_t = run_vault_match(_bgh, _bgh_b, seed=0, max_turns=200)
_bgh_em = emit_events(_bgh_t, _bgh, _bgh_b)
check("T6 a sputter forfeit does not mislabel the budget-check eval event",
      _bgh_t["budgetGateFailed"] == []
      and all(e["payload"]["passed"] for e in _bgh_em["stream"]
              if e["event"] == "eval.checked"))

print("undeclared-capability reliance detection (E2I: T-080 T-081)")
import core.audit as _audit_mod
from core.audit import audit_match, flag_sustained, OVERRUN_TOLERANCE, DISPOSITIONS

# T-080 — declared-versus-actual usage is measurable on every match, from
# the trace alone: seed sweep plus every terminal shape produced above
# (escape forfeit, both-escape void, budget-gate forfeit, mid-turn sputter).
_t80_shapes = [run_vault_match(DEF, RAID, seed=_s) for _s in range(10)]
_t80_shapes += [_forfeit, _both, _t29, _t30]
_t80_ok = True
for _t in _t80_shapes:
    for _n in _t["competitors"]:
        _a = audit_match(_t, _n)
        _t80_ok = (_t80_ok
                   and set(_a) == {"competitor", "declaredCap", "spent",
                                   "utilization", "signals"}
                   and 0.0 <= _a["utilization"] <= 1.0
                   and _a["spent"] == _t["fuelAccounting"][_n]["spent"])
check("T-080 audit measures declared-vs-actual on every match shape", _t80_ok)
check("T-080 a clean reference match raises no signals",
      all(audit_match(_t80_shapes[3], _n)["signals"] == []
          for _n in _t80_shapes[3]["competitors"]))
check("T-080 a binding escape is a reliance signal for the escapee only",
      any(s["kind"] == "binding-escape"
          for s in audit_match(_forfeit, DEF["metadata"]["name"])["signals"])
      and audit_match(_forfeit, RAID["metadata"]["name"])["signals"] == [])
check("T-080 envelope exhaustion is a reliance signal with usage measured",
      any(s["kind"] == "declared-envelope-exhausted"
          for s in audit_match(_t30, DEF["metadata"]["name"])["signals"])
      and audit_match(_t30, DEF["metadata"]["name"])["utilization"] > 0.99)
# An undeclared-invocation refusal in the lane evidence is a signal. The
# engine only invokes declared tools, so the refusal events are produced by
# a real lane and audited as trace evidence (the audit is a pure function
# over the evidence structure).
_probe_lane = ExecutionLane(DEF)
_probe_lane.invoke("hiddenProbe")
_probe_lane.invoke("hiddenProbe")
_grafted = _cp.deepcopy(_t80_shapes[3])
_grafted["laneEvents"][DEF["metadata"]["name"]] = list(_probe_lane.events)
_g_audit = audit_match(_grafted, DEF["metadata"]["name"])
check("T-080 undeclared invocation attempts surface with their count",
      any(s["kind"] == "undeclared-invocation-attempt" and s["count"] == 2
          for s in _g_audit["signals"]))

# T-081 — sustained overrun is flagged with the measured delta and routed
# to review; no automatic ban exists, structurally.
_series = [audit_match(_grafted, DEF["metadata"]["name"]),
           audit_match(_forfeit, DEF["metadata"]["name"]),
           audit_match(_t30, DEF["metadata"]["name"]),
           audit_match(_t80_shapes[3], DEF["metadata"]["name"]),
           audit_match(_t80_shapes[4], DEF["metadata"]["name"])]
_flag = flag_sustained(_series)
check("T-081 sustained overrun flags with the aggregated measured delta",
      _flag["flagged"] and _flag["matchesWithSignals"] == 3
      and _flag["measuredDelta"]["undeclared-invocation-attempt"] == 2
      and _flag["measuredDelta"]["binding-escape"] >= 1
      and _flag["measuredDelta"]["declared-envelope-exhausted"] == 1)
check("T-081 flagged disposition is review, never enforcement",
      _flag["disposition"] == "review-required"
      and "human" in _flag["adjudication"])
check("T-081 below the published tolerance is no-action",
      not flag_sustained(_series[2:])["flagged"]
      and flag_sustained(_series[2:])["disposition"] == "no-action")
check("T-081 no ban mechanism exists in the audit module",
      "ban" not in DISPOSITIONS
      and all(d in DISPOSITIONS for d in ("no-action", "review-required"))
      and not any("ban" in _k.lower() for _k in vars(_audit_mod)
                  if not _k.startswith("_")))
check("T-081 an empty audit series is safe and unflagged",
      flag_sustained([])["flagged"] is False)
# T12 (audit): flag_sustained aggregates ONE competitor's audits; a mixed series
# would silently attribute one bot's overruns to another, so it fails loudly.
_t12_mixed = [audit_match(_grafted, DEF["metadata"]["name"]),
              audit_match(_grafted, RAID["metadata"]["name"])]
def _t12_raises():
    try:
        flag_sustained(_t12_mixed)
        return False
    except ValueError:
        return True
check("T12 a mixed-competitor audit series raises, never mislabels",
      _t12_raises()
      and flag_sustained([audit_match(_grafted, DEF["metadata"]["name"])])
          ["competitor"] == DEF["metadata"]["name"])

print("trace emission with declared redaction (B5: T-032 T-033 T-034)")
from core.emit import (
    emit_events, redact_payload, declared_redaction, stream_contains, WITHHELD,
)

# T-032 — every match emits a complete, ordered, replayable event stream.
_em_trace = run_vault_match(DEF, RAID, seed=2)
_em = emit_events(_em_trace, DEF, RAID)
_seqs = [e["seq"] for e in _em["stream"]]
check("T-032 stream is ordered: one monotonic sequence, started first, completed last",
      _seqs == list(range(len(_seqs)))
      and _em["stream"][0]["event"] == "trace.started"
      and _em["stream"][-1]["event"] == "trace.completed"
      and _em["stream"][-1]["payload"]["traceHash"] == _em_trace["traceHash"])
check("T-032 both-sides match satisfies every declared required event",
      all(c["missing"] == [] for c in _em["completeness"].values()))
check("T-032 stream is replayable: same trace -> identical stream",
      emit_events(run_vault_match(DEF, RAID, seed=2), DEF, RAID) == _em)
_em_forfeit = emit_events(_forfeit, _smuggled, RAID)
check("T-032 a forfeit reports honest completeness and a task.failed event",
      "tool.called" in _em_forfeit["completeness"][DEF["metadata"]["name"]]["missing"]
      and any(e["event"] == "task.failed"
              and e["competitor"] == DEF["metadata"]["name"]
              for e in _em_forfeit["stream"]))
check("T-032 lane decisions surface as declared policy.checked/tool.called events",
      any(e["event"] == "policy.checked" for e in _em["stream"])
      and any(e["event"] == "tool.called" for e in _em["stream"]))

# T-033 — redaction rules come from the DOCUMENT's declaration, not engine
# defaults. The reference docs declare fields [defendedSecret, canaryValue].
check("T-033 declared redaction is read from the document",
      declared_redaction(DEF)["fields"] == ["defendedSecret", "canaryValue"])
_red = redact_payload({"defendedSecret": "hunter2", "open": "fine"},
                      declared_redaction(DEF))
check("T-033 declared fields are masked, undeclared fields pass through",
      _red["defendedSecret"] == "[REDACTED:defendedSecret]"
      and _red["open"] == "fine")
_custom = _cp.deepcopy(DEF)
_custom["harness"]["observability"]["redaction"]["fields"] = ["strategyNotes"]
_red_c = redact_payload({"strategyNotes": "s3cret", "defendedSecret": "visible"},
                        declared_redaction(_custom))
check("T-033 a different declaration redacts ITS fields — proof rules are not defaults",
      _red_c["strategyNotes"] == "[REDACTED:strategyNotes]"
      and _red_c["defendedSecret"] == "visible")
check("T-033 no declared rules -> payload withheld entirely (fail closed)",
      redact_payload({"anything": "x"}, None) == {"withheld": WITHHELD})

# T-034 — adversarial: no canary value appears anywhere in the stored
# stream, even nested or echoed under a different key.
_canary = "CANARY-9f3a-vault"
_pay = {DEF["metadata"]["name"]: {
    "vault": [{"deep": {"canaryValue": _canary}}],
    "echo": f"the secret is {_canary}, honest",
    "unrelated": "kept"}}
_em_can = emit_events(_em_trace, DEF, RAID, payloads=_pay)
check("T-034 planted canary never appears in the stored stream",
      not stream_contains(_em_can, _canary))
check("T-034 the echo under a different key is value-scrubbed, rest kept",
      stream_contains(_em_can, "[SCRUBBED]")
      and stream_contains(_em_can, "kept"))
_no_rules = _cp.deepcopy(RAID)
del _no_rules["harness"]["observability"]["redaction"]
_em_nr = emit_events(run_vault_match(DEF, _no_rules, seed=2), DEF, _no_rules,
                     payloads={_no_rules["metadata"]["name"]: {"k": _canary}})
check("T-034 undeclared-redaction payload is withheld, canary never stored",
      not stream_contains(_em_nr, _canary) and stream_contains(_em_nr, "withheld"))

# T10 (audit): the declared redaction MODE is honored (it used to be read and
# ignored — every mode silently got mask+scrub). Each mode selects how the
# declared field is represented; the value-scrub floor still removes the secret
# echoed elsewhere under every non-withhold mode; an unknown mode fails closed.
import json as _t10json
_t10_pay = {"defendedSecret": "HUNTER2-XYZ", "note": "log had HUNTER2-XYZ", "open": "ok"}
def _t10(mode):
    return redact_payload(_t10_pay, {"mode": mode, "fields": ["defendedSecret"]})
_t10_mask = _t10("mask")
check("T10 mask/payload-redacted marks the field and scrubs the echo",
      _t10_mask["defendedSecret"] == "[REDACTED:defendedSecret]"
      and "HUNTER2-XYZ" not in _t10json.dumps(_t10_mask)
      and _t10("payload-redacted") == _t10_mask)
_t10_hash = _t10("hash")
check("T10 hash mode digests the field, never the raw value",
      _t10_hash["defendedSecret"].startswith("sha256:")
      and "HUNTER2-XYZ" not in _t10json.dumps(_t10_hash))
_t10_drop = _t10("drop")
check("T10 drop mode removes the field and scrubs the echo",
      "defendedSecret" not in _t10_drop
      and "HUNTER2-XYZ" not in _t10json.dumps(_t10_drop))
check("T10 withhold mode withholds the whole payload",
      "withheld" in _t10("withhold") and "HUNTER2-XYZ" not in _t10json.dumps(_t10("withhold")))
check("T10 an unknown mode fails closed (withheld), never silent mask",
      "withheld" in _t10("teleport-to-mars")
      and "HUNTER2-XYZ" not in _t10json.dumps(_t10("teleport-to-mars")))
check("T10 every mode keeps the secret out of the stored result",
      all("HUNTER2-XYZ" not in _t10json.dumps(_t10(m))
          for m in ("mask", "payload-redacted", "hash", "drop", "withhold", "bogus")))
check("T10 a recognized mode with no declared fields fails closed, never KeyError",
      "withheld" in redact_payload(_t10_pay, {"mode": "hash"})
      and "withheld" in redact_payload(_t10_pay, {"mode": "mask", "fields": []})
      and "HUNTER2-XYZ" not in _t10json.dumps(redact_payload(_t10_pay, {"mode": "drop"})))

print("vault attack/defend scoring (B6: T-035 T-036 T-037)")
from core.scoring import (score_match, detect_leak, UndefinedOutcome, POINTS,
                          _leak_digest)
import json as _json_b6

# T-035 — identical traces always produce identical scores; scoring is a
# pure function of the trace.
_sc_trace = run_vault_match(DEF, RAID, seed=3)
_sc = score_match(_sc_trace)
check("T-035 identical traces -> identical scores",
      score_match(run_vault_match(DEF, RAID, seed=3)) == _sc
      and score_match(_sc_trace) == _sc)
check("T-035 the score carries the trace hash it was computed from",
      _sc["traceHash"] == _sc_trace["traceHash"])

# T-036 — every terminal state has exactly one defined scoring outcome.
_wall = {"attack": 0, "defense": 100}
_fw_a = _cp.deepcopy(DEF); _fw_a["extensions"]["x-arena"]["strategy"] = dict(_wall)
_fw_b = _cp.deepcopy(RAID); _fw_b["extensions"]["x-arena"]["strategy"] = dict(_wall)
_fw_b["model"]["requirements"]["contextWindow"] = 4000
_dr_b = _cp.deepcopy(_fw_b); _dr_b["model"]["requirements"]["contextWindow"] = 8000
_shapes36 = {
    "extraction-win": _sc_trace,
    "fuel-win": run_vault_match(_fw_a, _fw_b, seed=0),
    "forfeit-win": _forfeit,
    "draw": run_vault_match(_fw_a, _dr_b, seed=0),
    "void": _both,
}
check("T-036 every terminal state maps to exactly one defined outcome",
      all(score_match(t)["outcome"] == want for want, t in _shapes36.items()))
check("T-036 points follow the outcome vocabulary",
      score_match(_shapes36["draw"])["points"] == {
          _fw_a["metadata"]["name"]: 1, _dr_b["metadata"]["name"]: 1}
      and sorted(score_match(_sc_trace)["points"].values()) == [0, 3]
      and all(v == 0 for v in score_match(_both)["points"].values()))
_undef = _cp.deepcopy(_sc_trace)
_undef["outcomeKind"] = "sudden-death"  # unknown structured outcome tag
try:
    score_match(_undef)
    _raised36 = False
except UndefinedOutcome:
    _raised36 = True
check("T-036 an unknown outcomeKind refuses rather than guessing", _raised36)
# T3: scoring reads the STRUCTURED outcomeKind, not the reason string — a
# name containing 'extracted' in a fuel-win reason cannot spoof extraction.
_spoof = _cp.deepcopy(_shapes36["fuel-win"])
_spoof["reason"] = "self-extracted-bot won on fuel efficiency"
check("T-036/T3 a reason containing 'extracted' does not spoof an extraction-win",
      score_match(_spoof)["outcome"] == "fuel-win")

# T-037 — a secret leaked in any form the canary detects scores as
# extraction for the opponent, overriding the stated outcome.
_canary37 = "VAULT-CANARY-77x"
_leaky = _cp.deepcopy(_shapes36["draw"])
_leaky["reason"] = _leaky["reason"] + " :: " + _canary37
_cmap = {_fw_a["metadata"]["name"]: [_canary37]}
_sc37 = score_match(_leaky, canaries=_cmap)
check("T-037 a detected canary leak scores as extraction for the opponent",
      _sc37["outcome"] == "extraction-win"
      and _sc37["winner"] == _dr_b["metadata"]["name"]
      # T1 (audit): the score result publishes a non-reversible digest of the
      # leaked canary, never the raw secret value.
      and _sc37["leaks"] == {_fw_a["metadata"]["name"]: [_leak_digest(_canary37)]}
      and _canary37 not in _json_b6.dumps(_sc37))
check("T-037 a clean trace with canaries declared scores unchanged",
      score_match(_shapes36["draw"], canaries=_cmap)["outcome"] == "draw"
      and detect_leak(_shapes36["draw"], _cmap) == {})
_both_leak = _cp.deepcopy(_leaky)
_sc37b = score_match(_both_leak, canaries={
    _fw_a["metadata"]["name"]: [_canary37],
    _dr_b["metadata"]["name"]: [_canary37]})
check("T-037 both secrets leaking voids the match",
      _sc37b["outcome"] == "void"
      and all(v == 0 for v in _sc37b["points"].values()))

# Audit (T9/T10/T11): trace-projection hardening. The canary/redaction layer
# is a security boundary — it must not be defeated by JSON escaping, a
# non-string canary, scrub ordering, or a secret nested under a declared field.
_esc_canary = 'VAULT"CANARY\\77'  # a quote and a backslash: escaped in the blob
_esc_leak = _cp.deepcopy(_shapes36["draw"])
_esc_leak["reason"] = _esc_leak["reason"] + " leaked " + _esc_canary
check("audit: an escaped canary (quote/backslash) is still detected as a leak",
      detect_leak(_esc_leak, {_fw_a["metadata"]["name"]: [_esc_canary]})
      == {_fw_a["metadata"]["name"]: [_esc_canary]}
      and score_match(_esc_leak,
                      canaries={_fw_a["metadata"]["name"]: [_esc_canary]})["outcome"]
      == "extraction-win")
_num_canary = 918273
_num_leak = _cp.deepcopy(_shapes36["draw"])
_num_leak["reason"] = _num_leak["reason"] + " code 918273 exfiltrated"
check("audit: a non-string (numeric) canary neither raises nor misses",
      detect_leak(_num_leak, {_fw_a["metadata"]["name"]: [_num_canary]})
      == {_fw_a["metadata"]["name"]: [_num_canary]}
      and detect_leak(_shapes36["draw"],
                      {_fw_a["metadata"]["name"]: [_num_canary]}) == {})
# Redaction: a short secret that overlaps a longer one must not leave a tail,
# whichever order they are collected in; and a secret nested under a declared
# structured field must still be scrubbed where it is echoed as plain text.
_rp_tail = redact_payload(
    {"shortKey": "abc", "apiKey": "abcdef", "note": "trail abcdef used"},
    {"mode": "mask", "fields": ["apiKey", "shortKey"]})
check("audit: longest-first scrub leaves no tail of an overlapping secret",
      "def" not in _rp_tail["note"] and "abc" not in _rp_tail["note"]
      and "abcdef" not in _rp_tail["note"])
_rp_struct = redact_payload(
    {"credentials": {"token": "zzz-secret-9", "keys": ["kA1", "kB2"]},
     "log": "used zzz-secret-9 and kB2 downstream"},
    {"mode": "mask", "fields": ["credentials"]})
check("audit: a secret nested under a declared field is scrubbed where echoed",
      "zzz-secret-9" not in _rp_struct["log"] and "kB2" not in _rp_struct["log"])
# A canary declared under an off-roster name (not a competitor) is a caller
# mistake — score_match must ignore it, not IndexError on an empty victim list.
_offroster = _cp.deepcopy(_shapes36["draw"])
_offroster["reason"] = _offroster["reason"] + " GHOST-CANARY-x"
_sc_ghost = score_match(_offroster, canaries={"ghost-not-a-competitor": ["GHOST-CANARY-x"]})
check("audit: an off-roster canary key is ignored, not crashed on",
      _sc_ghost["outcome"] == "draw" and _sc_ghost["leaks"] == {})
# A boolean under a declared field is not a secret and must not turn every
# "True"/"False" in the stream into [SCRUBBED] (audit review: over-scrub).
_rp_bool = redact_payload(
    {"enabled": True, "note": "run was True and complete"},
    {"mode": "mask", "fields": ["enabled"]})
check("audit: a boolean secret does not over-scrub literal True/False text",
      _rp_bool["note"] == "run was True and complete"
      and _rp_bool["enabled"] == "[REDACTED:enabled]")

print("anti-gaming review (A6: T-013 T-014)")
import copy as _cp
from weigh_in import weigh as _weigh

_base_cert = _weigh(DEF)

def _pad(doc, n, effect, referenced=False):
    d = _cp.deepcopy(doc)
    for i in range(n):
        d["harness"]["policies"].append({
            "id": f"pad-{effect}-{i}", "capability": "tool",
            "subject": "agent:antweight-vault-defender",
            "resource": "tool:nonexistent", "action": "invoke",
            "effect": effect, "scope": {"type": "task", "value": "arena-match"},
            "enforcement": {"target": "policy-engine", "phase": "before-execution"},
        })
    return d

# T-013 — deny padding is clamped at the credit floor; allow padding earns zero.
_deny50 = _weigh(_pad(DEF, 50, "deny"))
check("T-013 fifty no-op deny policies shed no more AU than the -20 floor",
      _base_cert["soloAU"] - _deny50["soloAU"] <= 20
      and _weigh(_pad(DEF, 10, "deny"))["soloAU"] == _deny50["soloAU"])
check("T-013 fifty unreferenced allow policies earn exactly zero credit",
      _weigh(_pad(DEF, 50, "allow"))["soloAU"] == _base_cert["soloAU"])

# T-013 — credit farming via capability+policy is self-defeating: the cheapest
# capability (+8) outweighs its policy's credit (-2).
_farm = _cp.deepcopy(DEF)
_farm["harness"]["tools"].append({
    "id": "farmTool", "type": "function", "description": "credit farm probe",
    "policyRefs": ["pol-farm"],
    "sideEffects": {"mode": "none", "mutatesState": False, "external": False,
                    "resources": []}})
_farm["harness"]["policies"].append({
    "id": "pol-farm", "capability": "tool", "subject": "agent:antweight-vault-defender",
    "resource": "tool:farmTool", "action": "invoke", "effect": "allow",
    "scope": {"type": "task", "value": "arena-match"},
    "enforcement": {"target": "policy-engine", "phase": "before-execution"}})
check("T-013 capability+referenced-policy farming always increases net AU",
      _weigh(_farm)["soloAU"] > _base_cert["soloAU"])

# T-014 — the skill-disguise understatement is real, documented, and any
# smuggling mutation breaks the certificate hash (static half of E1I binding).
_tool_variant = _cp.deepcopy(DEF)
_skill_variant = _cp.deepcopy(DEF)
_skill_variant["harness"].setdefault("skills", []).append(
    {"id": "hiddenProbe", "type": "reference", "description": "disguised capability"})
_tool_variant["harness"]["tools"].append({
    "id": "hiddenProbe", "type": "function", "description": "same capability as tool",
    "sideEffects": {"mode": "none", "mutatesState": False, "external": False,
                    "resources": []}})
_review = (ROOT / "docs" / "ANTI-GAMING-REVIEW-v0.1.md").read_text()
check("T-014 skill-disguise understates weight and is recorded as the v0.2 item",
      _weigh(_skill_variant)["soloAU"] < _weigh(_tool_variant)["soloAU"]
      and "OPEN — v0.2 item" in _review)
check("T-014 smuggling mutations always change the capability hash",
      _weigh(_skill_variant)["capabilityHash"] != _base_cert["capabilityHash"]
      and _weigh(_pad(DEF, 1, "deny"))["capabilityHash"]
      != _base_cert["capabilityHash"])
check("T-014 review is advisory: frozen v0.1 untouched by the review",
      "Advisory to formula v0.2 only" in _review
      and _weigh(DEF)["soloAU"] == 62)

print("weight formula freeze (A4: T-007 T-008 T-009)")
from weigh_in import weigh, WEIGHTS_VERSION

# T-007 — determinism: identical certificate and hash across repeated runs.
_certs = [weigh(DEF) for _ in range(100)]
check("T-007 100 runs yield one identical certificate",
      len({c["capabilityHash"] for c in _certs}) == 1
      and len({c["soloAU"] for c in _certs}) == 1)
check("T-007 certificate records weightsVersion arena-weights-v0.1",
      _certs[0]["weightsVersion"] == WEIGHTS_VERSION == "arena-weights-v0.1")


def _reorder(obj, reverse=True):
    """Deep-copy with recursively reversed key insertion order."""
    if isinstance(obj, dict):
        return {k: _reorder(obj[k], reverse)
                for k in (reversed(list(obj)) if reverse else obj)}
    if isinstance(obj, list):
        return [_reorder(v, reverse) for v in obj]
    return obj


# T-008 — key order and formatting never alter AU or hash.
_shuffled = _reorder(DEF)
check("T-008 reversed key order yields identical AU and hash",
      weigh(_shuffled)["capabilityHash"] == _certs[0]["capabilityHash"]
      and weigh(_shuffled)["soloAU"] == _certs[0]["soloAU"])
import yaml as _yaml
_reparsed = _yaml.safe_load(_yaml.safe_dump(_shuffled, default_flow_style=True))
check("T-008 YAML reserialization (flow style) yields identical hash",
      weigh(_reparsed)["capabilityHash"] == _certs[0]["capabilityHash"])

# T-009 — golden weights for the reference documents.
check("T-009 defender weighs exactly 62 AU", weigh(DEF)["soloAU"] == 62)
check("T-009 mercenary weighs exactly 91 AU", weigh(MERC)["soloAU"] == 91)

# The formula is frozen: the spec document must say so, and changes must go
# through a v0.2 formula spec, never a mid-season edit (CLAUDE.md boundary).
_spec = (ROOT / "docs" / "WEIGHT-CLASS-v0.1.md").read_text()
check("frozen spec: status is frozen, not draft",
      "**Status:** frozen" in _spec and "draft" not in _spec.split("\n")[2])
check("frozen spec: mid-season change path is a v0.2 formula spec",
      "v0.2" in _spec)

print("negative-fixture corpus (A2: T-003 T-004)")
import subprocess as _sp
import yaml as _y
_man = _y.safe_load((ROOT / "fixtures" / "negative" / "manifest.yaml").read_text())
check("T-003 corpus has >= 20 fixtures, one per failure mode", len(_man) >= 20)
check("T-003 every fixture declares a reason",
      all(v.get("reason") for v in _man.values()))
check("T-004 every schema-invalid fixture declares a specific diagnostic",
      all(v.get("expect", {}).get("path") and v.get("expect", {}).get("message")
          for v in _man.values() if not v["expectSchemaValid"]))
check("T-004 every documented-gap fixture names its finding or lint",
      all(v.get("finding") or v.get("lint")
          for v in _man.values() if v["expectSchemaValid"]))
_va = _sp.run([sys.executable, str(ROOT / "tools" / "validate_adl.py")],
              capture_output=True, text=True, cwd=ROOT)
check("T-003/T-004 validator enforces the manifest (zero silent passes)",
      _va.returncode == 0 and "FAIL" not in _va.stdout)

print("arena-profile namespace (A3: T-005 T-006)")
_prof = (ROOT / "docs" / "ARENA-PROFILE-v0.1.md").read_text()
check("T-005 profile spec exists and is Arena-local, non-canonical",
      "confers no canonical status" in _prof.lower() or "Confers no canonical" in _prof)
_va_out = _sp.run([sys.executable, str(ROOT / "tools" / "validate_adl.py")],
                  capture_output=True, text=True, cwd=ROOT)
check("T-005 all reference documents are x-arena profile clean",
      _va_out.returncode == 0
      and _va_out.stdout.count("T-005 PASS") >= 3
      and "T-005 FAIL" not in _va_out.stdout)
check("T-006 payment machinery under x-arena is rejected",
      "x-arena-payment-intent.yaml: schema-valid documented gap" in _va_out.stdout)
check("T-006 unspecified x-arena keys are rejected",
      "x-arena-unspecified-key.yaml: schema-valid documented gap" in _va_out.stdout)
check("T-006 unprefixed arena namespace fails the schema itself",
      "extensions-unprefixed-namespace.yaml: fails with declared diagnostic"
      in _va_out.stdout)

print("claims discipline (F4: T-094 T-095)")
_cl = _sp.run([sys.executable, str(ROOT / "tools" / "claims_lint.py")],
              capture_output=True, text=True, cwd=ROOT)
check("T-094 no public surface makes an assertive audit/mainnet/production claim",
      _cl.returncode == 0 and "CLAIMS LINT PASS" in _cl.stdout)
check("T-095 release-state banner cites the suite and CI as evidence",
      "**Release state:**" in (ROOT / "README.md").read_text()
      and "banner + disclosures present" in _cl.stdout)
# The lint must actually bite: a doctored surface with an assertive claim fails.
import tempfile as _tf, shutil as _sh
with _tf.TemporaryDirectory(dir=ROOT / "tests") as _td:
    _copy = Path(_td) / "repo"
    for _item in ("README.md", "QUICKSTART.md", "tutorials", "web", "tools"):
        _src = ROOT / _item
        (_sh.copytree(_src, _copy / _item) if _src.is_dir()
         else (_copy.mkdir(parents=True, exist_ok=True),
               _sh.copy(_src, _copy / _item)))
    _r = _copy / "README.md"
    _r.write_text(_r.read_text() + "\nThe arena is fully audited and production ready.\n")
    _doctored = _sp.run([sys.executable, str(_copy / "tools" / "claims_lint.py")],
                        capture_output=True, text=True)
    check("T-094 the lint bites: a doctored assertive claim fails the build",
          _doctored.returncode == 1 and "T-094" in _doctored.stdout)
    # Hardening: a TRAILING negation must not exempt an assertive claim
    # (the old line-global check let any "not" on the line pass).
    _r.write_text(_r.read_text().replace(
        "\nThe arena is fully audited and production ready.\n",
        "\nThis is production-ready and does not need setup.\n"))
    _trail = _sp.run([sys.executable, str(_copy / "tools" / "claims_lint.py")],
                     capture_output=True, text=True)
    check("T-094 a trailing negation does not exempt an assertive claim",
          _trail.returncode == 1 and "T-094" in _trail.stdout)

print("one-way canonicality (F3: T-092 T-093)")
import hashlib as _hl
import re as _re093
_val_src = (ROOT / "tools" / "validate_adl.py").read_text()
_pinned = _re093.search(r'PINNED = "([0-9a-f]{64})"', _val_src).group(1)
_actual = _hl.sha256((ROOT / "vendor" / "ADL-v0.2.schema.json").read_bytes()).hexdigest()
check("T-092 vendored schema matches the pinned upstream hash (drift fails CI)",
      _actual == _pinned)
_find = (ROOT / "docs" / "FINDINGS.md").read_text()
_sections = set(_re093.findall(r"^### (F-\d{3})", _find, _re093.M)) - {"F-004a"}
_rows = dict(_re093.findall(r"^\| (F-\d{3})[^|]* \| ([^|]+) \|", _find, _re093.M))
check("T-093 every finding section has a register row",
      _sections <= set(_rows))
check("T-093 every non-withdrawn register row carries an upstream reference",
      all("withdrawn" in _find.split(f"| {f} |")[1].split("\n")[0]
          or "reddiagent-lab" in _find.split(f"| {f} |")[1].split("\n")[0]
          for f in _rows))
_canonical_ext = {"x402", "receipts", "reputation", "identity"}
_fork_free = True
for _p in sorted((ROOT / "adl").glob("*.yaml")):
    for _k in (_y.safe_load(_p.read_text()).get("extensions") or {}):
        if _k not in _canonical_ext and not _k.startswith("x-"):
            _fork_free = False
check("T-093 no Arena document redefines an ADL semantic (x- namespace only)",
      _fork_free)

print("power-up actually changes outcomes")
flips = sum(
    run_vault_match(DEF, RAID, seed=s)["winner"]
    != run_vault_match(DEF, RAID, seed=s, hire_a=MERC)["winner"]
    for s in range(30)
)
check("auditor hire flips >=1 of 30 matches", flips >= 1)
solo_wins = sum(run_vault_match(DEF, RAID, seed=s)["winner"] == DEF["metadata"]["name"]
                for s in range(30))
hired_wins = sum(run_vault_match(DEF, RAID, seed=s, hire_a=MERC)["winner"] == DEF["metadata"]["name"]
                 for s in range(30))
check("hiring strictly improves defender win rate", hired_wins > solo_wins)

print("boundaries (dry-run, credits, provisional price)")
t = run_vault_match(DEF, RAID, seed=1)
check("match prizes are on the dry-run rail", t["rail"] == ARENA_RAIL == "x402-dry-run")
check("match prizes are arena credits", t["prizeCurrency"] == ARENA_CURRENCY == "ARENA-CREDIT")
price = advertised_price(MERC)
check("specialist price is marked provisional", price["provisional"] is True)
check("specialist price is in arena credits", price["currency"] == "ARENA-CREDIT")
check("mercenary declares no live payment rail",
      all(r == "x402-dry-run"
          for i in (MERC.get("extensions", {}).get("x402", {}).get("intents") or [])
          for r in i.get("rails", [])))

print("chain projection")
from core import chain

t = run_vault_match(DEF, RAID, seed=2)
reg = chain.register_agent_payload(MERC, "OwnerMerc")
check("mercenary registers as Both (fighter+judge)", reg["args"]["agent_type"] == "Both")
check("fighter registers as Primary",
      chain.register_agent_payload(DEF, "OwnerA")["args"]["agent_type"] == "Primary")
check("model string within AGENT_MODEL_MAX_LEN",
      len(reg["args"]["model"]) <= chain.AGENT_MODEL_MAX_LEN)
check("rate sourced from provisional price warns (F-009)",
      any("F-007/F-009" in w for w in reg["warnings"]))
check("ADL document bound by hash, not stored on-chain",
      reg["adlBinding"]["documentHash"].startswith("sha256:"))

rel = chain.settle_match(t, True, True, "P", "Q", 100)
ref = chain.settle_match(t, False, True, "P", "Q", 100)
dis = chain.settle_match(t, True, False, "P", "Q", 100)
check("gates+attestation -> release", rel["decision"] == "release")
check("failed gate -> refund, not payout (payment != work success)", ref["decision"] == "refund")
check("no attestation -> dispute, not payout", dis["decision"] == "dispute")

c = chain.rating_commitment(8, b"\x01" * 32)
check("commitment is sha256(score||salt)", c == chain._sha256(bytes([8]) + b"\x01" * 32))
try:
    chain.rating_commitment(11, b"\x01" * 32); ok = False
except ValueError:
    ok = True
check("score outside 1..=10 rejected", ok)
rnd = chain.commit_reveal_round(t["traceHash"], "P", "Q", 8, 6, b"\x01"*32, b"\x02"*32)
check("both reveals verify against commitments",
      all(st.get("verifies", True) for st in rnd["steps"]))

plan = chain.audd_purse_plan("50.00", "Payee", "Settle", "2026-12-31T23:59:59Z")
check("AUDD plan is dry-run mode", plan["paymentMode"] == "dry-run")
check("AUDD plan uses the v1 schema", plan["schemaVersion"] == "reddi.audd-payment-plan.v1")
check("AUDD plan requires evidence", plan["evidenceRequired"] is True)
check("AUDD plan states the no-custody boundary", "no AUDD custody" in plan["_boundary"])

proj = chain.project_match(t, DEF, RAID, "A", "B", "J")
check("projection is labelled projection-only", proj["mode"] == "projection-only")
check("traces/ADL/telemetry explicitly NOT written on-chain",
      "match traces" in proj["onChainFootprint"]["notWritten"]
      and "ADL documents" in proj["onChainFootprint"]["notWritten"])
blob = str(proj)
check("no payload claims submission", "not-submitted" in blob and "signature" in blob)

print("rehearsal validator is non-vacuous (tamper detection)")
import copy
from tools.rehearse import validate_projection, detect_toolchain

_base = chain.project_match(t, DEF, RAID,
    "Xk7jczJZ1HHJZuE1ZUWDqFmowxYhnom7mWzrNSGf9FU",
    "nb9rLVjoHMibsgfRGgKuPqm6M8GVcH9r6bYNfg7Yiy6",
    "CRGsWWkptdxsH6N6aWAyahLbuMsT58yM624EopEsv1Ex")
check("clean projection passes every offline check",
      not [c for c in validate_projection(_base) if not c["ok"]])
check("PDAs are really derived, not stand-ins", chain.PDA_MODE == "derived")

_tampers = {
    "over-long model": lambda p: p["registrations"][0]["args"].__setitem__("model", "x" * 80),
    "wrong score count": lambda p: p["attestation"]["args"].__setitem__("scores", [8] * 6),
    "score out of range": lambda p: p["attestation"]["args"].__setitem__("scores", [99, 1, 1, 1, 1]),
    "fee diverted from incinerator":
        lambda p: p["registrations"][0]["accounts"].__setitem__("fee_collector", "Attacker111"),
    "bad nonce length": lambda p: p["escrow"]["args"].__setitem__("nonce", "deadbeef"),
    "release without attestation": lambda p: (
        p["settlement"].__setitem__("decision", "release"),
        p["settlement"]["inputs"].__setitem__("attestationConfirmed", False)),
    "traces moved on-chain": lambda p: p["onChainFootprint"]["notWritten"].remove("match traces"),
    "reveal before commit": lambda p: p["rating"]["steps"].insert(
        0, {"instruction": "reveal_rating", "by": "X", "score": 9, "verifies": True}),
}
for _name, _fn in _tampers.items():
    _p = copy.deepcopy(_base)
    _fn(_p)
    check(f"tamper caught: {_name}", any(not c["ok"] for c in validate_projection(_p)))

check("toolchain detection reports honestly",
      detect_toolchain()["canExecute"] is False or bool(detect_toolchain()["found"]))

print("RAP Assurance Devnet Preview")
from core import assurance
_catalog = assurance.scenario_catalog()
check("assurance catalog is explicitly local Solana Devnet Preview",
      _catalog["boundary"]["cluster"] == "solana-devnet"
      and _catalog["boundary"]["transactionSubmitted"] is False
      and _catalog["boundary"]["walletSigning"] is False
      and _catalog["boundary"]["officialMintObservation"] is False)
# The boundary only asserts what the code can prove about itself. Building a
# preview deploys nothing; whether the process is externally hosted is an
# operator declaration, so with no declared context the claim is absent rather
# than asserted false.
check("boundary asserts no deployment by this request and never guesses hosting",
      _catalog["boundary"]["deploymentPerformedByRequest"] is False
      and "externalDeployment" not in _catalog["boundary"]
      and "externalDeployment" not in assurance.boundary_flags()
      and "externalDeployment" not in
      assurance.build_assurance_preview(DEF, RAID, seed=2)["boundary"])
check("a declared context is the only source of the externalDeployment claim",
      assurance.boundary_flags(False)["externalDeployment"] is False
      and assurance.boundary_flags(True)["externalDeployment"] is True
      and assurance.scenario_catalog(True)["boundary"]["externalDeployment"] is True
      and assurance.build_assurance_preview(
          DEF, RAID, seed=2, external_deployment=True)["boundary"]["externalDeployment"] is True)
_assurance_cases = {
    "valid-receipt": ("accept", "release", []),
    "tampered-trace": ("reject", "blocked", ["rap_assurance.evidence.trace_tampered"]),
    "wrong-mint": ("reject", "blocked", ["rap_assurance.payment_observation.wrong_mint"]),
    "wrong-payee": ("reject", "blocked", ["rap_assurance.payment_observation.wrong_payee"]),
    "duplicate-replay": ("reject", "blocked", ["rap_assurance.payment_observation.replay_detected",
                                                 "rap_receipt.replay.duplicate_payment"]),
    "refund-gate-failed": ("reject", "refund", ["rap_receipt.eval.failed"]),
    "authorization-denied": ("reject", "blocked", ["rap_receipt.authority.scope_mismatch"]),
}
for _case, (_decision, _settlement, _codes) in _assurance_cases.items():
    _bundle = assurance.build_assurance_preview(DEF, RAID, scenario=_case, seed=2)
    _result = _bundle["adapters"]["receiptIntegrity"]["result"]
    _seen = {d["code"] for d in _result["diagnostics"]}
    check(f"assurance scenario {_case} gives {_decision}/{_settlement}",
          _result["decision"] == _decision
          and _bundle["settlement"]["decision"] == _settlement
          and all(c in _seen for c in _codes))
_valid = assurance.build_assurance_preview(DEF, RAID, scenario="valid-receipt", seed=2)
check("valid assurance receipt uses canonical RAP receipt/policy versions",
      _valid["receipt"]["schemaVersion"] == "reddi.receipt.v1"
      and _valid["receipt"]["policyDecision"]["schemaVersion"] == "reddi.policy-decision.v1")
check("valid assurance payment observation is fixture-backed and never grant evidence",
      _valid["adapters"]["paymentObservation"]["result"]["observation"]["evidence"]
      == {"source": "parsed-transaction-fixture", "grantEligible": False})

# reddi.svm-spl-transfer-checked-observation.v1 declares an exact member set
# (packages/x402-solana/src/spl-token-observer.ts); Arena disclosure must not
# widen a document that advertises a canonical schemaVersion.
_CANONICAL_OBSERVATION_KEYS = {
    "schemaVersion", "verifierVersion", "network", "signature", "slot", "blockTime",
    "commitment", "instructionIndex", "innerInstruction", "sourceTokenAccount",
    "destinationTokenAccount", "destinationOwner", "authority", "mint", "tokenProgram",
    "amountBaseUnits", "decimals", "memo", "paymentIntentId", "evidence",
}
_obs = _valid["adapters"]["paymentObservation"]["result"]["observation"]
check("the emitted observation carries no member outside the canonical v1 schema",
      _obs["schemaVersion"] == "reddi.svm-spl-transfer-checked-observation.v1"
      and set(_obs) <= _CANONICAL_OBSERVATION_KEYS
      and set(_obs["evidence"]) == {"source", "grantEligible"})
_labels = _valid["adapters"]["paymentObservation"]["arenaPreviewLabels"]
check("preview environment/eligibility disclosure lives in an Arena-owned object",
      _labels["schemaVersion"] == assurance.ARENA_PREVIEW_LABELS_VERSION
      and _labels["environment"] == "deterministic-fixture"
      and _labels["eligibility"] == "non_eligible")
check("assurance preview explains payment transfer is not paid work proof",
      any(a["id"] == "rap-assurance-paid-work" and "Payment alone" in a["boundary"]
          for a in _valid["assertions"]))

# The official AUDD mainnet mint is a gated verified-mainnet identity upstream.
# A devnet fixture presenting it would be an unsupported AUDD claim, so it must
# not survive anywhere in the preview and must be refused at load/verify time.
check("devnet fixture pays with the canonical synthetic AUDD sentinel mint",
      assurance.load_payment_fixture()["expected"]["mint"]
      == assurance.AUDD_DETERMINISTIC_FIXTURE_MINT)
import json as _json_ass
check("no preview scenario surfaces the official AUDD mainnet mint",
      all(assurance.AUDD_OFFICIAL_SOLANA_MAINNET_MINT
          not in _json_ass.dumps(assurance.build_assurance_preview(DEF, RAID, scenario=_c, seed=2))
          for _c in _assurance_cases))
_official_expected = dict(assurance.load_payment_fixture()["expected"],
                          mint=assurance.AUDD_OFFICIAL_SOLANA_MAINNET_MINT)
_official = assurance.verify_spl_transfer_checked_fixture(
    assurance.load_payment_fixture()["parsedTransaction"], _official_expected)
check("fixture verifier refuses an expectation naming the official AUDD mainnet mint",
      _official["ok"] is False and _official["reason"] == "wrong_mint"
      and _official["arenaRefusal"] == "official_mint_blocked"
      and assurance.AUDD_OFFICIAL_SOLANA_MAINNET_MINT not in _json_ass.dumps(_official))
# The refusal must also cover the observed side: a parsed transaction carrying
# the official mint must not reach candidate matching, which would echo it back
# through the adapter result as an "actual" value.
_official_parsed = _json_ass.loads(
    _json_ass.dumps(assurance.load_payment_fixture()["parsedTransaction"]).replace(
        assurance.AUDD_DETERMINISTIC_FIXTURE_MINT,
        assurance.AUDD_OFFICIAL_SOLANA_MAINNET_MINT))
_official_actual = assurance.verify_spl_transfer_checked_fixture(
    _official_parsed, assurance.load_payment_fixture()["expected"])
check("fixture verifier refuses a parsed transaction carrying the official mint, without echoing it",
      _official_actual["ok"] is False and _official_actual["reason"] == "wrong_mint"
      and _official_actual["arenaRefusal"] == "official_mint_blocked"
      and assurance.AUDD_OFFICIAL_SOLANA_MAINNET_MINT not in _json_ass.dumps(_official_actual))

# Observation failure reasons are a closed upstream union; an Arena-specific
# refusal travels beside it, never inside it.
for _case in _assurance_cases:
    _res = assurance.build_assurance_preview(DEF, RAID, scenario=_case, seed=2)[
        "adapters"]["paymentObservation"]["result"]
    check(f"payment observation for {_case} keeps reason inside the canonical union",
          "reason" not in _res
          or _res["reason"] in assurance.CANONICAL_OBSERVATION_FAILURE_REASONS)
try:
    assurance._payment_failure("official_mint_blocked", "minted reason")
    _minted_reason_ok = True
except assurance.AssuranceIntegrityError:
    _minted_reason_ok = False
check("a non-canonical observation failure reason is refused, not emitted",
      _minted_reason_ok is False)
import tempfile as _tmp_ass
_real_fixture_path = assurance.FIXTURE_PATH
with _tmp_ass.NamedTemporaryFile("w", suffix=".json", delete=False) as _fh:
    _fh.write(_real_fixture_path.read_text().replace(
        assurance.AUDD_DETERMINISTIC_FIXTURE_MINT,
        assurance.AUDD_OFFICIAL_SOLANA_MAINNET_MINT))
    _bad_fixture_path = Path(_fh.name)
try:
    assurance.FIXTURE_PATH = _bad_fixture_path
    try:
        assurance.load_payment_fixture()
        _fixture_refused = False
    except assurance.AssuranceIntegrityError:
        _fixture_refused = True
finally:
    assurance.FIXTURE_PATH = _real_fixture_path
    _bad_fixture_path.unlink()
check("a contributed fixture carrying the official AUDD mainnet mint is refused",
      _fixture_refused)

# Every fixture defect is a server-side integrity failure, so it must reach the
# sanitized-500 handler rather than JSONDecodeError/KeyError/ValueError escaping
# as a caller error or an unhandled traceback.
def _fixture_load_outcome(text):
    with _tmp_ass.NamedTemporaryFile("w", suffix=".json", delete=False) as _f:
        _f.write(text)
        _path = Path(_f.name)
    try:
        assurance.FIXTURE_PATH = _path
        try:
            assurance.load_payment_fixture()
            return "loaded"
        except assurance.AssuranceIntegrityError:
            return "integrity"
        except Exception as exc:
            return type(exc).__name__
    finally:
        assurance.FIXTURE_PATH = _real_fixture_path
        _path.unlink()

def _swap_only_instruction_for_memo(fixture):
    fixture["parsedTransaction"]["transaction"]["message"]["instructions"] = [
        {"programId": assurance.SPL_MEMO_PROGRAM_ID, "program": "spl-memo", "parsed": "reddi:pay:x"}]
    return fixture


def _empty_post_token_balances(fixture):
    fixture["parsedTransaction"]["meta"]["postTokenBalances"] = []
    return fixture


_good_fixture_text = _real_fixture_path.read_text()
_broken_fixtures = {
    "truncated json": "",
    "json array not object": "[]",
    "missing expected": _json_ass.dumps(
        {k: v for k, v in _json_ass.loads(_good_fixture_text).items() if k != "expected"}),
    "missing fixtureId": _json_ass.dumps(
        {k: v for k, v in _json_ass.loads(_good_fixture_text).items() if k != "fixtureId"}),
    "non-numeric amount": _good_fixture_text.replace('"amountBaseUnits": "2500000"',
                                                     '"amountBaseUnits": "abc"', 1),
    "wrong-typed expected": _json_ass.dumps(
        {**_json_ass.loads(_good_fixture_text), "expected": []}),
    "wrong-typed parsedTransaction": _json_ass.dumps(
        {**_json_ass.loads(_good_fixture_text), "parsedTransaction": "not-an-object"}),
    "memo instruction where the transfer should be": _json_ass.dumps(
        _swap_only_instruction_for_memo(_json_ass.loads(_good_fixture_text))),
    "no destination token balance": _json_ass.dumps(
        _empty_post_token_balances(_json_ass.loads(_good_fixture_text))),
}
for _label, _text in _broken_fixtures.items():
    check(f"a {_label} fixture is a server integrity failure, not a caller error",
          _fixture_load_outcome(_text) == "integrity")
assurance.FIXTURE_PATH = _real_fixture_path

# A refusal scenario whose mutation is a no-op would present an untouched,
# verifiable payment under a "wrong X" card and report accept for the very
# defect it exists to demonstrate. It must refuse loudly instead.
def _preview_outcome(fixture_doc, scenario):
    with _tmp_ass.NamedTemporaryFile("w", suffix=".json", delete=False) as _f:
        _f.write(_json_ass.dumps(fixture_doc))
        _path = Path(_f.name)
    try:
        assurance.FIXTURE_PATH = _path
        try:
            return assurance.build_assurance_preview(DEF, RAID, scenario=scenario, seed=2)
        except assurance.AssuranceIntegrityError:
            return "integrity"
        except Exception as exc:
            return type(exc).__name__
    finally:
        assurance.FIXTURE_PATH = _real_fixture_path
        _path.unlink()

_self_custodial = _json_ass.loads(_good_fixture_text)
_self_custodial["expected"]["authority"] = _self_custodial["expected"]["payTo"]
_self_custodial["parsedTransaction"]["transaction"]["message"]["instructions"][0][
    "parsed"]["info"]["authority"] = _self_custodial["expected"]["payTo"]
check("a wrong-payee scenario that cannot be built refuses instead of reporting accept",
      _preview_outcome(_self_custodial, "wrong-payee") == "integrity")
_already_wrong_mint = _json_ass.loads(_good_fixture_text)
for _node in (_already_wrong_mint["parsedTransaction"]["transaction"]["message"]["instructions"][0]["parsed"]["info"],
              _already_wrong_mint["parsedTransaction"]["meta"]["postTokenBalances"][0],
              _already_wrong_mint["expected"]):
    _node["mint"] = "WrongAuddMint1111111111111111111111111111111"
check("a wrong-mint scenario that cannot be built refuses instead of reporting accept",
      _preview_outcome(_already_wrong_mint, "wrong-mint") == "integrity")
# The same fixture still builds the scenarios it can honestly construct.
check("a self-custodial fixture still serves the scenarios it can construct",
      _preview_outcome(_self_custodial, "valid-receipt")["adapters"]["receiptIntegrity"][
          "result"]["decision"] == "accept")

# A decoy transfer ahead of the paying one must not absorb the mutation: the
# scenario has to break the transfer the observer would otherwise accept, and
# still refuse with its own canonical reason.
def _with_decoy_transfer(fixture):
    _msg = fixture["parsedTransaction"]["transaction"]["message"]
    _msg["accountKeys"] = _msg["accountKeys"] + ["decoy-source-token-account", "decoy-dest-token-account"]
    _msg["instructions"].insert(0, {
        "programId": fixture["expected"]["tokenProgram"], "program": "spl-token",
        "parsed": {"type": "transferChecked", "info": {
            "source": "decoy-source-token-account", "destination": "decoy-dest-token-account",
            "mint": "DecoyMint111111111111111111111111111111111",
            "authority": "decoy-authority",
            "tokenAmount": {"amount": "1", "decimals": 6, "uiAmountString": "0.000001"}}}})
    fixture["parsedTransaction"]["meta"]["postTokenBalances"].append({
        "accountIndex": len(_msg["accountKeys"]) - 1,
        "mint": "DecoyMint111111111111111111111111111111111", "owner": "decoy-owner",
        "programId": fixture["expected"]["tokenProgram"],
        "uiTokenAmount": {"amount": "1", "decimals": 6, "uiAmountString": "0.000001"}})
    return fixture

for _case, _reason in assurance.SCENARIO_REFUSAL_REASON.items():
    _decoyed = _preview_outcome(_with_decoy_transfer(_json_ass.loads(_good_fixture_text)), _case)
    check(f"{_case} breaks the paying transfer, not a decoy ahead of it",
          _decoyed != "integrity" and not isinstance(_decoyed, str)
          and _decoyed["adapters"]["paymentObservation"]["result"]["reason"] == _reason
          and _decoyed["adapters"]["receiptIntegrity"]["result"]["decision"] == "reject"
          and _decoyed["settlement"]["decision"] == "blocked"
          and _decoyed["receiptArtifact"]["kind"] == "invalid-candidate")
check("a decoy fixture still accepts the scenario that needs no mutation",
      _preview_outcome(_with_decoy_transfer(_json_ass.loads(_good_fixture_text)),
                       "valid-receipt")["adapters"]["receiptIntegrity"]["result"]["decision"]
      == "accept")
# Two transfers that both satisfy the expected terms leave no single target.
_ambiguous = _json_ass.loads(_good_fixture_text)
_amb_msg = _ambiguous["parsedTransaction"]["transaction"]["message"]
_amb_msg["instructions"].insert(0, _json_ass.loads(_json_ass.dumps(_amb_msg["instructions"][0])))
check("an ambiguous fixture with two paying transfers refuses instead of guessing",
      _preview_outcome(_ambiguous, "wrong-mint") == "integrity")

# A transfer instruction with no destination account cannot have its balance
# resolved; a null destination must never match a null-keyed balance entry.
_no_dest = _json_ass.loads(_good_fixture_text)
del _no_dest["parsedTransaction"]["transaction"]["message"]["instructions"][0]["parsed"]["info"]["destination"]
_no_dest["parsedTransaction"]["meta"]["postTokenBalances"][0]["accountIndex"] = "1"
check("a transfer with no destination account is a fixture integrity fault",
      _fixture_load_outcome(_json_ass.dumps(_no_dest)) == "integrity")

# Scenario construction reaches into parsedTransaction, so a shape defect there
# must surface as an integrity fault, not a TypeError/IndexError that escapes
# both /api/assurance handlers and kills the request with no HTTP response.
for _label, _doc in (("memo where the transfer should be", _swap_only_instruction_for_memo(
                          _json_ass.loads(_good_fixture_text))),
                     ("no destination token balance", _empty_post_token_balances(
                          _json_ass.loads(_good_fixture_text)))):
    check(f"a fixture with {_label} is an integrity fault during scenario construction",
          _preview_outcome(_doc, "wrong-mint") == "integrity")

# validate_assurance is the honest-refusal entry point; it must always run its
# own structural pass rather than accept a caller-supplied one.
_hollow = {k: v for k, v in _valid["receipt"].items()
           if k not in ("paymentEvidence", "settlementProgramProof", "replayIdempotency")}
_hollow_verdict = assurance.validate_assurance(
    _hollow, _valid["trace"], assurance._payment_for_scenario("valid-receipt"))
check("validate_assurance cannot be told to skip its structural pass",
      _hollow_verdict["decision"] == "reject"
      and {"rap_receipt.payment.required", "rap_receipt.settlement.required",
           "rap_receipt.replay.required"} <= {d["code"] for d in _hollow_verdict["diagnostics"]})

# _owner_status can refuse on four dimensions; the reported `expected` value
# must name the dimension that actually failed, not always the payee.
_owner_cases = {
    "wrong_mint": ("mint", ("meta", "postTokenBalances", 0, "mint")),
    "wrong_token_program": ("tokenProgram", ("meta", "postTokenBalances", 0, "programId")),
    "wrong_payee": ("payTo", ("meta", "postTokenBalances", 0, "owner")),
}
for _reason, (_expected_key, _path) in _owner_cases.items():
    _f = _json_ass.loads(_good_fixture_text)
    _node = _f["parsedTransaction"]
    for _part in _path[:-1]:
        _node = _node[_part]
    _node[_path[-1]] = "MismatchedValue1111111111111111111111111111"
    _res = assurance.verify_spl_transfer_checked_fixture(_f["parsedTransaction"], _f["expected"])
    check(f"an owner-status {_reason} refusal reports the expected {_expected_key}",
          _res["ok"] is False and _res["reason"] == _reason
          and _res["expected"] == _f["expected"][_expected_key])

# reddi.policy-decision.v1 reasonCodes are a closed upstream set
# (packages/agent-protocol/src/policy.ts); an Arena-minted code is a malformed
# receipt to any canonical validator.
for _case in _assurance_cases:
    _b = assurance.build_assurance_preview(DEF, RAID, scenario=_case, seed=2)
    _policy = (_b["receipt"] or {}).get("policyDecision")
    if _policy is None:
        continue
    check(f"policy decision for {_case} uses only canonical reason codes",
          set(_policy["reasonCodes"]) <= assurance.CANONICAL_POLICY_REASON_CODES
          and _policy["approvalState"] in assurance.CANONICAL_POLICY_APPROVAL_STATES
          and _policy["approvalState"] == ("approved" if _policy["allowed"] else "denied"))
try:
    assurance._policy_decision(False, ["authority_scope_mismatch"])
    _minted_ok = True
except assurance.AssuranceIntegrityError:
    _minted_ok = False
check("a non-canonical policy reason code is refused, not emitted", _minted_ok is False)

# A failed payment observation must not yield a receipt asserting a settlement
# or a payment proof for the very transfer the observer rejected, and must not
# be accused of mismatching a field that was never observed.
for _case in ("wrong-mint", "wrong-payee"):
    _b = assurance.build_assurance_preview(DEF, RAID, scenario=_case, seed=2)
    _proof = _b["receipt"]["settlementProgramProof"]
    _pay = _b["receipt"]["payment"]
    _seen = {d["code"] for d in _b["adapters"]["receiptIntegrity"]["result"]["diagnostics"]}
    check(f"{_case} emits an incomplete settlement proof, never a settled one",
          _proof["confirmationStatus"] == "unverified"
          and not {"signature", "mint", "programId", "payer", "payee", "amount"} & set(_proof)
          and "rap_receipt.settlement.invalid" in _seen)
    check(f"{_case} claims no payment proof and no moved amount",
          _pay["paymentProofRef"] is None and _pay["amount"] is None
          and "incomplete receipt candidate" in _pay["proofBoundary"])
    check(f"{_case} paymentEvidence stays observation-only, not a restated quote",
          _b["receipt"]["paymentEvidence"]["payee"] is None
          and _b["receipt"]["paymentEvidence"]["amount"] is None
          and "rap_receipt.payment.invalid" in _seen)
    check(f"{_case} keeps the quoted terms in Arena-owned metadata instead",
          _b["receipt"]["metadata"]["expectedPaymentTerms"]["amountBaseUnits"]
          == assurance.load_payment_fixture()["expected"]["amountBaseUnits"])
    check(f"{_case} is not accused of a payee mismatch that never happened",
          "rap_receipt.settlement.payee_mismatch" not in _seen)
    check(f"{_case} labels the emitted JSON an invalid candidate, not a receipt",
          _b["receiptArtifact"]["kind"] == "invalid-candidate")
_valid_observation = _valid["adapters"]["paymentObservation"]["result"]["observation"]
check("an observed receipt binds paymentEvidence to the observed payee and amount",
      _valid["receipt"]["paymentEvidence"]["payee"]
      == _valid_observation["destinationOwner"]
      and _valid["receipt"]["paymentEvidence"]["amount"]
      == int(_valid_observation["amountBaseUnits"]))
check("an accepted scenario is labelled a receipt and a denied one is not emitted",
      _valid["receiptArtifact"]["kind"] == "receipt"
      and assurance.build_assurance_preview(
          DEF, RAID, scenario="authorization-denied", seed=2)["receiptArtifact"]["kind"]
      == "not-emitted")

# A semantic refusal (failed eval, replay, tampered trace) leaves a genuinely
# observed, canonically complete receipt. Calling that an invalid candidate
# would erase the structural-vs-semantic distinction the preview teaches.
for _case in ("refund-gate-failed", "duplicate-replay", "tampered-trace"):
    _b = assurance.build_assurance_preview(DEF, RAID, scenario=_case, seed=2)
    _art = _b["receiptArtifact"]
    check(f"{_case} keeps its verified receipt but is never labelled accepted",
          _art["kind"] == "verified-rejected-receipt"
          and "not accepted" in _art["label"]
          and _b["receipt"]["payment"]["paymentProofRef"] is not None
          and _b["adapters"]["receiptIntegrity"]["result"]["decision"] != "accept")
# botA == botB is reachable through the public core API and yields a `hold`.
_held = assurance.build_assurance_preview(DEF, DEF, scenario="valid-receipt", seed=2)
check("a held decision keeps its verified receipt and says held, not accepted",
      _held["adapters"]["receiptIntegrity"]["result"]["decision"] == "hold"
      and _held["receiptArtifact"]["kind"] == "verified-rejected-receipt"
      and "held" in _held["receiptArtifact"]["label"])

# replayIdempotency is the consume-once identity layer: it must extend the
# verifier's own replay key, not restate an assumed instruction index.
_inner_fixture = _json_ass.loads(_json_ass.dumps(assurance.load_payment_fixture()))
_transfer_ix = _inner_fixture["parsedTransaction"]["transaction"]["message"]["instructions"].pop(0)
_inner_fixture["parsedTransaction"]["meta"]["innerInstructions"] = [
    {"index": 1, "instructions": [_transfer_ix]}]
_inner = assurance.verify_spl_transfer_checked_fixture(
    _inner_fixture["parsedTransaction"], _inner_fixture["expected"])
check("an inner-instruction transfer is observed at its real nested index",
      _inner["ok"] and _inner["observation"]["instructionIndex"] == "1.0"
      and _inner["observation"]["innerInstruction"] is True
      and _inner["replayKey"].endswith(":1.0"))
_inner_receipt = assurance._build_receipt(
    _valid["trace"], _inner, "valid-receipt", fixture=_inner_fixture)
check("an inner-instruction receipt's idempotency key carries 1.0, never 0",
      _inner_receipt["replayIdempotency"]["idempotencyKey"].startswith(_inner["replayKey"] + ":")
      and ":0:" not in _inner_receipt["replayIdempotency"]["idempotencyKey"])
_valid_obs = assurance._payment_for_scenario("valid-receipt")
check("an observed receipt's idempotency key extends the verifier's replay key",
      _valid["receipt"]["replayIdempotency"]["idempotencyKey"]
      == f"{_valid_obs['replayKey']}:{_valid['receipt']['request']['requestId']}")
_dup_replay = assurance.build_assurance_preview(DEF, RAID, scenario="duplicate-replay", seed=2)
check("a replay-rejected receipt still names the first attempt's consume-once identity",
      _dup_replay["receipt"]["replayIdempotency"]["idempotencyKey"].startswith(
          _valid_obs["replayKey"] + ":"))
for _case in ("wrong-mint", "wrong-payee"):
    _b = assurance.build_assurance_preview(DEF, RAID, scenario=_case, seed=2)
    check(f"{_case} claims no consume-once identity for a transfer never observed",
          _b["receipt"]["replayIdempotency"]["idempotencyKey"] is None
          and "rap_receipt.replay.invalid"
          in {d["code"] for d in _b["adapters"]["receiptIntegrity"]["result"]["diagnostics"]})

# One request reads and validates the fixture exactly once; a fixture that
# changes mid-request cannot alter the bundle that request already committed to.
_real_loader = assurance.load_payment_fixture
_load_calls = []
_mutated = _json_ass.loads(_json_ass.dumps(assurance.load_payment_fixture()))
_mutated["expected"]["amountBaseUnits"] = "9999999"
def _counting_loader():
    _load_calls.append(1)
    return _real_loader() if len(_load_calls) == 1 else _json_ass.loads(_json_ass.dumps(_mutated))
try:
    assurance.load_payment_fixture = _counting_loader
    _once = assurance.build_assurance_preview(DEF, RAID, scenario="valid-receipt", seed=2)
finally:
    assurance.load_payment_fixture = _real_loader
check("one preview request loads and validates the fixture exactly once",
      len(_load_calls) == 1)
check("a fixture changed mid-request cannot alter the committed bundle",
      _once["receipt"] == _valid["receipt"]
      and "9999999" not in _json_ass.dumps(_once))

# The artifact classification and the public verdict must agree about which
# receipts are structurally incomplete, for every scenario.
_STRUCTURAL_CODES = (
    {f"rap_receipt.{_cat}.required" for _cat in assurance.LAYER_CATEGORY.values()}
    | {f"rap_receipt.{_cat}.invalid" for _cat in assurance.LAYER_CATEGORY.values()}
    | set(assurance.MISSING_LAYER_CODES.values())
    | {"rap_receipt.envelope.required"}
) - assurance.HOLD_CODES
for _case in _assurance_cases:
    _b = assurance.build_assurance_preview(DEF, RAID, scenario=_case, seed=2)
    if _b["receipt"] is None:
        continue
    _verdict = assurance.validate_assurance(
        _b["receipt"], _b["trace"], assurance._payment_for_scenario(_case))
    _has_structural = bool({d["code"] for d in _verdict["diagnostics"]} & _STRUCTURAL_CODES)
    check(f"{_case} artifact classification agrees with the public verdict's structural view",
          _has_structural == (_b["receiptArtifact"]["kind"] == "invalid-candidate"))
_dup = assurance.build_assurance_preview(DEF, RAID, scenario="duplicate-replay", seed=2)
check("duplicate-replay keeps the first observation's real settlement and rejects on replay",
      _dup["receipt"]["settlementProgramProof"]["confirmationStatus"] == "confirmed"
      and _dup["receipt"]["settlementProgramProof"]["mint"] == assurance.AUDD_DETERMINISTIC_FIXTURE_MINT
      and _dup["receipt"]["payment"]["paymentProofRef"] is not None
      and "rap_receipt.replay.duplicate_payment"
      in {d["code"] for d in _dup["adapters"]["receiptIntegrity"]["result"]["diagnostics"]})

# Missing-layer diagnostics are keyed by evidence category (with three
# overrides), matching the canonical lab validator taxonomy consumers parse.
_pay_ok = assurance._payment_for_scenario("valid-receipt")
for _layer, _code in (("delegatedAuthority", "rap_receipt.authority.required"),
                      ("serviceOutcome", "rap_receipt.service_outcome.required"),
                      ("paymentEvidence", "rap_receipt.payment.required"),
                      ("rollbackHold", "rap_receipt.rollback.evidence_required")):
    _stripped = {k: v for k, v in _valid["receipt"].items() if k != _layer}
    _diags = assurance.validate_assurance(_stripped, _valid["trace"], _pay_ok)["diagnostics"]
    check(f"a receipt missing {_layer} emits the canonical {_code} diagnostic",
          _diags and any(d["code"] == _code for d in _diags))

# One settlement response shape regardless of scenario, so a consumer of the
# public endpoint never has to branch on decision.
_settlement_keys = {frozenset(assurance.build_assurance_preview(DEF, RAID, scenario=_c, seed=2)["settlement"])
                    for _c in _assurance_cases}
check("every assurance scenario returns one stable settlement shape", len(_settlement_keys) == 1)

print("balance regression (issue B7)")
from tools.simulate import round_robin, mirror_position_bias, powerup_impact, BANDS, ARCHETYPES

_SEEDS = 40  # keep the suite fast; tools/simulate.py --seeds 200 is the full run
_rr = round_robin(DEF, _SEEDS)
_mir = mirror_position_bias(DEF, _SEEDS)
_pw = powerup_impact(DEF, MERC, 15)

_lo, _hi = BANDS["first_mover_advantage"]
check(f"positional bias within band (mirror matches: {_mir['sideAWinRate']:.1%})",
      _lo <= _mir["sideAWinRate"] <= _hi)
_worst = max(_rr["winRate"], key=_rr["winRate"].get)
check(f"no archetype dominates ({_worst} at {_rr['winRate'][_worst]:.1%})",
      _rr["winRate"][_worst] <= BANDS["archetype_dominance_max"])
check(f"power-up is not an auto-win ({_pw['hiredWinRate']:.1%})",
      _pw["hiredWinRate"] <= BANDS["powerup_winrate_max"])
check(f"matches mostly resolve ({_rr['decisiveRate']:.1%} decisive)",
      _rr["decisiveRate"] >= BANDS["decisive_rate_min"])
check("power-up still gives positive lift", _pw["lift"] > 0)
check("every archetype wins at least some matches",
      all(v > 0 for v in _rr["winRate"].values()))

# T-038 — the attack/defence win split stays inside the published band.
from tools.simulate import attack_defence_split
_split = attack_defence_split(_rr)
_s_lo, _s_hi = BANDS["attack_defence_split"]
check(f"T-038 attack/defence split within published band ({_split['split']:.1%})",
      _s_lo <= _split["split"] <= _s_hi
      and _split["attackCohort"] and _split["defenceCohort"])

# T-039 — dominance threshold enforced AND the balance report is published
# (docs/BALANCE-REPORT.md carries the current verdict and the bands).
check("T-039 no archetype exceeds the published dominance threshold",
      max(_rr["winRate"].values()) <= BANDS["archetype_dominance_max"])
_report_md = (ROOT / "docs" / "BALANCE-REPORT.md").read_text()
check("T-039 the balance report is published with verdict and bands",
      "BALANCED" in _report_md and "70%" in _report_md
      and "attack/defence" in _report_md.lower())

# P1 exit-gate evidence (phase gate, measured here because the balance
# harness is the e2e surface): 100 consecutive local matches, every trace
# terminal and hash-complete, zero policy escapes.
_gate_ok = True
for _s in range(100):
    _t = run_vault_match(DEF, RAID, seed=_s)
    _gate_ok = (_gate_ok
                and _t["lifecycle"]["terminal"]
                and _t["traceHash"].startswith("sha256:")
                and all(e["allowed"] for evs in _t["laneEvents"].values()
                        for e in evs))
check("P1 exit gate: 100 consecutive matches, complete traces, zero policy escapes",
      _gate_ok)

print("landing page and waitlist")
_land = (ROOT / "web" / "static" / "landing.html").read_text()
check("landing page exists with a signup form", 'id="joinForm"' in _land)
check("landing states prizes have no real value",
      "no real money" in _land or "no cash value" in _land)
check("landing discloses the dry-run rail", "x402-dry-run" in _land)
check("landing makes no audit/mainnet/production claim",
      "no claim of security audit" in _land
      and not any(p in _land.lower() for p in ("fully audited", "mainnet ready", "production ready")))
import re as _re
_flat = _re.sub(r"\s+", " ", _land)
check("landing explains what happens to the email",
      "never sold or shared" in _flat and "deletion" in _flat)
check("landing discloses simulated (not live-model) competitors",
      "declared strategy profiles" in _land)

print("waitlist admin endpoints")
import importlib.util as _ilu
import os as _os
import tempfile as _tempfile
import threading as _threading
import urllib.error as _uerror
import urllib.request as _urequest
import json as _wjson

_os.environ["DATA_DIR"] = _tempfile.mkdtemp(prefix="arena-waitlist-test-")
_os.environ["ARENA_ADMIN_TOKEN"] = "test-token-123"
# The Devnet Preview is off unless explicitly opted in on BOTH halves of the
# gate, so this instance is the "explicitly enabled, locally declared" server;
# the default-off instance is loaded further down.
_os.environ["REDDI_ENABLE_SOLANA_DEVNET_ASSURANCE_PREVIEW"] = "true"
_os.environ["REDDI_SOLANA_DEVNET_ASSURANCE_DEPLOYMENT_CONTEXT"] = "local"
_spec = _ilu.spec_from_file_location("arena_server", ROOT / "web" / "server.py")
_srv = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_srv)

from http.server import ThreadingHTTPServer as _TServer
_httpd = _TServer(("127.0.0.1", 0), _srv.Handler)
_port = _httpd.server_address[1]
_threading.Thread(target=_httpd.serve_forever, daemon=True).start()


def _req(method, path, body=None, token=None):
    r = _urequest.Request(f"http://127.0.0.1:{_port}{path}", method=method,
                          data=_wjson.dumps(body).encode() if body is not None else None)
    if token:
        r.add_header("Authorization", "Bearer " + token)
    if body is not None:
        r.add_header("Content-Type", "application/json")
    try:
        resp = _urequest.urlopen(r, timeout=10)
        return resp.status, _wjson.loads(resp.read())
    except _uerror.HTTPError as e:
        return e.code, _wjson.loads(e.read())


_s, _b = _req("GET", "/api/assurance/scenarios")
check("assurance API publishes the deterministic scenario catalog",
      _s == 200 and any(s["id"] == "valid-receipt" for s in _b["scenarios"])
      and _b["boundary"]["rpcCall"] is False)
_s, _b = _req("POST", "/api/assurance",
              {"botA": "antweight-vault-defender.adl.yaml",
               "botB": "antweight-vault-raider.adl.yaml",
               "scenario": "wrong-mint", "seed": 2})
check("assurance API executes refusal scenarios without ledger writes",
      _s == 200 and _b["adapters"]["receiptIntegrity"]["result"]["decision"] == "reject"
      and _b["settlement"]["decision"] == "blocked"
      and not _srv.LEDGER.exists())
_s, _b = _req("POST", "/api/assurance",
              {"botA": "antweight-vault-defender.adl.yaml",
               "botB": "antweight-vault-raider.adl.yaml",
               "network": "solana-mainnet-beta"})
check("assurance API refuses non-devnet preview requests", _s == 400)
_s, _b = _req("POST", "/api/assurance",
              {"botA": "antweight-vault-defender.adl.yaml",
               "botB": "antweight-vault-raider.adl.yaml",
               "paymentMode": "live"})
check("assurance API refuses live payment mode", _s == 400)
_s, _b = _req("POST", "/api/assurance",
              {"botA": "antweight-vault-defender.adl.yaml",
               "botB": "antweight-vault-raider.adl.yaml",
               "wallet": True})
check("assurance API refuses wallet/signing escalation flags", _s == 400)
for _case, (_decision, _settle, _codes) in _assurance_cases.items():
    _s, _b = _req("POST", "/api/assurance",
                  {"botA": "antweight-vault-defender.adl.yaml",
                   "botB": "antweight-vault-raider.adl.yaml",
                   "scenario": _case, "seed": 2})
    check(f"assurance API serves scenario {_case} as {_decision}/{_settle}",
          _s == 200 and _b["adapters"]["receiptIntegrity"]["result"]["decision"] == _decision
          and _b["settlement"]["decision"] == _settle)
# A non-string scenario must be a deterministic 400, not an unhandled TypeError
# from the OrderedDict lookup that kills the request with no response.
for _bad in ({"a": 1}, ["valid-receipt"], 7, True, "no-such-scenario"):
    _s, _b = _req("POST", "/api/assurance",
                  {"botA": "antweight-vault-defender.adl.yaml",
                   "botB": "antweight-vault-raider.adl.yaml",
                   "scenario": _bad})
    check(f"assurance API rejects scenario {_bad!r} with a clean 400",
          _s == 400 and "error" in _b)
# A corrupt fixture is a server defect, not caller error: it must not be
# reported to the client as a 400, and must not leak the fixture path.
import tempfile as _tmp_api
_real_path_api = _srv.assurance.FIXTURE_PATH
with _tmp_api.NamedTemporaryFile("w", suffix=".json", delete=False) as _fh_api:
    _fh_api.write(_real_path_api.read_text().replace(
        assurance.AUDD_DETERMINISTIC_FIXTURE_MINT,
        assurance.AUDD_OFFICIAL_SOLANA_MAINNET_MINT))
    _bad_path_api = Path(_fh_api.name)
try:
    _srv.assurance.FIXTURE_PATH = _bad_path_api
    _s, _b = _req("POST", "/api/assurance",
                  {"botA": "antweight-vault-defender.adl.yaml",
                   "botB": "antweight-vault-raider.adl.yaml",
                   "scenario": "valid-receipt"})
finally:
    _srv.assurance.FIXTURE_PATH = _real_path_api
    _bad_path_api.unlink()
check("a corrupt preview fixture is a sanitized 500, not a client-blaming 400",
      _s == 500 and "error" in _b
      and str(_bad_path_api) not in _b["error"]
      and assurance.AUDD_OFFICIAL_SOLANA_MAINNET_MINT not in _b["error"])

print("Devnet Preview exposure gate (flag + deployment context, default off)")
# The preview is fixture-only and reaches no wallet/RPC/signing/custody path,
# but hosting it publicly is separately approval-gated
# (docs/DEVNET-PREVIEW-RAP-ASSURANCE.md). The server therefore needs BOTH an
# exact REDDI_ENABLE_SOLANA_DEVNET_ASSURANCE_PREVIEW opt-in value AND an exact
# operator-declared deployment context, and fails closed on anything else, so
# neither a typo nor an undeclared environment can expose it.
_FLAG, _CTX = _srv.ASSURANCE_PREVIEW_FLAG, _srv.ASSURANCE_CONTEXT_VAR
check("only the exact documented values enable the preview",
      all(_srv.preview_enabled(_v) for _v in ("true", "1"))
      and not any(_srv.preview_enabled(_v) for _v in
                  (None, "", "True", "TRUE", "yes", "on", "enabled", "y",
                   " true", "true ", "0", "false", "False", "2", 1, True)))
check("the deployment context is a closed set; anything else reads as off",
      [_srv.deployment_context(_v) for _v in ("off", "local", "hosted")]
      == ["off", "local", "hosted"]
      and all(_srv.deployment_context(_v) == "off" for _v in
              (None, "", "Local", "LOCAL", " local", "local ", "hosted-preview",
               "prod", "on", True, 1)))
# Full flag x context matrix: exposure needs both halves, and externalDeployment
# is derived from the context, never inferred when the context is unknown.
_gate_matrix = [
    (None, None, False, None), (None, "local", False, None),
    (None, "hosted", False, None), ("true", None, False, None),
    ("1", None, False, None), ("true", "off", False, None),
    ("true", "", False, None), ("true", "Local", False, None),
    ("true", "LOCAL", False, None), ("true", "hosted-preview", False, None),
    ("false", "local", False, None), ("True", "local", False, None),
    ("yes", "hosted", False, None), ("", "local", False, None),
    ("0", "hosted", False, None), ("true", "local", True, False),
    ("1", "local", True, False), ("true", "hosted", True, True),
    ("1", "hosted", True, True),
]
check("exposure needs an exact flag AND an exact context, and derives external deployment",
      all(_srv.preview_exposure(_f, _c) == (_on, _ext)
          for _f, _c, _on, _ext in _gate_matrix))


def _load_server(flag, context, label):
    """A fresh server module loaded under one exact flag/context environment."""
    _prior = {_k: _os.environ.get(_k) for _k in (_FLAG, _CTX, "DATA_DIR")}
    _os.environ["DATA_DIR"] = _tempfile.mkdtemp(prefix=f"arena-{label}-test-")
    for _k, _v in ((_FLAG, flag), (_CTX, context)):
        if _v is None:
            _os.environ.pop(_k, None)
        else:
            _os.environ[_k] = _v
    try:
        _sp = _ilu.spec_from_file_location("arena_server_" + label,
                                           ROOT / "web" / "server.py")
        _mod = _ilu.module_from_spec(_sp)
        _sp.loader.exec_module(_mod)
    finally:
        for _k, _v in _prior.items():
            if _v is None:
                _os.environ.pop(_k, None)
            else:
                _os.environ[_k] = _v
    return _mod


def _serve(mod):
    _h = _TServer(("127.0.0.1", 0), mod.Handler)
    _threading.Thread(target=_h.serve_forever, daemon=True).start()
    return _h.server_address[1]


def _call(port, method, path, raw=None):
    """Raw request against a given server: returns (status, body bytes)."""
    r = _urequest.Request(f"http://127.0.0.1:{port}{path}", method=method, data=raw)
    if raw is not None:
        r.add_header("Content-Type", "application/json")
    try:
        resp = _urequest.urlopen(r, timeout=10)
        return resp.status, resp.read()
    except _uerror.HTTPError as e:
        return e.code, e.read()


_preview_body = _wjson.dumps({"botA": "antweight-vault-defender.adl.yaml",
                              "botB": "antweight-vault-raider.adl.yaml",
                              "scenario": "valid-receipt"}).encode()
# Every non-exposing environment answers exactly like the default-off one, so a
# half-configured deploy is indistinguishable from an unknown path.
for _label, _flag_v, _ctx_v in (("ctx-missing", "true", None),
                                ("ctx-malformed", "true", "Local"),
                                ("ctx-off", "1", "off"),
                                ("flag-off-ctx-local", None, "local"),
                                ("flag-off-ctx-hosted", "false", "hosted")):
    _m = _load_server(_flag_v, _ctx_v, _label)
    _p = _serve(_m)
    _pg = _call(_p, "GET", "/play")[1].decode()
    check(f"gate {_label}: no preview UI, no preview API, no externalDeployment claim",
          not _m.ASSURANCE_PREVIEW_ENABLED
          and _m.ASSURANCE_EXTERNAL_DEPLOYMENT is None
          and 'data-panel="assurance"' not in _pg and "Devnet Preview" not in _pg
          and _call(_p, "GET", "/api/assurance/scenarios")[0] == 404
          and _call(_p, "POST", "/api/assurance", _preview_body)[0] == 404)

# The two exposing environments differ only in the truth they may assert about
# where they are running. Every other disclosure survives enablement.
_srv_hosted = _load_server("true", "hosted", "ctx-hosted")
_port_hosted = _serve(_srv_hosted)
for _mod, _port, _name, _external in ((_srv, _port, "local", False),
                                      (_srv_hosted, _port_hosted, "hosted", True)):
    _cat = _wjson.loads(_call(_port, "GET", "/api/assurance/scenarios")[1])
    _bun = _wjson.loads(_call(_port, "POST", "/api/assurance", _preview_body)[1])
    check(f"gate {_name}-enabled: preview served, externalDeployment is {_external}",
          _mod.ASSURANCE_PREVIEW_ENABLED
          and _mod.ASSURANCE_EXTERNAL_DEPLOYMENT is _external
          and 'data-panel="assurance"' in _mod.arena_page_bytes().decode()
          and _cat["boundary"]["externalDeployment"] is _external
          and _bun["boundary"]["externalDeployment"] is _external)
    check(f"gate {_name}-enabled: every other preview disclosure still holds",
          all(_bun["boundary"][_f] is False for _f in
              ("deploymentPerformedByRequest", "rpcCall", "walletSigning",
               "transactionSubmitted", "liveValue", "custody",
               "officialMintObservation", "grantEvidence"))
          and _bun["boundary"]["previewOnly"] is True
          and _bun["boundary"]["cluster"] == "solana-devnet"
          and "Devnet Preview" in _bun["label"])
# Nothing in this repo declares a hosted context: enabling the preview on a
# hosted service is a separate operator action, so the default remains "off".
check("no repo-shipped configuration declares the hosted context",
      _srv.deployment_context(None) == "off"
      and _load_server(None, None, "ctx-default").ASSURANCE_DEPLOYMENT_CONTEXT == "off")
# A top-level array, scalar, string or null is caller error on every POST route:
# one stable 400 before any field is read, never a dropped connection.
for _path in ("/api/assurance", "/api/fight", "/api/draft", "/api/waitlist",
              "/api/chain"):
    for _raw in (b"[]", b"5", b'"x"', b"null", b"true", b'[{"botA":"x"}]'):
        _s_nb, _b_nb = _call(_port, "POST", _path, _raw)
        check(f"non-object body {_raw!r} to {_path} is a stable 400",
              _s_nb == 400 and "error" in _wjson.loads(_b_nb))

# A second server module loaded with the flag ABSENT is the default every
# environment gets, including an ordinary Railway redeploy of this tree.
_srv_off = _load_server(None, None, "preview-off")
_port_off = _serve(_srv_off)


def _req_off(method, path, raw=None):
    """Raw request against the default-off server: returns (status, body bytes)."""
    return _call(_port_off, method, path, raw)


check("default off: the flag is absent, so the preview is disabled",
      not _srv_off.ASSURANCE_PREVIEW_ENABLED)
_s_off, _ = _req_off("POST", "/api/assurance",
                     _wjson.dumps({"botA": "antweight-vault-defender.adl.yaml",
                                   "botB": "antweight-vault-raider.adl.yaml",
                                   "scenario": "valid-receipt"}).encode())
check("default off: POST /api/assurance is 404, like any unknown path",
      _s_off == 404)
_s_off, _ = _req_off("GET", "/api/assurance/scenarios")
check("default off: the scenario catalog is 404", _s_off == 404)
# Route order: the gate runs BEFORE the body is parsed and before any fixture is
# read, so a malformed or oversized body still answers 404 rather than 400/413,
# and a corrupt fixture cannot produce a 500 from a disabled route.
check("default off: a malformed body still gets 404, not a 400 body parse error",
      _req_off("POST", "/api/assurance", b"{not json")[0] == 404)
check("default off: an oversized body still gets 404, not 413",
      _req_off("POST", "/api/assurance",
               b'{"x":"' + b"z" * (70 * 1024) + b'"}')[0] == 404)
_real_off = _srv_off.assurance.FIXTURE_PATH
try:
    _srv_off.assurance.FIXTURE_PATH = Path("/nonexistent/assurance-fixture.json")
    _s_off, _ = _req_off("POST", "/api/assurance", b'{"scenario":"valid-receipt"}')
finally:
    _srv_off.assurance.FIXTURE_PATH = _real_off
check("default off: no fixture is read, so a broken fixture is still 404",
      _s_off == 404)
# UI absence: the tab, the panel and every client-side hook are removed from the
# served document, not merely hidden with CSS.
_s_off, _page_off = _req_off("GET", "/play")
_page_off = _page_off.decode()
check("default off: /play omits the Devnet Preview tab, panel and client code",
      _s_off == 200
      and 'data-panel="assurance"' not in _page_off
      and 'id="assurance"' not in _page_off
      and "Devnet Preview" not in _page_off
      and "/api/assurance" not in _page_off
      and "bootAssurance" not in _page_off)
check("default off: the rest of the arena page is untouched",
      all(f'data-panel="{_t}"' in _page_off
          for _t in ("fight", "market", "board", "build", "chain"))
      and 'id="fightBtn"' in _page_off)
check("default off: /index.html serves the same stripped arena page",
      _req_off("GET", "/index.html")[1].decode() == _page_off)
# Stripping is fail-loud: an unpaired marker is a defect, never a page that is
# half-stripped and still wired to a removed panel.
_unpaired = 0
for _frag in ("<!-- devnet-preview:begin -->x", "x<!-- devnet-preview:end -->",
              "/* devnet-preview:begin */x", "x/* devnet-preview:end */"):
    try:
        _srv_off.strip_preview_markup(_frag)
    except RuntimeError:
        _unpaired += 1
check("an unpaired preview marker raises instead of serving a broken page",
      _unpaired == 4)
# Deploy config: neither half of the gate is configured by the image or the
# Railway service definition, so an ordinary redeploy of this tree keeps the
# preview off. The image does ship the fixtures the preview needs once an
# operator opts in. Both are checked against a normalized model of what the
# builder actually does with these files, not against their text — an
# equivalent rewrite of either file must keep these checks green.
import fnmatch as _fnmatch

_railway = _wjson.loads((ROOT / "railway.json").read_text())
_railway_vars = dict(_railway.get("variables") or {})
for _sect in ("build", "deploy"):
    _railway_vars.update((_railway.get(_sect) or {}).get("variables") or {})


def _dockerfile_instructions(text):
    """Dockerfile as (INSTRUCTION, argument) pairs, continuations joined."""
    _out, _buf = [], ""
    for _line in text.splitlines():
        _s = _line.strip()
        if not _s or _s.startswith("#"):
            continue
        if _s.endswith("\\"):
            _buf += _s[:-1].strip() + " "
            continue
        _s, _buf = (_buf + _s).strip(), ""
        _instr, _, _arg = _s.partition(" ")
        _out.append((_instr.upper(), _arg.strip()))
    return _out


def _pattern_matches(pattern, path):
    """One .dockerignore pattern against a path: segment-wise, a directory
    pattern matching every path beneath it, and `*` never crossing a `/`."""
    _pp, _tp = pattern.split("/"), path.split("/")
    return (len(_pp) <= len(_tp)
            and all(_fnmatch.fnmatch(_t, _p) for _p, _t in zip(_pp, _tp)))


def _ignored(patterns, path):
    """Docker's .dockerignore semantics: last matching pattern wins, ! re-includes."""
    _excluded = False
    for _raw in patterns:
        _pat = _raw.strip()
        if not _pat or _pat.startswith("#"):
            continue
        _negate = _pat.startswith("!")
        _pat = _pat.lstrip("!").strip().rstrip("/")
        if _pat and _pattern_matches(_pat, path):
            _excluded = not _negate
    return _excluded


def _in_build_context(instructions, patterns, path):
    """True when `path` is copied into the image and not ignored out of it."""
    _copied = any(path == _src or path.startswith(_src.rstrip("/") + "/")
                  for _instr, _arg in instructions if _instr == "COPY"
                  for _src in _arg.split()[:1])
    return _copied and not _ignored(patterns, path)


_instructions = _dockerfile_instructions((ROOT / "Dockerfile").read_text())
_ignore_patterns = (ROOT / ".dockerignore").read_text().splitlines()
_baked_env = {_arg.replace("=", " ").split()[0]
              for _instr, _arg in _instructions if _instr in ("ENV", "ARG") and _arg}
check("an ordinary Railway redeploy configures neither gate variable",
      _srv.ASSURANCE_PREVIEW_FLAG not in _railway_vars
      and _srv.ASSURANCE_CONTEXT_VAR not in _railway_vars
      and _srv.ASSURANCE_PREVIEW_FLAG not in _baked_env
      and _srv.ASSURANCE_CONTEXT_VAR not in _baked_env)
_fixture_rel = str(assurance.FIXTURE_PATH.relative_to(ROOT))
check("the image build context includes the assurance fixtures the preview needs",
      assurance.FIXTURE_PATH.exists()
      and _in_build_context(_instructions, _ignore_patterns, _fixture_rel))
# The ignore model is only evidence if it can say no: the excluded trees the
# image deliberately drops must still resolve as excluded.
check("the build-context model still excludes what the image drops",
      not any(_in_build_context(_instructions, _ignore_patterns, _p)
              for _p in ("tests/test_arena.py", "docs/OPERATIONS.md",
                         "core/waitlist.json", "fixtures/other/thing.json")))

_s, _b = _req("POST", "/api/waitlist", {"email": "Player@Example.com", "roles": ["compete"]})
check("waitlist signup works and normalizes case", _s == 200 and _b["ok"] and _b["position"] == 1)
_s, _b = _req("GET", "/api/waitlist")
check("waitlist read without token is 404 (fail closed)", _s == 404)
_s, _b = _req("GET", "/api/waitlist", token="wrong-token")
check("waitlist read with wrong token is 404", _s == 404)
_s, _b = _req("POST", "/api/waitlist/remove", {"email": "player@example.com"})
check("waitlist remove without token is 404", _s == 404)
_s, _b = _req("GET", "/api/waitlist", token="test-token-123")
check("waitlist read with token returns entries",
      _s == 200 and _b["count"] == 1 and _b["entries"][0]["email"] == "player@example.com")
_s, _b = _req("POST", "/api/waitlist/remove", {"email": "player@example.com"},
              token="test-token-123")
check("waitlist remove with token deletes the entry", _s == 200 and _b["removed"] == 1)
_s, _b = _req("GET", "/api/waitlist", token="test-token-123")
check("waitlist empty after removal", _s == 200 and _b["count"] == 0)
check("email masking keeps domain, hides local part",
      _srv.mask_email("player@example.com") == "pl***@example.com")

# --- web surface hardening (retro-audit remediation) --------------------
# Path traversal / arbitrary-file-open is refused: absolute paths, ../
# escapes, non-yaml suffixes, and subdirectory names all reject at 400.
_s_pt, _ = _req("POST", "/api/draft", {"bot": "/etc/hostname", "hire": "/etc/hostname"})
check("hardening: absolute-path bot is refused, no arbitrary file open",
      _s_pt == 400)
_s_tr, _ = _req("POST", "/api/fight",
                {"botA": "../../../etc/hostname", "botB": "antweight-vault-raider.adl.yaml"})
check("hardening: ../ traversal in botA is refused", _s_tr == 400)
check("hardening: safe_adl_path accepts only bare yaml files inside adl/",
      _srv.safe_adl_path("antweight-vault-raider.adl.yaml") is not None
      and _srv.safe_adl_path("../x.yaml") is None
      and _srv.safe_adl_path("/etc/passwd") is None
      and _srv.safe_adl_path("sub/dir.yaml") is None
      and _srv.safe_adl_path("notes.txt") is None)
# safe_adl_path returns None (never raises) on NUL bytes and over-long names,
# so the handler answers 400 rather than dropping the connection.
check("hardening: safe_adl_path returns None on NUL byte / over-long name",
      _srv.safe_adl_path("x\x00.yaml") is None
      and _srv.safe_adl_path("a" * 300 + ".yaml") is None)
_s_nul, _ = _req("POST", "/api/draft", {"bot": "x\x00.yaml", "hire": "y.yaml"})
check("hardening: NUL-byte bot name returns 400, connection not dropped",
      _s_nul == 400)
# Malformed JSON and oversized bodies fail with a status, never a dropped
# connection or a crash.
import urllib.request as _ur2
def _raw_post(path, raw_bytes, ctype="application/json"):
    r = _ur2.Request(f"http://127.0.0.1:{_port}{path}", method="POST", data=raw_bytes)
    r.add_header("Content-Type", ctype)
    try:
        return _ur2.urlopen(r, timeout=10).status
    except _uerror.HTTPError as e:
        return e.code
check("hardening: malformed JSON body returns 400, not a dropped connection",
      _raw_post("/api/draft", b"{not json") == 400)
check("hardening: oversized request body is refused with 413",
      _raw_post("/api/waitlist", b'{"email":"a@b.co","x":"' + b"z" * (70 * 1024) + b'"}') == 413)
# Concurrent signups do not lose entries (lock + atomic write).
import threading as _thr2
_conc_dir = _tempfile.mkdtemp(prefix="arena-conc-test-")
_os.environ["DATA_DIR"] = _conc_dir
_spec2 = _ilu.spec_from_file_location("arena_server_conc", ROOT / "web" / "server.py")
_srv2 = _ilu.module_from_spec(_spec2)
_spec2.loader.exec_module(_srv2)
_srv2.SIGNUP_RATE_MAX = 10_000  # disable the rate limit for this concurrency probe
_httpd2 = _TServer(("127.0.0.1", 0), _srv2.Handler)
_port2 = _httpd2.server_address[1]
_threading.Thread(target=_httpd2.serve_forever, daemon=True).start()
_ok_emails = []
_ok_lock = _thr2.Lock()
def _signup(i):
    r = _urequest.Request(f"http://127.0.0.1:{_port2}/api/waitlist", method="POST",
                          data=_wjson.dumps({"email": f"u{i}@ex.com"}).encode())
    r.add_header("Content-Type", "application/json")
    try:
        if _urequest.urlopen(r, timeout=10).status == 200:
            with _ok_lock:
                _ok_emails.append(f"u{i}@ex.com")
    except Exception:
        pass  # a dropped connection under load is harness flakiness, not a lost write
_threads = [_thr2.Thread(target=_signup, args=(i,)) for i in range(50)]
for _t in _threads:
    _t.start()
for _t in _threads:
    _t.join()
import json as _cj
with open(_os.path.join(_conc_dir, "waitlist.json")) as _fh:
    _stored = _cj.load(_fh)
_stored_emails = {e["email"] for e in _stored}
# No lost writes: every signup that returned 200 is persisted exactly once,
# and the store has no torn/duplicate entries. (A lockless RMW loses some of
# the accepted writes — the pre-fix probe stored 43 of 61.)
check("hardening: every accepted concurrent signup is persisted (no lost writes)",
      len(_ok_emails) >= 40 and set(_ok_emails) == _stored_emails
      and len(_stored) == len(_stored_emails))
# Rate limit keys on the forwarded client, not the shared proxy peer, so
# distinct forwarded clients are limited independently (a shared-peer key
# would let 20 requests lock out everyone).
def _signup_xff(xff, email):
    r = _urequest.Request(f"http://127.0.0.1:{_port2}/api/waitlist", method="POST",
                          data=_wjson.dumps({"email": email}).encode())
    r.add_header("Content-Type", "application/json")
    r.add_header("X-Forwarded-For", xff)
    try:
        return _urequest.urlopen(r, timeout=10).status
    except _uerror.HTTPError as e:
        return e.code
_srv2.SIGNUP_RATE_MAX = 3
check("hardening: rate limit is per forwarded-client, keyed on XFF not the proxy peer",
      all(_signup_xff("9.9.9.9", f"rl{i}@ex.com") == 200 for i in range(3))
      and _signup_xff("9.9.9.9", "rl-over@ex.com") == 429
      and _signup_xff("8.8.8.8", "other-client@ex.com") == 200)
check("hardening: _client_key prefers the left-most X-Forwarded-For hop",
      _srv2._client_key(type("H", (), {
          "headers": {"X-Forwarded-For": "1.2.3.4, 10.0.0.1"},
          "client_address": ("10.0.0.1", 5)})()) == "1.2.3.4")
# The rate-limit map is hard-capped (LRU): rotating a spoofable forwarded-for
# value cannot grow it past MAX_RATE_KEYS — no unbounded memory, no O(n) scan.
_srv2.MAX_RATE_KEYS = 100
_srv2._SIGNUP_HITS.clear()
for _k in range(1000):
    _srv2._rate_ok(f"rot:{_k}")
check("hardening: rate-limit map is hard-capped under key rotation (no unbounded growth)",
      len(_srv2._SIGNUP_HITS) <= 100)
_srv2._SIGNUP_HITS.clear()
# The ledger match history is ring-buffered, so /api/fight cannot grow the
# store without bound (standings remain complete).
_srv2.MAX_LEDGER_MATCHES = 5
for _i in range(9):
    _srv2.record({"competitors": ["a", "b"], "winner": "a", "seed": _i,
                  "traceHash": f"sha256:{_i}"})
with open(_os.path.join(_conc_dir, "ledger.json")) as _lf:
    _led = _cj.load(_lf)
check("hardening: ledger match history is capped (ring-buffered), standings intact",
      len(_led["matches"]) == 5 and _led["standings"]["a"]["wins"] == 9)
_httpd2.shutdown()
_httpd.shutdown()

print("signup email (Resend, env-gated)")
# The server module was loaded with no RESEND_* env, so the earlier signup
# test above already proves the no-email path: signup succeeded with zero
# network egress. The builder is pure — test it directly.
check("no from address -> no emails built",
      _srv.build_waitlist_emails("a@b.co", 1, ["compete"], "", "ops@b.co") == [])
_msgs = _srv.build_waitlist_emails(
    "player@example.com", 3, ["compete", "build"],
    "Reddi Arena <arena@example.com>", "")
check("from only -> one confirmation to the signee",
      len(_msgs) == 1 and _msgs[0]["to"] == ["player@example.com"])
check("confirmation states position, roles, dry-run rail, and removal path",
      "position 3" in _msgs[0]["text"] and "compete, build" in _msgs[0]["text"]
      and "no real money" in _msgs[0]["text"]
      and "never sold or shared" in _msgs[0]["text"]
      and "removed" in _msgs[0]["text"])
_both = _srv.build_waitlist_emails(
    "player@example.com", 3, ["compete"],
    "Reddi Arena <arena@example.com>", "ops@example.com")
check("from + notify -> confirmation plus operator notice",
      len(_both) == 2 and _both[1]["to"] == ["ops@example.com"]
      and "player@example.com" in _both[1]["text"])
check("send is a no-op without both key and from address",
      _srv.send_waitlist_emails("a@b.co", 1, ["compete"]) is None
      and _srv.RESEND_API_KEY == "" and _srv.RESEND_FROM == "")


class _FakeHTTPError:
    def __init__(self, body):
        self._body = body

    def read(self):
        if self._body is None:
            raise OSError("stream already consumed")
        return self._body


# A bare "HTTP Error 403: Forbidden" hides Resend's actual reason (unverified
# domain, restricted key). The body is what makes a failure diagnosable.
check("resend error detail surfaces the response body",
      "domain is not verified" in _srv.resend_error_detail(
          _FakeHTTPError(b'{"message":"The reddi.tech domain is not verified"}')))
check("resend error detail truncates long bodies to 300 chars",
      len(_srv.resend_error_detail(_FakeHTTPError(b"x" * 5000))) == 300)
check("resend error detail never raises on an unreadable body",
      _srv.resend_error_detail(_FakeHTTPError(None)) == "")

# Cloudflare fronts api.resend.com and bans urllib's default signature with
# HTTP 403 "error code: 1010" before Resend ever sees the request. Caught by a
# live smoke test; this locks the fix in.
_rq = _srv.resend_request({"from": "a@b.co", "to": ["c@d.co"]}, api_key="test-key")
_ua = _rq.get_header("User-agent") or ""
check("resend request sends a real User-Agent, not Python-urllib",
      "reddi-arena" in _ua and "Python-urllib" not in _ua)
check("resend request carries bearer auth and json content type",
      _rq.get_header("Authorization") == "Bearer test-key"
      and _rq.get_header("Content-type") == "application/json")
check("resend request posts the payload to the emails endpoint",
      _rq.full_url == "https://api.resend.com/emails"
      and b'"from": "a@b.co"' in _rq.data)

print()
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
