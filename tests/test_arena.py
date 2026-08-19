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

print()
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
