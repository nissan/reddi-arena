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


def _tier(value: Any, divisor: int, per: int) -> int:
    if not isinstance(value, (int, float)):
        return 0
    return int(math.ceil(value / divisor)) * per


def _referenced_policy_ids(harness: dict) -> set[str]:
    """Only policies actually referenced by a capability earn the hygiene credit."""
    referenced: set[str] = set()
    for collection in ("tools", "functions"):
        for item in harness.get(collection) or []:
            for ref in item.get("policyRefs") or []:
                referenced.add(ref)
    return referenced


def weigh(doc: dict, hires: list[dict] | None = None) -> dict:
    """Return a full weigh-in certificate for an ADL document."""
    lines: list[tuple[str, int]] = []

    model = doc.get("model") or {}
    harness = doc.get("harness") or {}
    reqs = model.get("requirements") or {}

    lines.append(("chassis.base", CHASSIS_BASE))
    lines.append(("chassis.contextWindow", _tier(reqs.get("contextWindow"), 8000, 6)))
    lines.append(("chassis.maxOutputTokens", _tier(reqs.get("maxOutputTokens"), 512, 3)))

    for key, au in REQUIREMENT_AU.items():
        if reqs.get(key) is True:
            lines.append((f"chassis.req.{key}", au))

    for modality in reqs.get("modalities") or []:
        au = MODALITY_AU.get(modality, 12)
        if au:
            lines.append((f"chassis.modality.{modality}", au))

    for tool in harness.get("tools") or []:
        tool_au = TOOL_BASE_AU
        mode = ((tool.get("sideEffects") or {}).get("mode")) or "none"
        tool_au += SIDE_EFFECT_AU.get(mode, 14)
        if tool.get("auditLevel") == "full":
            tool_au += AUDIT_FULL_AU
        lines.append((f"tool.{tool.get('id', '?')}", tool_au))

    for fn in harness.get("functions") or []:
        lines.append((f"function.{fn.get('id', '?')}", FUNCTION_AU))

    for skill in harness.get("skills") or []:
        lines.append((f"skill.{skill.get('id', '?')}", SKILL_AU))

    for src in harness.get("dataSources") or []:
        src_au = SOURCE_TYPE_AU.get(src.get("type"), 8)
        src_au += TRUST_AU.get(src.get("trust"), 6)
        lines.append((f"source.{src.get('id', '?')}", src_au))

    memory_mode = (harness.get("memory") or {}).get("mode", "session")
    if MEMORY_AU.get(memory_mode, 25):
        lines.append((f"memory.{memory_mode}", MEMORY_AU.get(memory_mode, 25)))

    referenced = _referenced_policy_ids(harness)
    credit = 0
    for policy in harness.get("policies") or []:
        pid = policy.get("id")
        # Deny-effect policies always earn credit; allow-policies must be
        # referenced by a declared capability so no-op padding cannot farm credit.
        if policy.get("effect") == "deny" or pid in referenced:
            credit += POLICY_CREDIT_AU
    credit = max(credit, POLICY_CREDIT_FLOOR)
    if credit:
        lines.append(("policy.hygiene-credit", credit))

    intents = ((doc.get("extensions") or {}).get("x402") or {}).get("intents") or []
    for intent in intents:
        lines.append((f"x402.intent.{intent.get('id', '?')}", PAYMENT_INTENT_AU))

    solo_au = sum(au for _, au in lines)

    hire_lines: list[tuple[str, int]] = []
    for hire in hires or []:
        merc_au = hire["au"]
        coupled = int(math.ceil(merc_au * COUPLING_FACTOR)) + ENGAGEMENT_OVERHEAD_AU
        hire_lines.append((f"hire.{hire['name']}", coupled))

    fielded_au = solo_au + sum(au for _, au in hire_lines)

    certificate = {
        "weightsVersion": WEIGHTS_VERSION,
        "agent": (doc.get("metadata") or {}).get("name"),
        "requestedConformanceLevel": (doc.get("conformance") or {}).get("requestedLevel"),
        "soloAU": solo_au,
        "soloClass": classify(solo_au),
        "fieldedAU": fielded_au,
        "fieldedClass": classify(fielded_au),
        "classBumped": classify(solo_au) != classify(fielded_au),
        "breakdown": [{"item": k, "au": v} for k, v in lines + hire_lines],
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
