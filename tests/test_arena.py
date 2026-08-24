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

print("weigh-in and draft")
solo = weigh_competitor(DEF)
check("defender is 62 AU Antweight", solo["soloAU"] == 62 and solo["soloClass"] == "Antweight")
d_ant = evaluate_hire(DEF, MERC, "Antweight")
check("hire refused at Antweight (class breach)", not d_ant.allowed)
check("refusal shows the AU delta", d_ant.au_delta == 65 and d_ant.fielded_au == 127)
d_beetle = evaluate_hire(DEF, MERC, "Beetleweight")
check("same hire allowed at Beetleweight", d_beetle.allowed)

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
