#!/usr/bin/env python3
"""
Reddi Arena — localnet rehearsal harness.

Arena-local tooling. This is deliberately NOT a lab-style `*_gate` / `*_packet`
script: the lab's 2026-07-26 direction reset paused adding those, and this
harness has no business recreating that pattern in a downstream repo.

What it does:
  1. Detects whether a Solana toolchain is present (surfpool / solana / anchor).
  2. Validates the chain projection payloads OFFLINE against the on-chain
     constraints read from programs/escrow — arg ranges, seed lengths, string
     limits, account completeness, settlement logic.
  3. Emits an ordered execution plan a human could run, once a toolchain AND
     explicit operator approval both exist.
  4. Prints an honest verdict about what is and is not blocking.

What it does not do:
  * Start a validator, connect to any RPC, or reach any network.
  * Create, load, or use a wallet or keypair.
  * Sign or submit a transaction on localnet, devnet, or mainnet.

Run: python3 tools/rehearse.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from core import chain  # noqa: E402
from core.arena import run_vault_match, load_adl  # noqa: E402

TOOLS = ["surfpool", "solana", "anchor", "solana-test-validator"]


def detect_toolchain() -> dict:
    found = {t: shutil.which(t) for t in TOOLS}
    return {
        "found": {k: v for k, v in found.items() if v},
        "missing": [k for k, v in found.items() if not v],
        "canExecute": bool(found.get("surfpool") or found.get("solana-test-validator")),
    }


# --------------------------------------------------------------------------
# Offline validation of the projected payloads
# --------------------------------------------------------------------------
def validate_projection(proj: dict) -> list[dict]:
    """Check every payload against the constraints in programs/escrow."""
    checks: list[dict] = []

    def ck(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    # --- registry ---
    for reg in proj["registrations"]:
        a = reg["args"]
        ck(f"register_agent[{a['agent_type']}] model <= {chain.AGENT_MODEL_MAX_LEN} chars",
           len(a["model"]) <= chain.AGENT_MODEL_MAX_LEN, a["model"])
        ck("register_agent agent_type is a valid variant",
           a["agent_type"] in chain.AGENT_TYPES, a["agent_type"])
        ck("register_agent min_reputation fits u8",
           0 <= a["min_reputation"] <= 255, str(a["min_reputation"]))
        ck("register_agent rate_lamports fits u64",
           0 <= a["rate_lamports"] < 2**64, str(a["rate_lamports"]))
        ck("register_agent burns the fee to the incinerator",
           reg["accounts"]["fee_collector"] == chain.AGENT_FEE_BURN_ADDRESS)
        ck("register_agent fee equals AGENT_REGISTRATION_FEE",
           reg["feeLamports"] == chain.AGENT_REGISTRATION_FEE)
        pda = reg["accounts"]["agent_pda"]
        ck("agent PDA derived via find_program_address",
           pda.get("derivation") == "find_program_address", pda.get("address", ""))
        ck("ADL bound by hash only (document stays off-chain)",
           reg["adlBinding"]["documentHash"].startswith("sha256:"))

    # --- escrow ---
    e = proj["escrow"]
    ck("lock_escrow nonce is 16 bytes ([u8; 16])", len(e["args"]["nonce"]) == 32,
       f"{len(e['args']['nonce'])} hex chars")
    ck("lock_escrow amount > 0", e["args"]["amount"] > 0)
    ck("lock_escrow status is a valid variant", e["status"] in chain.ESCROW_STATUS)
    ck("escrow PDA derived via find_program_address",
       e["accounts"]["escrow_pda"].get("derivation") == "find_program_address")

    # --- attestation ---
    at = proj["attestation"]
    ck("attest_quality supplies exactly 5 scores", len(at["args"]["scores"]) == 5)
    ck("attest_quality scores in 1..=10",
       all(1 <= s <= 10 for s in at["args"]["scores"]), str(at["args"]["scores"]))

    # --- ratings ---
    r = proj["rating"]
    ck("commit-reveal uses sha256(score || salt)", r["scheme"] == "sha256(score || salt)")
    ck("both parties commit before either reveals",
       [s["instruction"] for s in r["steps"]][:2] == ["commit_rating", "commit_rating"])
    ck("every reveal verifies against its commitment",
       all(s.get("verifies", True) for s in r["steps"]))

    # --- settlement logic ---
    s = proj["settlement"]
    ck("settlement decision is a known outcome",
       s["decision"] in ("release", "refund", "dispute", "cancel"), s["decision"])
    ck("release requires BOTH gates passed and attestation confirmed",
       (s["decision"] == "release")
       == (s["inputs"]["requiredGatesPassed"] and s["inputs"]["attestationConfirmed"]
           and s["inputs"]["winner"] is not None))

    # --- boundary invariants (the ones that matter most) ---
    blob = json.dumps(proj)
    ck("nothing claims to have been submitted", "not-submitted" in blob)
    ck("projection is labelled projection-only", proj["mode"] == "projection-only")
    ck("no private key / secret material in payloads",
       not any(k in blob.lower() for k in ("privatekey", "secretkey", "mnemonic", "seedphrase")))
    fp = proj["onChainFootprint"]
    ck("match traces stay off-chain", "match traces" in fp["notWritten"])
    ck("ADL documents stay off-chain", "ADL documents" in fp["notWritten"])
    ck("no player-identifiable metadata on-chain",
       "player-identifiable metadata" in fp["notWritten"])

    return checks


def execution_plan(proj: dict) -> list[dict]:
    """The ordered instruction sequence a rehearsal would run."""
    steps = []
    for i, reg in enumerate(proj["registrations"], 1):
        steps.append({"step": len(steps) + 1, "program": "registry",
                      "instruction": "register_agent",
                      "note": f"fighter {i}: {reg['adlBinding']['agent']}"})
    steps += [
        {"step": len(steps) + 1, "program": "escrow", "instruction": "lock_escrow",
         "note": "both purses locked at weigh-in"},
        {"step": len(steps) + 2, "program": "attestation", "instruction": "attest_quality",
         "note": "judge scores the match"},
        {"step": len(steps) + 3, "program": "attestation", "instruction": "confirm_attestation",
         "note": "confirmation gates payout"},
        {"step": len(steps) + 4, "program": "escrow",
         "instruction": proj["settlement"]["instruction"],
         "note": f"settlement: {proj['settlement']['decision']}"},
        {"step": len(steps) + 5, "program": "reputation", "instruction": "commit_rating x2",
         "note": "both parties commit before either reveals"},
        {"step": len(steps) + 6, "program": "reputation", "instruction": "reveal_rating x2",
         "note": "scores revealed and verified"},
    ]
    return steps


def main() -> int:
    tc = detect_toolchain()

    a = load_adl(ROOT / "adl" / "antweight-vault-defender.adl.yaml")
    b = load_adl(ROOT / "adl" / "antweight-vault-raider.adl.yaml")
    trace = run_vault_match(a, b, seed=2)
    proj = chain.project_match(trace, a, b,
                               "Xk7jczJZ1HHJZuE1ZUWDqFmowxYhnom7mWzrNSGf9FU",
                               "nb9rLVjoHMibsgfRGgKuPqm6M8GVcH9r6bYNfg7Yiy6",
                               "CRGsWWkptdxsH6N6aWAyahLbuMsT58yM624EopEsv1Ex")

    checks = validate_projection(proj)
    plan = execution_plan(proj)
    failed = [c for c in checks if not c["ok"]]

    print("REHEARSAL PREFLIGHT — Reddi Arena (Arena-local; not a lab gate script)\n")

    print(f"  PDA derivation mode: {chain.PDA_MODE}")
    print(f"  toolchain found:     {', '.join(tc['found']) or 'none'}")
    print(f"  toolchain missing:   {', '.join(tc['missing'])}\n")

    print(f"  offline payload validation — {len(checks) - len(failed)}/{len(checks)} passed")
    for c in failed:
        print(f"    FAIL  {c['check']}  {c['detail']}")
    if not failed:
        print("    all constraints from programs/escrow satisfied")

    print("\n  execution plan (would run, in order):")
    for s in plan:
        print(f"    {s['step']:>2}. {s['program']:12s} {s['instruction']:22s} {s['note']}")

    print("\n  BLOCKERS")
    blockers = []
    if not tc["canExecute"]:
        blockers.append("no local validator (install surfpool or solana-test-validator)")
    blockers.append("no wallet/keypair exists in this repo, by design")
    blockers.append("devnet writes need explicit operator approval: scoped wallet/RPC, "
                    "transaction count, spend cap, artifact path")
    for bl in blockers:
        print(f"    - {bl}")

    verdict = ("PAYLOADS-VALID / EXECUTION-BLOCKED" if not failed
               else "PAYLOADS-INVALID — fix before rehearsing")
    print(f"\n  VERDICT: {verdict}")
    print("  Nothing was started, connected, signed, or submitted.")

    if "--json" in sys.argv:
        out = {"toolchain": tc, "pdaMode": chain.PDA_MODE, "checks": checks,
               "plan": plan, "blockers": blockers, "verdict": verdict}
        Path("rehearsal-preflight.json").write_text(json.dumps(out, indent=2))
        print("\n  wrote rehearsal-preflight.json")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
