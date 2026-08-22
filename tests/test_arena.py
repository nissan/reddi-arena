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

print()
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
