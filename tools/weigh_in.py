#!/usr/bin/env python3
"""
Reddi Arena — deterministic weigh-in.

Computes an agent's Arena Unit (AU) weight and weight class purely from a
validated ADL v0.2 document. Pure function of the document: no network, no
provider probe, no execution, no clock, no randomness.

The point of this tool for the RAP/ADL proof: weight class is DERIVED from the
declaration, so the declaration must be complete and honest to be playable.
Understating capability to make weight either fails schema validation or fails
at runtime when an undeclared capability is exercised (see gate.declaration-
matches-behaviour in the ruleset).

BOUNDARY: computing a weight authorizes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml --break-system-packages")

WEIGHTS_VERSION = "arena-weights-v0.1"

CHASSIS_BASE = 20

REQUIREMENT_AU = {
    "toolCalling": 4,
    "structuredOutput": 3,
    "streaming": 1,
    "jsonMode": 2,
}

MODALITY_AU = {"text": 0, "embedding": 6, "image": 12, "audio": 12}

# Mirrors the schema's tool.sideEffects.mode enum exactly.
SIDE_EFFECT_AU = {
    "none": 0,
    "read": 2,
    "write": 8,
    "filesystem": 8,
    "mcp": 12,
    "network": 14,
    "messaging": 14,
    "shell": 18,
    "payment": 20,
    "multiple": 20,
}

SOURCE_TYPE_AU = {
    "file": 3,
    "url": 6,
    "api": 8,
    "database": 10,
    "vector-index": 12,
    "mcp": 14,
}

TRUST_AU = {"approved": 0, "unknown": 4, "untrusted": 6}

MEMORY_AU = {"session": 0, "persistent": 15, "external": 25}

TOOL_BASE_AU = 8
FUNCTION_AU = 5
SKILL_AU = 4
AUDIT_FULL_AU = 2
PAYMENT_INTENT_AU = 25
POLICY_CREDIT_AU = -2
POLICY_CREDIT_FLOOR = -20
ENGAGEMENT_OVERHEAD_AU = 10
COUPLING_FACTOR = 0.6

CLASSES = [
    ("Antweight", 100),
    ("Beetleweight", 250),
    ("Hobbyweight", 500),
    ("Featherweight", 900),
    ("Middleweight", 1800),
    ("Heavyweight", math.inf),
]


def classify(au: int) -> str:
    for name, ceiling in CLASSES:
        if au <= ceiling:
            return name
    return "Heavyweight"


def _lst(x) -> list:
    """Coerce a should-be-list to a list — a malformed (non-list) collection
    reads as empty rather than raising 'not iterable' (audit E2)."""
    return x if isinstance(x, list) else []


def _key(x, default: str) -> str:
    """Coerce an enum-lookup value to a hashable str; a non-str (list/dict)
    would raise 'unhashable type' as a dict key / set member (audit E2)."""
    return x if isinstance(x, str) else default


def _tier(value: Any, divisor: int, per: int) -> int:
    # bool is not a declaration; inf/nan overflow int(ceil()). For a huge int,
    # float division would overflow to inf too — so use EXACT integer ceil
    # division for ints (also removes a latent float-rounding path). Matches
    # math.ceil(value/divisor) for every well-formed value.
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return (-(-value // divisor)) * per
    if isinstance(value, float) and math.isfinite(value):
        return int(math.ceil(value / divisor)) * per
    return 0


def _referenced_policy_ids(harness: dict) -> set[str]:
    """Only policies actually referenced by a capability earn the hygiene credit."""
    referenced: set[str] = set()
    for collection in ("tools", "functions"):
        for item in _lst(harness.get(collection)):
            if not isinstance(item, dict):
                continue
            for ref in _lst(item.get("policyRefs")):
                if isinstance(ref, str):
                    referenced.add(ref)
    return referenced


# ---------------------------------------------------------------------------
# A7: conformance level -> league tier (tests T-015/T-016).
#
# This is an ARENA-LOCAL eligibility assessment, not canonical conformance
# certification — the lab's checker remains the authority on conformance
# levels (one-way canonicality). The ladder below assesses what a document
# structurally demonstrates, so tier eligibility can be computed
# deterministically at weigh-in. Each rung names its requirement; a rung
# passes only if every lower rung passed.
#
# Tier levels mirror core.arena.LEAGUE_TIERS (the suite asserts they stay
# in sync): purses and hiring require Title (L3); Rookie/Open are
# glory-only. Reaching a tier grants MATCH ELIGIBILITY only — never
# provider, network, wallet, or rail access.
# ---------------------------------------------------------------------------
TIER_LEVELS = {"rookie": 1, "open": 2, "title": 3}


def _l1(doc: dict) -> bool:
    return bool(_m(doc.get("metadata")).get("name")
                and doc.get("model")
                and _m(doc.get("harness")).get("tools"))


def _l2(doc: dict) -> bool:
    harness = _m(doc.get("harness"))
    tools = _lst(harness.get("tools"))
    policies = _lst(harness.get("policies"))
    covered = {p.get("resource") for p in policies
               if isinstance(p, dict) and isinstance(p.get("resource"), str)}
    obs = _m(harness.get("observability"))
    return bool(tools and obs.get("events")
                and all(isinstance(t, dict) and f"tool:{t.get('id')}" in covered
                        for t in tools))


def _l3(doc: dict) -> bool:
    # Evidence may live in conformance.evidenceRefs OR on the observability
    # events themselves — the lab-certified L3 reference mercenary declares
    # only the latter (finding F-012, reddiagent-lab#450).
    obs = _m(_m(doc.get("harness")).get("observability"))
    conf = _m(doc.get("conformance"))
    events = _lst(obs.get("events"))
    evidenced = bool(conf.get("evidenceRefs")
                     or (events and all(isinstance(e, dict) and e.get("evidenceRef")
                                        for e in events)))
    return bool(_m(obs.get("redaction")).get("fields")
                and obs.get("retention")
                and evidenced)


LEVEL_LADDER = [
    (1, "declares metadata.name, a model block, and at least one harness tool", _l1),
    (2, "every declared tool is policy-covered and observability events are declared", _l2),
    (3, "declares observability redaction and retention plus conformance evidenceRefs", _l3),
]


LADDER_MAX = LEVEL_LADDER[-1][0]


def assess_level(doc: dict) -> dict:
    """Arena-local structural assessment (arenaAssessedLevel = highest rung
    with every rung at or below it passing; the first failing rung is named).
    Deliberately NOT canonical conformance — see F-012 / reddiagent-lab#450."""
    assessed = 0
    failing = None
    for level, requirement, checkfn in LEVEL_LADDER:
        if checkfn(doc):
            assessed = level
        else:
            failing = {"level": level, "requirement": requirement}
            break
    return {"arenaAssessedLevel": assessed, "failingRung": failing}


def tier_verdict(doc: dict) -> dict:
    """The verdict recorded in the weigh-in certificate (T-015/T-016).

    Eligibility anchors to min(requestedLevel, arenaAssessedLevel) — which
    reproduces the lab checker's recorded verdicts for both reference docs
    (defender 1, mercenary 3). A requestedLevel above the assessed level is
    rejected with the failing rung named, and eligibility falls back to the
    assessed level — the over-claim is refused, the bot is not locked out of
    tiers it genuinely reaches. A requestedLevel beyond the ladder is
    assessed at the ladder maximum, not treated as a defect. An unreadable
    requestedLevel fails closed. Purse and hiring exist only at Title.
    """
    assessment = assess_level(doc)
    assessed = assessment["arenaAssessedLevel"]
    requested = _m(doc.get("conformance")).get("requestedLevel")
    if requested is not None and (not isinstance(requested, int)
                                  or isinstance(requested, bool)):
        return {
            "status": "rejected-unreadable",
            "reason": f"unreadable requestedLevel {requested!r} (non-integer)",
            "arenaAssessedLevel": assessed, "requestedLevel": None,
            "effectiveLevel": 0, "overRequested": False,
            "eligibleTiers": [], "highestTier": None,
            "purse": False, "hiring": False,
        }
    capped_request = min(requested, LADDER_MAX) if requested is not None else assessed
    over = capped_request > assessed
    effective = min(capped_request, assessed)
    if over:
        failing = assessment["failingRung"]
        status = "over-request-rejected"
        reason = (f"requestedLevel {requested} rejected: arena assessment is "
                  f"L{assessed} — L{failing['level']} requires "
                  f"{failing['requirement']}; eligibility falls back to "
                  f"L{effective}")
    else:
        status = "ok"
        reason = f"assessed L{assessed}, requested {requested}; effective L{effective}"
        if requested is not None and requested > LADDER_MAX:
            reason += (f" (requestedLevel {requested} is beyond the arena "
                       f"ladder maximum L{LADDER_MAX}; assessed at the maximum)")
    eligible = sorted((t for t, lvl in TIER_LEVELS.items() if effective >= lvl),
                      key=lambda t: TIER_LEVELS[t])
    highest = eligible[-1] if eligible else None
    return {
        "status": status,
        "reason": reason,
        "arenaAssessedLevel": assessed,
        "requestedLevel": requested,
        "effectiveLevel": effective,
        "overRequested": over,
        "eligibleTiers": eligible,
        "highestTier": highest,
        "purse": highest == "title",
        "hiring": highest == "title",
    }


def _m(x) -> dict:
    """Coerce a value that should be a mapping to a dict — a malformed
    (non-mapping) container reads as empty rather than raising AttributeError
    on `.get` (audit E2). weigh() must not crash on an untrusted document;
    run_vault_match's fault check then forfeits such a document."""
    return x if isinstance(x, dict) else {}


def weigh(doc: dict, hires: list[dict] | None = None) -> dict:
    """Return a full weigh-in certificate for an ADL document."""
    lines: list[tuple[str, int]] = []

    doc = _m(doc)
    model = _m(doc.get("model"))
    harness = _m(doc.get("harness"))
    reqs = _m(model.get("requirements"))

    lines.append(("chassis.base", CHASSIS_BASE))
    lines.append(("chassis.contextWindow", _tier(reqs.get("contextWindow"), 8000, 6)))
    lines.append(("chassis.maxOutputTokens", _tier(reqs.get("maxOutputTokens"), 512, 3)))

    for key, au in REQUIREMENT_AU.items():
        if reqs.get(key) is True:
            lines.append((f"chassis.req.{key}", au))

    for modality in _lst(reqs.get("modalities")):
        au = MODALITY_AU.get(_key(modality, ""), 12)
        if au:
            lines.append((f"chassis.modality.{modality}", au))

    for tool in _lst(harness.get("tools")):
        if not isinstance(tool, dict):
            continue
        tool_au = TOOL_BASE_AU
        mode = _key(_m(tool.get("sideEffects")).get("mode"), "none")
        tool_au += SIDE_EFFECT_AU.get(mode, 14)
        if tool.get("auditLevel") == "full":
            tool_au += AUDIT_FULL_AU
        lines.append((f"tool.{tool.get('id', '?')}", tool_au))

    for fn in _lst(harness.get("functions")):
        if isinstance(fn, dict):
            lines.append((f"function.{fn.get('id', '?')}", FUNCTION_AU))

    for skill in _lst(harness.get("skills")):
        if isinstance(skill, dict):
            lines.append((f"skill.{skill.get('id', '?')}", SKILL_AU))

    for src in _lst(harness.get("dataSources")):
        if not isinstance(src, dict):
            continue
        src_au = SOURCE_TYPE_AU.get(_key(src.get("type"), ""), 8)
        src_au += TRUST_AU.get(_key(src.get("trust"), ""), 6)
        lines.append((f"source.{src.get('id', '?')}", src_au))

    memory_mode = _key(_m(harness.get("memory")).get("mode", "session"), "session")
    if MEMORY_AU.get(memory_mode, 25):
        lines.append((f"memory.{memory_mode}", MEMORY_AU.get(memory_mode, 25)))

    referenced = _referenced_policy_ids(harness)
    credit = 0
    for policy in _lst(harness.get("policies")):
        if not isinstance(policy, dict):
            continue
        pid = policy.get("id")
        # Deny-effect policies always earn credit; allow-policies must be
        # referenced by a declared capability so no-op padding cannot farm credit.
        # (pid is only tested for set membership when it is a hashable str.)
        if policy.get("effect") == "deny" or (isinstance(pid, str) and pid in referenced):
            credit += POLICY_CREDIT_AU
    credit = max(credit, POLICY_CREDIT_FLOOR)
    if credit:
        lines.append(("policy.hygiene-credit", credit))

    intents = _lst(_m(_m(doc.get("extensions")).get("x402")).get("intents"))
    for intent in intents:
        if isinstance(intent, dict):
            lines.append((f"x402.intent.{intent.get('id', '?')}", PAYMENT_INTENT_AU))

    solo_au = sum(au for _, au in lines)

    hire_lines: list[tuple[str, int]] = []
    for hire in _lst(hires):
        merc_au = _m(hire).get("au")
        if not isinstance(merc_au, int) or isinstance(merc_au, bool):
            merc_au = 0
        # ceil(merc_au * 0.6) as EXACT integer math — merc_au * 0.6 (float)
        # overflows for a huge malformed AU (audit re-review). COUPLING_FACTOR
        # is 0.6 = 6/10.
        coupled = -(-(merc_au * 6) // 10) + ENGAGEMENT_OVERHEAD_AU
        hire_lines.append((f"hire.{_m(hire).get('name')}", coupled))

    fielded_au = solo_au + sum(au for _, au in hire_lines)

    # These two raw fields flow into the JSON-canonical capability hash, so a
    # non-serializable value (bytes/set) would crash json.dumps (audit
    # re-review M1). Coerce to a serializable scalar; the tierVerdict below
    # already handles the requestedLevel semantics separately.
    _agent = _m(doc.get("metadata")).get("name")
    _req_level = _m(doc.get("conformance")).get("requestedLevel")
    certificate = {
        "weightsVersion": WEIGHTS_VERSION,
        "agent": _agent if isinstance(_agent, str) else None,
        "requestedConformanceLevel": _req_level
            if isinstance(_req_level, (str, int, float)) and not isinstance(_req_level, bool)
            else None,
        "soloAU": solo_au,
        "soloClass": classify(solo_au),
        "fieldedAU": fielded_au,
        "fieldedClass": classify(fielded_au),
        "classBumped": classify(solo_au) != classify(fielded_au),
        "breakdown": [{"item": k, "au": v} for k, v in lines + hire_lines],
        # A7 / T-015: the tier verdict is part of the certificate and is
        # covered by the capability hash below, so it is auditable and
        # cannot be swapped after weigh-in.
        "tierVerdict": tier_verdict(doc),
    }
    canonical = json.dumps(
        {k: v for k, v in certificate.items() if k != "capabilityHash"},
        sort_keys=True,
        separators=(",", ":"),
    )
    certificate["capabilityHash"] = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
    return certificate


def main() -> int:
    ap = argparse.ArgumentParser(description="Reddi Arena deterministic weigh-in")
    ap.add_argument("adl", help="Path to an ADL v0.2 YAML/JSON document")
    ap.add_argument("--hire", action="append", default=[],
                    help="Path to a mercenary ADL engaged for this match (repeatable)")
    ap.add_argument("--json", action="store_true", help="Emit the raw certificate")
    args = ap.parse_args()

    with open(args.adl) as fh:
        doc = yaml.safe_load(fh)

    hires = []
    for path in args.hire:
        with open(path) as fh:
            merc = yaml.safe_load(fh)
        merc_cert = weigh(merc)
        hires.append({"name": merc_cert["agent"], "au": merc_cert["soloAU"]})

    cert = weigh(doc, hires)

    if args.json:
        print(json.dumps(cert, indent=2))
        return 0

    print(f"WEIGH-IN  [{cert['weightsVersion']}]")
    print(f"  agent            {cert['agent']}")
    print(f"  conformance      requested L{cert['requestedConformanceLevel']}")
    print("  ---- breakdown ----")
    for row in cert["breakdown"]:
        print(f"  {row['au']:>6}  {row['item']}")
        # noqa
    print("  -------------------")
    print(f"  solo             {cert['soloAU']} AU  -> {cert['soloClass']}")
    print(f"  fielded          {cert['fieldedAU']} AU  -> {cert['fieldedClass']}")
    if cert["classBumped"]:
        print(f"  !! CLASS BUMP: hires moved this bot {cert['soloClass']} -> {cert['fieldedClass']}")
    print(f"  capabilityHash   {cert['capabilityHash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
