"""
Reddi Arena — chain projection layer.

Computes the EXACT on-chain payloads an Arena match would submit to the Quasar
programs, without submitting anything. Everything here is a pure function.

WHAT THIS DOES NOT DO — by design, not by omission:
  * No RPC connection, no cluster access, no network call of any kind.
  * No wallet, no keypair, no signing, no transaction construction.
  * No devnet or mainnet write. Devnet requires explicit operator approval with
    scoped wallet/RPC, transaction count, spend cap, and artifact path.
  * No AUDD custody, SPL-token escrow, or settlement. Per the rail-parity
    matrix, AUDD support is payment-plan and proof-metadata only.

Public keys accepted here are opaque identifiers used to derive deterministic
payloads. Supplying one grants nothing.

Shapes are pinned against nissan/reddi-agent-protocol programs/escrow:
  state.rs           AgentAccount, EscrowAccount, RatingAccount, AttestationAccount
  constants.rs       AGENT_SEED, ESCROW_SEED, RATING_SEED, ATTESTATION_SEED,
                     AGENT_REGISTRATION_FEE, AGENT_MODEL_MAX_LEN
  reveal_rating.rs   commitment = sha256(score || salt), score in 1..=10
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

# --- pinned from programs/escrow/src/constants.rs -------------------------
AGENT_SEED = b"agent"
ESCROW_SEED = b"escrow"
RATING_SEED = b"rating"
ATTESTATION_SEED = b"attestation"
AGENT_REGISTRATION_FEE = 10_000_000      # 0.01 SOL, burned to incinerator
AGENT_MODEL_MAX_LEN = 64
AGENT_FEE_BURN_ADDRESS = "1nc1nerator11111111111111111111111111111111"
RATING_EXPIRE_SLOTS = 1_512_000
CANCEL_WINDOW_SLOTS = 50_400

AGENT_TYPES = ("Primary", "Attestation", "Both")
ESCROW_STATUS = ("Locked", "Released", "Cancelled")
RATING_STATES = ("Pending", "BothCommitted", "Revealed", "Expired")

# Devnet program IDs, from the protocol repo README. Recorded for provenance
# only; nothing here connects to them.
DEVNET_PROGRAMS = {
    "registry": "Xk7jczJZ1HHJZuE1ZUWDqFmowxYhnom7mWzrNSGf9FU",
    "escrow": "VYCbMszux9seLK2aXFZMECMBFURvfuJLXsXPmJS5igW",
    "reputation": "nb9rLVjoHMibsgfRGgKuPqm6M8GVcH9r6bYNfg7Yiy6",
    "attestation": "CRGsWWkptdxsH6N6aWAyahLbuMsT58yM624EopEsv1Ex",
}

PROJECTION_MODE = "projection-only"
# nonce seed is 16 bytes on-chain ([u8; 16]); keep the hex slice consistent
NONCE_HEX_LEN = 32
NOT_SUBMITTED = "not-submitted: no RPC, no wallet, no signature, no cluster write"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# Real PDA derivation when solders is available; a labelled stand-in otherwise.
try:
    from solders.pubkey import Pubkey as _Pubkey
    PDA_MODE = "derived"
except ImportError:  # pragma: no cover
    _Pubkey = None
    PDA_MODE = "preimage-stand-in"


def _pda(seeds: list[bytes], program: str) -> dict:
    """
    Derive the real program-derived address via find_program_address when
    solders is installed. Deriving an address reads nothing and writes nothing —
    it is pure local math over the seeds and program id.
    """
    if _Pubkey is None:
        return {"address": "pda-preimage:" + _sha256(b"|".join(seeds))[:32],
                "bump": None, "derivation": "preimage-stand-in (install solders for real PDAs)"}
    addr, bump = _Pubkey.find_program_address(seeds, _Pubkey.from_string(program))
    return {"address": str(addr), "bump": bump, "derivation": "find_program_address"}


def _pubkey_bytes(key: str) -> bytes:
    """Seed bytes for a pubkey seed. Falls back to utf-8 for placeholder owners."""
    if _Pubkey is not None:
        try:
            return bytes(_Pubkey.from_string(key))
        except Exception:
            pass
    return key.encode()


# --------------------------------------------------------------------------
# 1. Registration — an ADL document projected onto AgentAccount
# --------------------------------------------------------------------------
def register_agent_payload(adl: dict, owner: str, rate_lamports: int | None = None) -> dict:
    """Project an ADL document onto the register_agent instruction arguments."""
    xa = (adl.get("extensions") or {}).get("x-arena") or {}
    is_merc = xa.get("listing") == "mercenary"
    # A specialist can also judge; a fighter is Primary only.
    agent_type = "Both" if is_merc else "Primary"

    # model string: the ADL capability + preferred provider, truncated to the
    # on-chain max. The full document lives off-chain, bound by hash.
    model_env = adl.get("model") or {}
    providers = model_env.get("providers") or {}
    model = f"{model_env.get('capability','chat')}:{providers.get('preferred','ollama')}"

    # rate_lamports: THIS IS FINDING F-009. The chain has a first-class rate
    # field; ADL v0.2 has none. We source it from the provisional x-arena.price.
    if rate_lamports is None:
        price = (xa.get("price") or {}).get("amount")
        rate_lamports = int(price) * 1_000_000 if price is not None else 0

    warnings = []
    if len(model) > AGENT_MODEL_MAX_LEN:
        warnings.append(f"model string {len(model)} > AGENT_MODEL_MAX_LEN {AGENT_MODEL_MAX_LEN}")
    if rate_lamports and not (xa.get("price") or {}).get("provisional") is not None:
        pass
    if (xa.get("price") or {}).get("provisional"):
        warnings.append("rate derived from provisional x-arena.price (F-007/F-009); "
                        "no canonical ADL price field exists")

    return {
        "mode": PROJECTION_MODE,
        "instruction": "register_agent",
        "program": DEVNET_PROGRAMS["registry"],
        "args": {
            "agent_type": agent_type,
            "model": model,
            "rate_lamports": rate_lamports,
            "min_reputation": int(xa.get("minReputation", 0)),
        },
        "accounts": {
            "owner": owner,
            "agent_pda": _pda([AGENT_SEED, _pubkey_bytes(owner)], DEVNET_PROGRAMS["registry"]),
            "fee_collector": AGENT_FEE_BURN_ADDRESS,
        },
        "feeLamports": AGENT_REGISTRATION_FEE,
        "adlBinding": {
            "agent": adl["metadata"]["name"],
            "documentHash": "sha256:" + _sha256(json.dumps(adl, sort_keys=True).encode()),
            "note": "the ADL document stays off-chain; only its hash is bound",
        },
        "warnings": warnings,
        "submitted": NOT_SUBMITTED,
    }


# --------------------------------------------------------------------------
# 2. Purse escrow — lock at weigh-in, release only on verified work
# --------------------------------------------------------------------------
@dataclass
class EscrowProjection:
    payer: str
    payee: str
    amount: int
    nonce: str
    status: str = "Locked"
    events: list = field(default_factory=list)


def lock_escrow_payload(payer: str, payee: str, amount_lamports: int, job_id: str) -> dict:
    nonce = _sha256(job_id.encode())[:NONCE_HEX_LEN]
    return {
        "mode": PROJECTION_MODE,
        "instruction": "lock_escrow",
        "program": DEVNET_PROGRAMS["escrow"],
        "args": {"amount": amount_lamports, "nonce": nonce},
        "accounts": {
            "payer": payer, "payee": payee,
            "escrow_pda": _pda([ESCROW_SEED, _pubkey_bytes(payer), bytes.fromhex(nonce)],
                               DEVNET_PROGRAMS["escrow"]),
        },
        "status": "Locked",
        "cancelWindowSlots": CANCEL_WINDOW_SLOTS,
        "submitted": NOT_SUBMITTED,
    }


def settle_match(trace: dict, gates_passed: bool, attestation_confirmed: bool,
                 payer: str, payee: str, amount_lamports: int) -> dict:
    """
    The rule the Arena exists to teach, expressed as a settlement decision.

    Transport completing is NOT sufficient. Release requires required gates to
    pass AND attestation to confirm. Anything else refunds or disputes.
    """
    job_id = trace["traceHash"]
    transport_ok = trace.get("result") in ("decisive", "draw")

    if not transport_ok:
        decision, instruction, reason = "cancel", "cancel_escrow", "match did not complete"
    elif not gates_passed:
        decision, instruction, reason = ("refund", "cancel_escrow",
                                         "a required eval gate failed; transport success is not work success")
    elif not attestation_confirmed:
        decision, instruction, reason = ("dispute", "dispute_attestation",
                                         "attestation not confirmed; payout blocked despite completed match")
    elif trace.get("winner") is None:
        decision, instruction, reason = "refund", "cancel_escrow", "draw; purses returned"
    else:
        decision, instruction, reason = "release", "release_escrow", "gates passed and attestation confirmed"

    return {
        "mode": PROJECTION_MODE,
        "decision": decision,
        "instruction": instruction,
        "program": DEVNET_PROGRAMS["escrow"],
        "reason": reason,
        "inputs": {
            "transportOk": transport_ok,
            "requiredGatesPassed": gates_passed,
            "attestationConfirmed": attestation_confirmed,
            "winner": trace.get("winner"),
        },
        "accounts": {"payer": payer, "payee": payee},
        "amount": amount_lamports,
        "evidenceRef": f"trace:{job_id}",
        "submitted": NOT_SUBMITTED,
    }


# --------------------------------------------------------------------------
# 3. Commit-reveal ratings — sha256(score || salt), score 1..=10
# --------------------------------------------------------------------------
def rating_commitment(score: int, salt: bytes) -> str:
    if not 1 <= score <= 10:
        raise ValueError("score must be in 1..=10 (EscrowError::InvalidScore)")
    if len(salt) != 32:
        raise ValueError("salt must be 32 bytes")
    return _sha256(bytes([score]) + salt)


def commit_reveal_round(job_id: str, consumer: str, specialist: str,
                        consumer_score: int, specialist_score: int,
                        consumer_salt: bytes, specialist_salt: bytes) -> dict:
    """Project a full commit -> reveal round, including verification."""
    c_commit = rating_commitment(consumer_score, consumer_salt)
    s_commit = rating_commitment(specialist_score, specialist_salt)
    rating_pda = _pda([RATING_SEED, job_id.encode()[:32]], DEVNET_PROGRAMS["reputation"])

    steps = [
        {"instruction": "commit_rating", "by": consumer, "commitment": c_commit,
         "stateAfter": "Pending"},
        {"instruction": "commit_rating", "by": specialist, "commitment": s_commit,
         "stateAfter": "BothCommitted"},
        {"instruction": "reveal_rating", "by": consumer, "score": consumer_score,
         "verifies": rating_commitment(consumer_score, consumer_salt) == c_commit},
        {"instruction": "reveal_rating", "by": specialist, "score": specialist_score,
         "verifies": rating_commitment(specialist_score, specialist_salt) == s_commit,
         "stateAfter": "Revealed"},
    ]
    return {
        "mode": PROJECTION_MODE,
        "program": DEVNET_PROGRAMS["reputation"],
        "ratingPda": rating_pda,
        "scheme": "sha256(score || salt)",
        "steps": steps,
        "expireSlots": RATING_EXPIRE_SLOTS,
        "property": "no score is readable before its reveal; a rival cannot copy or retaliate",
        "submitted": NOT_SUBMITTED,
    }


# --------------------------------------------------------------------------
# 4. Attestation — the arena referee
# --------------------------------------------------------------------------
def attest_quality_payload(job_id: str, judge: str, consumer: str, scores: list[int]) -> dict:
    if len(scores) != 5 or not all(1 <= s <= 10 for s in scores):
        raise ValueError("attestation takes exactly 5 scores in 1..=10")
    return {
        "mode": PROJECTION_MODE,
        "instruction": "attest_quality",
        "program": DEVNET_PROGRAMS["attestation"],
        "args": {"job_id": job_id[:32], "scores": scores},
        "accounts": {
            "judge": judge, "consumer": consumer,
            "attestation_pda": _pda([ATTESTATION_SEED, job_id.encode()[:32]],
                                    DEVNET_PROGRAMS["attestation"]),
        },
        "followUp": ["confirm_attestation", "dispute_attestation"],
        "submitted": NOT_SUBMITTED,
    }


# --------------------------------------------------------------------------
# 5. AUDD payment plan — reddi.audd-payment-plan.v1, dry-run only
# --------------------------------------------------------------------------
AUDD_PLAN_SCHEMA = "reddi.audd-payment-plan.v1"


def audd_purse_plan(amount: str, payee: str, settlement_account: str,
                    quote_expires_at: str, network: str = "solana-devnet",
                    mint: str = "AUDD_MINT_PLACEHOLDER") -> dict:
    """
    Emit a well-formed AUDD payment plan for an arena purse, in dry-run mode.

    Per the rail-parity matrix this is payment-plan and proof-metadata support
    only — NOT custody, SPL escrow, live activation, or settlement finality.
    paymentMode is hard-coded to dry-run; there is no parameter to change it.
    """
    return {
        "schemaVersion": AUDD_PLAN_SCHEMA,
        "asset": "AUDD",
        "network": network,
        "mint": mint,
        "payee": payee,
        "settlementAccount": settlement_account,
        "amount": amount,
        "quoteExpiresAt": quote_expires_at,
        "failurePolicy": {
            "mode": "no_charge_on_failure",
            "description": "A failed required eval gate charges nothing; the purse is returned.",
        },
        "refundPolicy": {
            "mode": "automatic",
            "description": "Draws and no-contests refund both purses automatically.",
        },
        "evidenceRequired": True,
        "paymentMode": "dry-run",
        "_boundary": ("proof-metadata only; no AUDD custody, no SPL escrow, no live "
                      "activation, no settlement-finality claim"),
    }


# --------------------------------------------------------------------------
# 6. Full match projection
# --------------------------------------------------------------------------
def project_match(trace: dict, adl_a: dict, adl_b: dict, owner_a: str, owner_b: str,
                  judge: str, purse_lamports: int = 100_000_000,
                  gates_passed: bool = True, attestation_confirmed: bool = True) -> dict:
    return {
        "mode": PROJECTION_MODE,
        "note": ("Everything below is what WOULD be submitted. Nothing is submitted. "
                 "Devnet writes require explicit operator approval."),
        "programs": DEVNET_PROGRAMS,
        "registrations": [
            register_agent_payload(adl_a, owner_a),
            register_agent_payload(adl_b, owner_b),
        ],
        "escrow": lock_escrow_payload(owner_a, owner_b, purse_lamports, trace["traceHash"]),
        "attestation": attest_quality_payload(trace["traceHash"], judge, owner_a, [8, 7, 9, 8, 7]),
        "settlement": settle_match(trace, gates_passed, attestation_confirmed,
                                   owner_a, owner_b, purse_lamports),
        "rating": commit_reveal_round(
            trace["traceHash"], owner_a, owner_b, 8, 6,
            b"\x01" * 32, b"\x02" * 32),
        "onChainFootprint": {
            "written": ["agent registry records", "escrow state", "rating commitments and reveals",
                        "attestation scores", "trace hash as evidence reference"],
            "notWritten": ["match traces", "ADL documents", "replay telemetry",
                           "player-identifiable metadata", "leaderboard rendering"],
        },
    }
