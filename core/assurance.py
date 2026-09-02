"""RAP Assurance preview adapter for the Arena.

This module is deliberately a local/public-preview bridge, not a new protocol
schema. It maps the Arena's existing deterministic evidence (ADL documents,
match traces, chain projections) into the canonical RAP receipt/integrity field
names documented in:

* nissan/reddi-agent-protocol/docs/RAP-RECEIPT-POLICY-V1.md
* reddinft/reddiagent-lab/scripts/rap_receipt_validator.py
* nissan/reddi-agent-protocol/packages/x402-solana/src/spl-token-observer.ts

It never reaches Solana RPC, never loads a wallet, never signs, never submits,
and never treats the AUDD fixture as an official mint observation or grant
evidence. The only Solana data surfaced here is read-only metadata already
vendored in core.chain (devnet program IDs and locally derived PDAs).
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Any

from core import chain
from core.arena import (
    ARENA_CURRENCY,
    ARENA_RAIL,
    _canon,
    _hash,
    run_vault_match,
    weigh_competitor,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = ROOT / "fixtures" / "assurance" / "audd-transfer-checked.json"

RAP_RECEIPT_SCHEMA_VERSION = "reddi.receipt.v1"
RAP_POLICY_DECISION_SCHEMA_VERSION = "reddi.policy-decision.v1"
SPL_OBSERVATION_SCHEMA_VERSION = "reddi.svm-spl-transfer-checked-observation.v1"
SPL_OBSERVER_VERSION = "reddi.x402-solana.spl-transfer-checked-observer.v1"
PREVIEW_FORMAT_VERSION = "reddi.arena.rap-assurance-preview.v1"
FINALIZED_AT = "2026-08-31T00:00:00Z"
SPL_MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"

# Mirrors the canonical AUDD rail config's `deterministic-fixture` environment
# (packages/agent-protocol/src/audd-rail-config.ts). The sentinel mint must
# never be presented as an official or devnet AUDD mint, so the official
# mainnet mint is recorded here only as a value this preview refuses.
AUDD_DETERMINISTIC_FIXTURE_MINT = "AUDDdev111111111111111111111111111111111111"
AUDD_OFFICIAL_SOLANA_MAINNET_MINT = "AUDDttiEpCydTm7joUMbYddm72jAWXZnCpPZtDoxqBSw"
AUDD_FIXTURE_RAIL = {
    "environment": "deterministic-fixture",
    "status": "deterministic-fixture-only",
    "mint": AUDD_DETERMINISTIC_FIXTURE_MINT,
    "grantEligibility": "non_eligible",
    "evidenceEnvironment": "deterministic-fixture",
}

# Closed set from ReddiPolicyReasonCode / ReddiPolicyApprovalState in
# nissan/reddi-agent-protocol/packages/agent-protocol/src/policy.ts. A
# reddi.policy-decision.v1 document may only carry codes from this set.
CANONICAL_POLICY_REASON_CODES = frozenset(
    {
        "allowed",
        "budget_policy_missing",
        "invalid_quote",
        "malformed_limit",
        "request_amount_exceeds_limit",
        "session_budget_exceeded",
        "source_budget_exceeded",
        "specialist_budget_exceeded",
        "asset_network_budget_exceeded",
        "call_count_exceeded",
        "unsupported_asset_network",
        "operator_denied",
        "operator_approval_required",
        "payment_proof_missing",
        "unsupported_network_asset",
        "malformed_receipt",
        "credential_leakage_rejected",
    }
)
CANONICAL_POLICY_APPROVAL_STATES = frozenset({"approved", "denied", "requires_operator_approval"})

# Closed set from SplTransferCheckedObservationFailureReason in
# nissan/reddi-agent-protocol/packages/x402-solana/src/spl-token-observer.ts.
# An Arena-specific refusal travels in `arenaRefusal`, never in `reason`.
CANONICAL_OBSERVATION_FAILURE_REASONS = frozenset(
    {
        "malformed_expected_payment",
        "missing_transaction",
        "failed_transaction",
        "missing_confirmation_metadata",
        "wrong_signature",
        "no_transfer_checked",
        "wrong_token_program",
        "wrong_mint",
        "wrong_amount",
        "wrong_payee",
        "wrong_destination",
        "wrong_decimals",
        "wrong_authority",
        "duplicate_matching_transfer",
        "missing_memo",
        "memo_mismatch",
        "replay_detected",
    }
)

# Arena-owned preview disclosure. It is deliberately NOT part of any canonical
# RAP/x402 document; the label vocabulary reuses ReddiPaymentRecordLabels
# (packages/agent-protocol/src/payment-records.ts) so it stays comparable.
ARENA_PREVIEW_LABELS_VERSION = "reddi.arena.devnet-preview-labels.v1"

# The canonical observation failure each mutating refusal scenario must produce.
SCENARIO_REFUSAL_REASON = {"wrong-mint": "wrong_mint", "wrong-payee": "wrong_payee"}

REQUIRED_FIXTURE_KEYS = ("fixtureId", "boundary", "expected", "parsedTransaction")
REQUIRED_FIXTURE_EXPECTED_KEYS = (
    "network", "signature", "mint", "tokenProgram", "payTo", "amountBaseUnits", "authority",
)


class AssuranceIntegrityError(ValueError):
    """A server-side fixture or canonicality defect, never caller input."""

CANONICAL_REFS = {
    "adl": "vendor/ADL-v0.2.schema.json (pinned from reddiagent-lab)",
    "rapReceipt": "nissan/reddi-agent-protocol/docs/RAP-RECEIPT-POLICY-V1.md",
    "receiptIntegrity": "reddinft/reddiagent-lab/scripts/rap_receipt_validator.py",
    "splObserver": "nissan/reddi-agent-protocol/packages/x402-solana/src/spl-token-observer.ts",
    "auddRailMatrix": "nissan/reddi-agent-protocol/docs/AUDD-SOL-USDC-RAIL-PARITY-MATRIX-2026-06-24.md",
}

BOUNDARY_FLAGS = {
    "cluster": "solana-devnet",
    "previewOnly": True,
    # What this code can actually prove about itself: building a preview
    # performs no deployment. Whether the process answering the request is
    # externally hosted is an operator declaration, not something this module
    # can observe, so it is never asserted here.
    "deploymentPerformedByRequest": False,
    "rpcCall": False,
    "walletSigning": False,
    "transactionSubmitted": False,
    "liveValue": False,
    "custody": False,
    "settlementFinalityClaim": False,
    "officialMintObservation": False,
    "grantEvidence": False,
    "quasarCriticalPath": False,
}

SCENARIOS: "OrderedDict[str, dict[str, str]]" = OrderedDict(
    [
        (
            "valid-receipt",
            {
                "title": "Valid fixture receipt",
                "summary": "Payment proof, authority, work trace, eval, attestation, and replay ledger line up.",
                "expect": "accept",
            },
        ),
        (
            "tampered-trace",
            {
                "title": "Tampered replay evidence",
                "summary": "The displayed trace is changed after the receipt is built; the hash binding catches it.",
                "expect": "reject",
            },
        ),
        (
            "wrong-mint",
            {
                "title": "Wrong mint",
                "summary": "The parsed TransferChecked fixture pays with a different mint than the expected AUDD fixture rail.",
                "expect": "reject",
            },
        ),
        (
            "wrong-payee",
            {
                "title": "Wrong payee",
                "summary": "The destination token account owner does not match the mandate payee.",
                "expect": "reject",
            },
        ),
        (
            "duplicate-replay",
            {
                "title": "Duplicate / replay",
                "summary": "The same payment response is already in the replay ledger and cannot count twice.",
                "expect": "reject",
            },
        ),
        (
            "refund-gate-failed",
            {
                "title": "Refund on failed work gate",
                "summary": "The payment fixture exists, but the required eval gate fails, so no payout is accepted.",
                "expect": "reject",
            },
        ),
        (
            "authorization-denied",
            {
                "title": "Authorization denied before payment",
                "summary": "The delegated authority does not cover this resource; no payment or work receipt is accepted.",
                "expect": "reject",
            },
        ),
    ]
)

# Field names mirror the canonical lab integrity validator. They are used only
# to sanity-check Arena preview fixtures; this is not a replacement RAP schema.
REQUIRED_LAYERS = (
    "delegatedAuthority",
    "resourceAuthorization",
    "paymentEvidence",
    "settlementProgramProof",
    "serviceOutcome",
    "evalEvidence",
    "replayIdempotency",
    "privacyAccounting",
    "disputeState",
    "rollbackHold",
)

REQUIRED_LAYER_FIELDS: dict[str, tuple[str, ...]] = {
    "delegatedAuthority": (
        "mandateId",
        "principal",
        "spender",
        "payee",
        "purpose",
        "rail",
        "maxAmount",
        "expiresAt",
        "auditRef",
    ),
    "resourceAuthorization": ("serverRef", "toolName", "authorizationRef", "scope"),
    "paymentEvidence": (
        "requiredHash",
        "payloadHash",
        "responseHash",
        "rail",
        "facilitatorRef",
        "payee",
        "amount",
        "boundRequestId",
    ),
    "settlementProgramProof": (
        "cluster",
        "signature",
        "mint",
        "programId",
        "confirmationStatus",
        "payer",
        "payee",
        "amount",
    ),
    "serviceOutcome": ("requestHash", "responseHash", "status", "completedAt", "agentId"),
    "evalEvidence": ("gateId", "status", "evaluatorRef", "reportHash"),
    "replayIdempotency": (
        "receiptId",
        "idempotencyKey",
        "requestHash",
        "nonce",
        "priorPaymentResponseHashes",
    ),
    "privacyAccounting": ("entryRef", "privacyClass", "joinRefs", "retentionPolicy"),
    "disputeState": ("status",),
    "rollbackHold": ("holdState", "rollbackRequired"),
}

# The canonical validator keys diagnostics by evidence *category*, not by layer
# name, with three missing-layer overrides. Ported verbatim so preview
# diagnostics match the taxonomy consumers already parse.
LAYER_CATEGORY = {
    "delegatedAuthority": "authority",
    "resourceAuthorization": "resource",
    "paymentEvidence": "payment",
    "settlementProgramProof": "settlement",
    "serviceOutcome": "service",
    "evalEvidence": "eval",
    "replayIdempotency": "replay",
    "privacyAccounting": "accounting",
    "disputeState": "dispute",
    "rollbackHold": "rollback",
}

MISSING_LAYER_CODES = {
    "serviceOutcome": "rap_receipt.service_outcome.required",
    "paymentEvidence": "rap_receipt.payment.required",
    # Distinct from rap_receipt.rollback.required, which is an active hold state.
    "rollbackHold": "rap_receipt.rollback.evidence_required",
}

HOLD_CODES = frozenset(
    {
        "rap_receipt.service.failed_after_payment",
        "rap_receipt.dispute.open",
        "rap_receipt.rollback.required",
    }
)

CONFIRMED_SETTLEMENT_STATUSES = frozenset({"confirmed", "finalized"})
KNOWN_SERVICE_STATUSES = frozenset({"success", "failed"})
KNOWN_EVAL_STATUSES = frozenset({"pass", "failed"})
KNOWN_DISPUTE_STATUSES = frozenset({"none", "closed", "open"})
KNOWN_HOLD_STATES = frozenset({"none", "hold"})


class ReplayStore:
    """Small deterministic replay store compatible with the x402-solana shape."""

    def __init__(self, seen: set[str] | None = None):
        self.seen = set(seen or set())

    def check_and_store(self, key: str) -> bool:
        if key in self.seen:
            return False
        self.seen.add(key)
        return True


def boundary_flags(external_deployment: bool | None = None) -> dict:
    """Boundary flags for a preview response.

    `externalDeployment` is derived from the caller's explicit operator-declared
    deployment context — False for a local declaration, True for a hosted one —
    and is omitted entirely when the context is unknown, because "not externally
    deployed" is not something this module may infer.
    """
    flags = dict(BOUNDARY_FLAGS)
    if external_deployment is not None:
        flags["externalDeployment"] = bool(external_deployment)
    return flags


def scenario_catalog(external_deployment: bool | None = None) -> dict:
    return {
        "previewFormat": PREVIEW_FORMAT_VERSION,
        "boundary": boundary_flags(external_deployment),
        "canonicalRefs": dict(CANONICAL_REFS),
        "scenarios": [
            {"id": key, **value} for key, value in SCENARIOS.items()
        ],
    }


def _official_mint_present(obj: Any) -> bool:
    return AUDD_OFFICIAL_SOLANA_MAINNET_MINT in json.dumps(obj, default=str)


def preview_labels() -> dict:
    """Arena-owned Devnet Preview disclosure, outside every canonical schema."""
    return {
        "schemaVersion": ARENA_PREVIEW_LABELS_VERSION,
        "environment": AUDD_FIXTURE_RAIL["evidenceEnvironment"],
        "eligibility": AUDD_FIXTURE_RAIL["grantEligibility"],
        "railStatus": AUDD_FIXTURE_RAIL["status"],
        "boundary": "Arena preview disclosure; not a field of any canonical RAP or x402 document",
    }


def load_payment_fixture() -> dict:
    """Read and fully validate the preview fixture, or fail as a server defect.

    Every builder downstream indexes this document directly, so a contributed
    fixture that is unreadable, unparseable, or the wrong shape is a
    server-side integrity failure — never a caller error.
    """
    try:
        raw = FIXTURE_PATH.read_text()
    except OSError as exc:
        raise AssuranceIntegrityError(f"preview fixture is unreadable ({type(exc).__name__})") from exc
    try:
        fixture = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AssuranceIntegrityError(
            f"preview fixture is not valid JSON (line {exc.lineno} column {exc.colno})") from exc
    if not isinstance(fixture, dict):
        raise AssuranceIntegrityError("preview fixture must be a JSON object")
    missing = [key for key in REQUIRED_FIXTURE_KEYS if not fixture.get(key)]
    if missing:
        raise AssuranceIntegrityError(f"preview fixture is missing required keys: {', '.join(missing)}")
    if not isinstance(fixture["expected"], dict) or not isinstance(fixture["parsedTransaction"], dict):
        raise AssuranceIntegrityError("preview fixture expected/parsedTransaction must be JSON objects")
    missing = [key for key in REQUIRED_FIXTURE_EXPECTED_KEYS if not _string(fixture["expected"].get(key))]
    if missing:
        raise AssuranceIntegrityError(f"preview fixture expected terms are missing: {', '.join(missing)}")
    amount = fixture["expected"]["amountBaseUnits"]
    if not amount.isdigit() or amount.startswith("0"):
        raise AssuranceIntegrityError(
            "preview fixture expected.amountBaseUnits must be a positive integer base-unit string")
    if _official_mint_present(fixture):
        raise AssuranceIntegrityError(
            "Devnet preview fixtures must never carry the official AUDD mainnet mint; "
            f"use {AUDD_DETERMINISTIC_FIXTURE_MINT}"
        )
    _destination_balance(fixture["parsedTransaction"],
                         _transfer_instruction_info(fixture["parsedTransaction"]))
    return fixture


def _transfer_instruction_info(parsed: dict) -> dict:
    for item in _collect_instructions(parsed):
        if _is_transfer_checked(item["instruction"]):
            info = _get_path(item["instruction"], "parsed", "info")
            if isinstance(info, dict):
                return info
    raise AssuranceIntegrityError(
        "preview fixture has no parsed TransferChecked instruction with an info object")


def _destination_balance(parsed: dict, info: dict) -> dict:
    destination = _string(info.get("destination"))
    if destination is None:
        raise AssuranceIntegrityError(
            "preview fixture transfer instruction names no destination token account")
    for item in _as_list(_get_path(parsed, "meta", "postTokenBalances")):
        if not isinstance(item, dict):
            continue
        account = _account_key_at(parsed, item.get("accountIndex"))
        if account is not None and account == destination:
            return item
    raise AssuranceIntegrityError(
        "preview fixture has no meta.postTokenBalances entry for the transfer destination account")


def _paying_instruction_info(parsed: dict, expected: dict) -> dict:
    """The one transfer that satisfies the expected terms — the one an observer accepts.

    Breaking any other transfer would leave the paying one intact, so the
    scenario would present a verifiable payment under a refusal card.
    """
    matches = []
    for item in _collect_instructions(parsed):
        if not _is_transfer_checked(item["instruction"]):
            continue
        info = _get_path(item["instruction"], "parsed", "info")
        if isinstance(info, dict) and _candidate_matches(_candidate(parsed, item, expected), expected):
            matches.append(info)
    if len(matches) != 1:
        raise AssuranceIntegrityError(
            "preview scenario needs exactly one TransferChecked instruction satisfying the expected "
            f"payment terms to break; found {len(matches)}")
    return matches[0]


def _assert_scenario_refuses(scenario: str, parsed: dict, expected: dict) -> None:
    """Prove the mutated fixture actually produces the refusal the scenario claims."""
    reason = SCENARIO_REFUSAL_REASON.get(scenario)
    if reason is None:
        return
    outcome = verify_spl_transfer_checked_fixture(parsed, expected)
    if outcome.get("ok") or outcome.get("reason") != reason:
        got = "an accepted observation" if outcome.get("ok") else outcome.get("reason")
        raise AssuranceIntegrityError(
            f"preview scenario {scenario} must observe {reason} after its mutation but got {got}; "
            "refusing rather than presenting the opposite verdict")


def _break_field(container: dict, key: str, value: Any, what: str) -> None:
    """Apply a refusal-scenario mutation, refusing if it would change nothing.

    A no-op mutation would leave an untouched, verifiable payment presented
    under a refusal scenario, so the scenario would report accept for the very
    defect it exists to demonstrate.
    """
    if container.get(key) == value:
        raise AssuranceIntegrityError(
            f"preview scenario cannot be constructed: the {what} already holds the value "
            "the scenario must change, so the refusal it demonstrates would not occur")
    container[key] = value


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _trace_hash(trace: dict) -> str:
    return _hash({k: v for k, v in trace.items() if k != "traceHash"})


def _digest_ref(prefix: str, obj: Any) -> str:
    return f"{prefix}:" + _sha256_text(_canon(obj))[:24]


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _get_path(root: Any, *path: Any) -> Any:
    cur = root
    for part in path:
        if isinstance(part, int):
            if not isinstance(cur, list) or not 0 <= part < len(cur):
                return None
            cur = cur[part]
        else:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(part)
    return cur


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _public_key(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("pubkey")
    return _string(value)


def _collect_instructions(parsed: dict) -> list[dict]:
    out = []
    outer = _as_list(_get_path(parsed, "transaction", "message", "instructions"))
    for idx, instruction in enumerate(outer):
        if isinstance(instruction, dict):
            out.append({"instruction": instruction, "index": str(idx), "inner": False})
    for group in _as_list(_get_path(parsed, "meta", "innerInstructions")):
        if not isinstance(group, dict):
            continue
        parent = str(group.get("index", "unknown"))
        for idx, instruction in enumerate(_as_list(group.get("instructions"))):
            if isinstance(instruction, dict):
                out.append({"instruction": instruction, "index": f"{parent}.{idx}", "inner": True})
    return out


def _is_transfer_checked(instruction: dict) -> bool:
    return _get_path(instruction, "parsed", "type") == "transferChecked"


def _memo_values(instructions: list[dict]) -> list[str]:
    values = []
    for item in instructions:
        ix = item["instruction"]
        program_id = ix.get("programId")
        if program_id != SPL_MEMO_PROGRAM_ID:
            if ix.get("program") not in ("spl-memo", "spl-memo-v1"):
                continue
        parsed = ix.get("parsed")
        if isinstance(parsed, str):
            values.append(parsed)
        elif isinstance(parsed, dict):
            memo = parsed.get("memo") or _get_path(parsed, "info", "memo")
            if isinstance(memo, str):
                values.append(memo)
    return values


def _account_key_at(parsed: dict, index: Any) -> str | None:
    if not isinstance(index, int) or isinstance(index, bool):
        return None
    keys = _as_list(_get_path(parsed, "transaction", "message", "accountKeys"))
    if not 0 <= index < len(keys):
        return None
    return _public_key(keys[index])


OWNER_STATUS_EXPECTED_KEY = {
    "wrong_payee": "payTo",
    "wrong_mint": "mint",
    "wrong_token_program": "tokenProgram",
    "wrong_destination": "destinationTokenAccount",
}


def _owner_status(parsed: dict, token_account: str | None, expected: dict) -> dict:
    if not token_account:
        return {"ok": False, "reason": "wrong_destination", "actual": None}
    for item in _as_list(_get_path(parsed, "meta", "postTokenBalances")):
        if not isinstance(item, dict):
            continue
        if _account_key_at(parsed, item.get("accountIndex")) != token_account:
            continue
        if item.get("owner") != expected["payTo"]:
            return {"ok": False, "reason": "wrong_payee", "actual": item.get("owner")}
        if item.get("mint") != expected["mint"]:
            return {"ok": False, "reason": "wrong_mint", "actual": item.get("mint")}
        if item.get("programId") is not None and item.get("programId") != expected["tokenProgram"]:
            return {"ok": False, "reason": "wrong_token_program", "actual": item.get("programId")}
        return {"ok": True, "owner": expected["payTo"]}
    return {"ok": False, "reason": "wrong_destination", "actual": token_account}


def _candidate(parsed: dict, item: dict, expected: dict) -> dict:
    ix = item["instruction"]
    info = _as_dict(_get_path(ix, "parsed", "info"))
    token_amount = _as_dict(info.get("tokenAmount"))
    dest = _string(info.get("destination"))
    amount = _string(token_amount.get("amount")) or _string(info.get("amount"))
    candidate = {
        "index": item["index"],
        "inner": item["inner"],
        "programId": _string(ix.get("programId")),
        "sourceTokenAccount": _string(info.get("source")),
        "destinationTokenAccount": dest,
        "authority": _string(info.get("authority")),
        "mint": _string(info.get("mint")),
        "amountBaseUnits": amount,
        "decimals": token_amount.get("decimals") if isinstance(token_amount.get("decimals"), int) else None,
    }
    candidate["ownerStatus"] = _owner_status(parsed, dest, expected)
    return candidate


def _candidate_matches(candidate: dict, expected: dict) -> bool:
    if candidate["programId"] != expected["tokenProgram"]:
        return False
    if candidate["mint"] != expected["mint"]:
        return False
    if expected.get("destinationTokenAccount") and candidate["destinationTokenAccount"] != expected["destinationTokenAccount"]:
        return False
    if not candidate["ownerStatus"].get("ok"):
        return False
    if candidate["amountBaseUnits"] != expected["amountBaseUnits"]:
        return False
    if "decimals" in expected and candidate["decimals"] != expected["decimals"]:
        return False
    if expected.get("authority") and candidate["authority"] != expected["authority"]:
        return False
    return True


def _payment_failure(reason: str, message: str, expected: Any = None, actual: Any = None,
                     arena_refusal: str | None = None) -> dict:
    if reason not in CANONICAL_OBSERVATION_FAILURE_REASONS:
        raise AssuranceIntegrityError(
            f"{SPL_OBSERVATION_SCHEMA_VERSION} failure reasons must come from the canonical closed set; "
            f"got {reason}"
        )
    out = {"ok": False, "reason": reason, "message": message}
    if expected is not None:
        out["expected"] = expected
    if actual is not None:
        out["actual"] = actual
    if arena_refusal is not None:
        out["arenaRefusal"] = arena_refusal
    return out


def _no_payment_attempt(arena_refusal: str, message: str) -> dict:
    """No observation logic ran, so there is no canonical failure reason to give."""
    return {"ok": False, "observationAttempted": False, "arenaRefusal": arena_refusal, "message": message}


def _candidate_failure(candidates: list[dict], expected: dict) -> dict:
    with_program = [c for c in candidates if c["programId"] == expected["tokenProgram"]]
    if not with_program:
        return _payment_failure(
            "wrong_token_program",
            "no TransferChecked instruction used the expected token program",
            expected["tokenProgram"],
            [c["programId"] for c in candidates],
        )
    with_mint = [c for c in with_program if c["mint"] == expected["mint"]]
    if not with_mint:
        return _payment_failure(
            "wrong_mint",
            "no TransferChecked instruction used the expected mint",
            expected["mint"],
            [c["mint"] for c in with_program],
        )
    with_dest = (
        [c for c in with_mint if c["destinationTokenAccount"] == expected.get("destinationTokenAccount")]
        if expected.get("destinationTokenAccount")
        else with_mint
    )
    if not with_dest:
        return _payment_failure(
            "wrong_destination",
            "no TransferChecked instruction paid the expected destination token account",
            expected.get("destinationTokenAccount"),
            [c["destinationTokenAccount"] for c in with_mint],
        )
    with_owner = [c for c in with_dest if c["ownerStatus"].get("ok")]
    if not with_owner:
        first = with_dest[0]["ownerStatus"] if with_dest else {"reason": "wrong_payee"}
        reason = first.get("reason", "wrong_payee")
        return _payment_failure(
            reason,
            "destination token account is not owned by the expected payee for the expected mint/program",
            expected.get(OWNER_STATUS_EXPECTED_KEY.get(reason, "payTo")),
            first.get("actual"),
        )
    with_amount = [c for c in with_owner if c["amountBaseUnits"] == expected["amountBaseUnits"]]
    if not with_amount:
        return _payment_failure(
            "wrong_amount",
            "no TransferChecked instruction used the exact expected base-unit amount",
            expected["amountBaseUnits"],
            [c["amountBaseUnits"] for c in with_owner],
        )
    if "decimals" in expected and all(c["decimals"] != expected["decimals"] for c in with_amount):
        return _payment_failure(
            "wrong_decimals",
            "no TransferChecked instruction used the expected decimals",
            expected["decimals"],
            [c["decimals"] for c in with_amount],
        )
    if expected.get("authority") and all(c["authority"] != expected["authority"] for c in with_amount):
        return _payment_failure(
            "wrong_authority",
            "no TransferChecked instruction used the expected transfer authority",
            expected["authority"],
            [c["authority"] for c in with_amount],
        )
    return _payment_failure("wrong_amount", "transaction does not satisfy the expected payment terms")


def _validate_expected(expected: dict, commitment: str) -> dict | None:
    required = ("network", "signature", "mint", "tokenProgram", "payTo", "amountBaseUnits")
    if not isinstance(expected, dict) or any(not _string(expected.get(k)) for k in required):
        return _payment_failure("malformed_expected_payment", "expected payment terms are incomplete")
    if not expected["amountBaseUnits"].isdigit() or expected["amountBaseUnits"].startswith("0"):
        return _payment_failure("malformed_expected_payment", "expected amount must be a positive integer base-unit string")
    if _official_mint_present(expected):
        return _payment_failure(
            "wrong_mint",
            "the official AUDD mainnet mint may never be observed by the fixture-only Devnet Preview",
            AUDD_DETERMINISTIC_FIXTURE_MINT,
            arena_refusal="official_mint_blocked",
        )
    if commitment not in ("confirmed", "finalized"):
        return _payment_failure("missing_confirmation_metadata", "commitment must be confirmed or finalized")
    return None


def verify_spl_transfer_checked_fixture(
    parsed_transaction: dict,
    expected: dict,
    commitment: str = "confirmed",
    replay_store: ReplayStore | None = None,
) -> dict:
    """Read-only verifier for the deterministic parsed TransferChecked fixture.

    This intentionally mirrors the canonical x402-solana observer semantics the
    Arena needs for its preview cases, while keeping the boundary explicit: the
    input is already-parsed fixture data and the function performs no RPC.
    """
    malformed = _validate_expected(expected, commitment)
    if malformed:
        return malformed
    parsed = parsed_transaction if isinstance(parsed_transaction, dict) else {}
    meta = _as_dict(parsed.get("meta"))
    if not parsed or not meta:
        return _payment_failure("missing_transaction", "parsed transaction metadata is required")
    if _official_mint_present(parsed):
        return _payment_failure(
            "wrong_mint",
            "the official AUDD mainnet mint may never appear in a Devnet Preview fixture transaction",
            AUDD_DETERMINISTIC_FIXTURE_MINT,
            arena_refusal="official_mint_blocked",
        )
    if meta.get("err") not in (None, False):
        return _payment_failure("failed_transaction", "transaction metadata reports failure", None, meta.get("err"))
    if not _positive_int(parsed.get("slot")):
        return _payment_failure("missing_confirmation_metadata", "transaction must include a positive slot")
    block_time = parsed.get("blockTime")
    if block_time is not None and not _positive_int(block_time):
        return _payment_failure("missing_confirmation_metadata", "blockTime must be positive when present")
    signatures = _as_list(_get_path(parsed, "transaction", "signatures"))
    first_sig = signatures[0] if signatures and isinstance(signatures[0], str) else None
    if first_sig != expected["signature"]:
        return _payment_failure("wrong_signature", "first signature must match expected payment signature", expected["signature"], first_sig or signatures)

    instructions = _collect_instructions(parsed)
    transfer_items = [item for item in instructions if _is_transfer_checked(item["instruction"])]
    if not transfer_items:
        return _payment_failure("no_transfer_checked", "transaction contains no parsed SPL TransferChecked instruction")
    candidates = [_candidate(parsed, item, expected) for item in transfer_items]
    matches = [candidate for candidate in candidates if _candidate_matches(candidate, expected)]
    if not matches:
        return _candidate_failure(candidates, expected)
    if len(matches) > 1:
        return _payment_failure("duplicate_matching_transfer", "transaction contains more than one matching TransferChecked payment", 1, len(matches))

    expected_memo = expected.get("memo")
    memos = _memo_values(instructions)
    if expected.get("memoRequired") is True or expected_memo is not None:
        if not expected_memo:
            return _payment_failure("malformed_expected_payment", "memoRequired requires an expected memo")
        if not memos:
            return _payment_failure("missing_memo", "expected memo binding is missing", expected_memo)
        if expected_memo not in memos:
            return _payment_failure("memo_mismatch", "transaction memo does not match expected payment binding", expected_memo, memos)

    match = matches[0]
    replay_key = f"spl-transfer-checked:{expected['network'].lower()}:{expected['signature']}:{match['index']}"
    if replay_store is not None and not replay_store.check_and_store(replay_key):
        return _payment_failure("replay_detected", "payment transfer has already been accepted by the replay store", replay_key)

    return {
        "ok": True,
        "observation": {
            "schemaVersion": SPL_OBSERVATION_SCHEMA_VERSION,
            "verifierVersion": SPL_OBSERVER_VERSION,
            "network": expected["network"],
            "signature": expected["signature"],
            "slot": parsed["slot"],
            "blockTime": block_time if isinstance(block_time, int) and not isinstance(block_time, bool) else None,
            "commitment": commitment,
            "instructionIndex": match["index"],
            "innerInstruction": match["inner"],
            "sourceTokenAccount": match.get("sourceTokenAccount"),
            "destinationTokenAccount": match.get("destinationTokenAccount") or expected.get("destinationTokenAccount", ""),
            "destinationOwner": expected["payTo"],
            "authority": match.get("authority"),
            "mint": expected["mint"],
            "tokenProgram": expected["tokenProgram"],
            "amountBaseUnits": expected["amountBaseUnits"],
            "decimals": match.get("decimals"),
            "memo": expected_memo if expected_memo in memos else None,
            "paymentIntentId": expected.get("paymentIntentId"),
            "evidence": {
                "source": "parsed-transaction-fixture",
                "grantEligible": False,
            },
        },
        "replayKey": replay_key,
    }


def _policy_decision(allowed: bool, reason_codes: list[str], quote: dict | None = None) -> dict:
    unknown = sorted(code for code in reason_codes if code not in CANONICAL_POLICY_REASON_CODES)
    if unknown:
        raise AssuranceIntegrityError(
            f"{RAP_POLICY_DECISION_SCHEMA_VERSION} reasonCodes must come from the canonical closed set; "
            f"got {', '.join(unknown)}"
        )
    return {
        "schemaVersion": RAP_POLICY_DECISION_SCHEMA_VERSION,
        "allowed": allowed,
        "reasonCodes": reason_codes,
        "quotedAmount": quote,
        "limits": {"perRequestMaxBaseUnits": "3000000", "remainingBaseUnits": "500000"} if allowed else None,
        "asset": "AUDD",
        "network": "solana-devnet",
        "approvalState": "approved" if allowed else "denied",
        "auditNotes": [
            "fixture-only local preview; no wallet, RPC, signing, custody, or transaction submission",
            "payments prove transfer metadata; RAP Assurance requires authority, resource authorization, work evidence, eval, attestation, replay, accounting, dispute, and hold layers",
        ] if allowed else [
            "operator_denied: delegated authority does not cover the requested Arena fixture; payment preparation stops before any payment proof exists"
        ],
    }


def _request_envelope(trace: dict, scenario: str) -> dict:
    request_id = f"arena:vault:{trace['seed']}:{trace['competitors'][0]}:{trace['competitors'][1]}:{scenario}"
    payload = {
        "format": trace.get("format"),
        "seed": trace.get("seed"),
        "competitors": trace.get("competitors"),
        "scenario": scenario,
        "requiredEvalGate": "vault-trace-determinism",
    }
    return {
        "requestId": request_id,
        "requestHash": _hash(payload),
        "purpose": "arena-vault-competition-workflow",
        "toolName": "vault-match",
        "resourceScope": f"format=vault;seed={trace.get('seed')};fixture-only",
        "payloadHash": _hash(payload),
    }


def _observed_result(payment_result: dict) -> dict:
    """The verify result that actually observed a transfer, else empty.

    A replay rejection still had a real first observation; every other failure
    has none, and the receipt must not invent one.
    """
    if payment_result.get("ok"):
        return payment_result
    first = _as_dict(payment_result.get("firstAttempt"))
    return first if first.get("ok") else {}


def _settlement_proof(observation: dict) -> dict:
    """Settlement proof built only from the payment observation.

    Without a verified observation nothing settled, so every observable field
    is absent rather than restated from the expected payment terms. The layer
    is then an incomplete evidence layer, which is what
    `rap_receipt.settlement.invalid` truthfully reports.
    """
    if not observation:
        return {
            "cluster": "solana-devnet fixture",
            "confirmationStatus": "unverified",
        }
    return {
        "cluster": "solana-devnet fixture",
        "signature": f"fixture:{observation['signature']}:{observation['instructionIndex']}",
        "mint": observation["mint"],
        "programId": observation["tokenProgram"],
        "confirmationStatus": observation["commitment"],
        "payer": observation["authority"],
        "payee": observation["destinationOwner"],
        "amount": int(observation["amountBaseUnits"]),
    }


def _build_receipt(
    trace: dict,
    payment_result: dict,
    scenario: str,
    eval_status: str = "pass",
    duplicate_payment: bool = False,
    policy_allowed: bool = True,
    fixture: dict | None = None,
) -> dict:
    fixture = fixture if fixture is not None else load_payment_fixture()
    expected = fixture["expected"]
    observed = _observed_result(payment_result)
    observation = _as_dict(observed.get("observation"))
    replay_key = observed.get("replayKey")
    payer = expected["authority"]
    payee = expected["payTo"]
    request = _request_envelope(trace, scenario)
    request_id = request["requestId"]
    rail = "svm-spl-token-transfer-checked:solana-devnet:AUDD"
    response_hash = trace["traceHash"]
    eval_report_hash = _hash({"gate": "vault-trace-determinism", "traceHash": response_hash, "status": eval_status})
    payment_response_hash = _hash({
        "signature": observation.get("signature"),
        "instructionIndex": observation.get("instructionIndex"),
        "amount": observation.get("amountBaseUnits"),
        "mint": observation.get("mint"),
        "payee": observation.get("destinationOwner"),
    })
    settlement = _settlement_proof(observation)
    settlement_signature = settlement.get("signature")
    quote = {
        "amount": expected["amountBaseUnits"],
        "asset": "AUDD",
        "network": "solana-devnet",
        "source": "arena:vault-preview",
        "specialist": "arena:match-winner-or-referee",
    }
    policy = _policy_decision(policy_allowed, ["allowed"] if policy_allowed else ["operator_denied"], quote if policy_allowed else None)
    prior = [payment_response_hash] if duplicate_payment else []
    status = "attested" if eval_status == "pass" else "failed"

    receipt = {
        "schemaVersion": RAP_RECEIPT_SCHEMA_VERSION,
        "job": {"id": request_id, "type": "arena-vault-match"},
        "source": {"id": "reddi-arena-local-preview", "type": "local-public-preview"},
        "payer": {"id": "fixture-operator", "publicPaymentAddress": payer},
        "specialist": {"id": "arena-referee", "endpoint": "local-fixture-only", "publicPaymentAddress": payee},
        "protocol": {"name": "Reddi Agent Protocol", "version": "v0.1 fixture"},
        "payment": {
            "network": "solana-devnet",
            "asset": "AUDD",
            "amount": observation.get("amountBaseUnits"),
            "paymentProofRef": (
                f"fixture:spl-transfer-checked:{observation['signature']}:{observation['instructionIndex']}"
                if observation else None
            ),
            "proofBoundary": (
                "fixture proof metadata only; not a live AUDD payment" if observation
                else "no verified payment observation; this is an incomplete receipt candidate, not a receipt"
            ),
        },
        "requestHash": request["requestHash"],
        "responseHash": response_hash,
        "evidenceRef": f"trace:{response_hash}",
        "policyDecision": policy,
        "attestationStatus": status,
        "createdAt": FINALIZED_AT,
        "metadata": {
            "arenaRail": ARENA_RAIL,
            "arenaCurrency": ARENA_CURRENCY,
            "paymentObservationGrantEligible": False,
            "fixtureBoundary": fixture["boundary"],
            "expectedPaymentTerms": {
                "boundary": "Arena-owned quoted terms; what was required, never evidence that it happened",
                "network": expected["network"],
                "mint": expected["mint"],
                "payee": payee,
                "amountBaseUnits": expected["amountBaseUnits"],
            },
        },
        "request": request,
        "finalizedAt": FINALIZED_AT,
        "delegatedAuthority": {
            "mandateId": "mandate:arena-rap-assurance-preview",
            "principal": "fixture-operator",
            "spender": "reddi-arena-local-preview",
            "payee": payee,
            "purpose": request["purpose"],
            "rail": rail,
            "maxAmount": 3000000,
            "expiresAt": "2026-12-31T23:59:59Z",
            "auditRef": "audit://arena/rap-assurance-preview/mandate",
        },
        "resourceAuthorization": {
            "serverRef": "arena://local/devnet-preview",
            "toolName": request["toolName"],
            "authorizationRef": "mandate:arena-rap-assurance-preview",
            "scope": request["resourceScope"],
        },
        "paymentEvidence": {
            "requiredHash": _hash(expected),
            "payloadHash": _hash(observation or {"payment": "not-observed"}),
            "responseHash": payment_response_hash,
            "rail": rail,
            "facilitatorRef": "fixture:x402-solana-read-only-observer",
            "payee": observation.get("destinationOwner"),
            "amount": int(observation["amountBaseUnits"]) if observation else None,
            "boundRequestId": request_id,
        },
        "settlementProgramProof": settlement,
        "serviceOutcome": {
            "requestHash": request["requestHash"],
            "responseHash": response_hash,
            "status": "success" if trace.get("result") in ("decisive", "draw") else "failed",
            "completedAt": FINALIZED_AT,
            "agentId": payee,
        },
        "evalEvidence": {
            "gateId": "vault-trace-determinism",
            "status": eval_status,
            "evaluatorRef": "arena://core/run_vault_match",
            "reportHash": eval_report_hash,
        },
        "replayIdempotency": {
            "receiptId": "receipt:" + _sha256_text(request_id)[:24],
            "idempotencyKey": f"{replay_key}:{request_id}" if replay_key else None,
            "requestHash": request["requestHash"],
            "nonce": expected.get("paymentIntentId", "fixture-audd-intent"),
            "priorPaymentResponseHashes": prior,
        },
        "privacyAccounting": {
            "entryRef": "privacy://arena/preview/no-personal-data",
            "privacyClass": "public-fixture",
            "joinRefs": [ref for ref in (request_id, payment_response_hash, settlement_signature,
                                         response_hash, eval_report_hash) if ref],
            "retentionPolicy": "fixture only; no player-identifiable metadata",
        },
        "disputeState": {"status": "none"},
        "rollbackHold": {"holdState": "none", "rollbackRequired": False},
    }
    return receipt


def _diag(code: str, message: str, layer: str, path: str) -> dict:
    return {"code": code, "message": message, "layer": layer, "path": path}


def _missing(layer_value: dict, fields: tuple[str, ...]) -> list[str]:
    return [field for field in fields if field not in layer_value or layer_value[field] in (None, "")]


def _validate_receipt_layers(receipt: dict) -> list[dict]:
    diagnostics: list[dict] = []
    if not isinstance(receipt.get("request"), dict):
        diagnostics.append(_diag("rap_receipt.envelope.required", "Receipt must carry a request envelope.", "envelope", "receipt.request"))
    else:
        request = receipt["request"]
        missing = _missing(request, ("requestId", "requestHash", "purpose", "toolName", "resourceScope"))
        if missing:
            diagnostics.append(_diag("rap_receipt.envelope.required", f"Request envelope missing: {', '.join(missing)}.", "envelope", "receipt.request"))
    if not isinstance(receipt.get("finalizedAt"), str) or not receipt.get("finalizedAt"):
        diagnostics.append(_diag("rap_receipt.envelope.required", "Receipt must carry finalizedAt.", "envelope", "receipt.finalizedAt"))
    for layer in REQUIRED_LAYERS:
        category = LAYER_CATEGORY[layer]
        value = receipt.get(layer)
        if not isinstance(value, dict):
            code = MISSING_LAYER_CODES.get(layer, f"rap_receipt.{category}.required")
            diagnostics.append(_diag(code, f"Evidence layer {layer} must be present.", category, f"receipt.{layer}"))
            continue
        missing = _missing(value, REQUIRED_LAYER_FIELDS[layer])
        if missing:
            diagnostics.append(_diag(f"rap_receipt.{category}.invalid", f"Evidence layer {layer} missing: {', '.join(missing)}.", category, f"receipt.{layer}"))
    return diagnostics


def _valid_request(receipt: dict) -> dict:
    request = _as_dict(receipt.get("request"))
    if _missing(request, ("requestId", "requestHash", "purpose", "toolName", "resourceScope")):
        return {}
    return request


def _valid_layer(receipt: dict, layer: str) -> dict:
    """The layer when present and complete, else empty.

    Mirrors the canonical validator: a semantic cross-check must never consume
    an incomplete evidence layer, because the structural pass already rejected
    it with `rap_receipt.<category>.invalid`. Running anyway invents mismatches
    against fields that were simply never observed.
    """
    value = _as_dict(receipt.get(layer))
    if _missing(value, REQUIRED_LAYER_FIELDS[layer]):
        return {}
    return value


def _validate_receipt_semantics(receipt: dict) -> list[dict]:
    diagnostics: list[dict] = []
    request = _valid_request(receipt)
    authority = _valid_layer(receipt, "delegatedAuthority")
    resource = _valid_layer(receipt, "resourceAuthorization")
    payment = _valid_layer(receipt, "paymentEvidence")
    settlement = _valid_layer(receipt, "settlementProgramProof")
    service = _valid_layer(receipt, "serviceOutcome")
    eval_ev = _valid_layer(receipt, "evalEvidence")
    replay = _valid_layer(receipt, "replayIdempotency")
    accounting = _valid_layer(receipt, "privacyAccounting")
    dispute = _valid_layer(receipt, "disputeState")
    hold = _valid_layer(receipt, "rollbackHold")

    if authority and request and authority.get("purpose") != request.get("purpose"):
        diagnostics.append(_diag("rap_receipt.authority.scope_mismatch", "Mandate purpose does not match request purpose.", "authority", "receipt.delegatedAuthority.purpose"))
    if authority.get("revoked"):
        diagnostics.append(_diag("rap_receipt.authority.expired", "Mandate is revoked.", "authority", "receipt.delegatedAuthority.revoked"))
    if authority and receipt.get("finalizedAt") and authority.get("expiresAt", "") < receipt.get("finalizedAt"):
        diagnostics.append(_diag("rap_receipt.authority.expired", "Mandate expired before receipt finalization.", "authority", "receipt.delegatedAuthority.expiresAt"))
    if resource and request and (resource.get("toolName") != request.get("toolName") or resource.get("scope") != request.get("resourceScope")):
        diagnostics.append(_diag("rap_receipt.resource.scope_mismatch", "Resource authorization covers a different tool or scope.", "resource", "receipt.resourceAuthorization"))

    expected_payee = authority.get("payee")
    if expected_payee:
        for layer_name, value, field, path in (
            ("paymentEvidence", payment, "payee", "receipt.paymentEvidence.payee"),
            ("settlementProgramProof", settlement, "payee", "receipt.settlementProgramProof.payee"),
            ("serviceOutcome", service, "agentId", "receipt.serviceOutcome.agentId"),
        ):
            if value and value.get(field) != expected_payee:
                diagnostics.append(_diag("rap_receipt.settlement.payee_mismatch", f"{layer_name}.{field} does not match mandate payee.", "settlement", path))
    if payment and authority:
        if isinstance(payment.get("amount"), (int, float)) and isinstance(authority.get("maxAmount"), (int, float)) and payment["amount"] > authority["maxAmount"]:
            diagnostics.append(_diag("rap_receipt.authority.scope_mismatch", "Paid amount exceeds mandate cap.", "authority", "receipt.paymentEvidence.amount"))
        if payment.get("rail") != authority.get("rail"):
            diagnostics.append(_diag("rap_receipt.authority.scope_mismatch", "Payment rail does not match mandate rail.", "authority", "receipt.paymentEvidence.rail"))
    if settlement:
        if settlement.get("confirmationStatus") not in CONFIRMED_SETTLEMENT_STATUSES:
            diagnostics.append(_diag("rap_receipt.settlement.unconfirmed", "Settlement proof is not confirmed/finalized.", "settlement", "receipt.settlementProgramProof.confirmationStatus"))
        if payment and settlement.get("amount") != payment.get("amount"):
            diagnostics.append(_diag("rap_receipt.settlement.amount_mismatch", "Settlement amount does not match payment amount.", "settlement", "receipt.settlementProgramProof.amount"))
    if payment and replay and payment.get("responseHash") in _as_list(replay.get("priorPaymentResponseHashes")):
        diagnostics.append(_diag("rap_receipt.replay.duplicate_payment", "Payment response hash already appears in the replay ledger.", "replay", "receipt.replayIdempotency.priorPaymentResponseHashes"))
    if payment and request and payment.get("boundRequestId") != request.get("requestId"):
        diagnostics.append(_diag("rap_receipt.replay.duplicate_payment", "Payment proof is bound to a different request.", "replay", "receipt.paymentEvidence.boundRequestId"))
    if request:
        for layer_name, value, path in (
            ("serviceOutcome", service, "receipt.serviceOutcome.requestHash"),
            ("replayIdempotency", replay, "receipt.replayIdempotency.requestHash"),
        ):
            if value and value.get("requestHash") != request.get("requestHash"):
                diagnostics.append(_diag("rap_receipt.replay.duplicate_payment", f"{layer_name} is bound to a different request hash.", "replay", path))
    if accounting:
        join_refs = _as_list(accounting.get("joinRefs"))
        needed = [
            request.get("requestId"),
            payment.get("responseHash"),
            settlement.get("signature"),
            service.get("responseHash"),
            eval_ev.get("reportHash"),
        ]
        missing = sorted(ref for ref in needed if ref and ref not in join_refs)
        if missing:
            diagnostics.append(_diag("rap_receipt.accounting.join_required", "Accounting joinRefs cannot link all evidence.", "accounting", "receipt.privacyAccounting.joinRefs"))
    if service:
        if service.get("status") not in KNOWN_SERVICE_STATUSES:
            diagnostics.append(_diag("rap_receipt.service.invalid", "Unknown service status rejects.", "service", "receipt.serviceOutcome.status"))
        elif service.get("status") != "success":
            diagnostics.append(_diag("rap_receipt.service.failed_after_payment", "Service failed after payment; hold for refund/retry/dispute.", "service", "receipt.serviceOutcome.status"))
    if eval_ev:
        if eval_ev.get("status") not in KNOWN_EVAL_STATUSES:
            diagnostics.append(_diag("rap_receipt.eval.invalid", "Unknown eval status rejects.", "eval", "receipt.evalEvidence.status"))
        elif eval_ev.get("status") != "pass":
            diagnostics.append(_diag("rap_receipt.eval.failed", "Required evaluation gate did not pass.", "eval", "receipt.evalEvidence.status"))
    if dispute:
        if dispute.get("status") not in KNOWN_DISPUTE_STATUSES:
            diagnostics.append(_diag("rap_receipt.dispute.invalid", "Unknown dispute status rejects.", "dispute", "receipt.disputeState.status"))
        elif dispute.get("status") == "open":
            diagnostics.append(_diag("rap_receipt.dispute.open", "Dispute state is open.", "dispute", "receipt.disputeState.status"))
    if hold:
        if hold.get("holdState") not in KNOWN_HOLD_STATES:
            diagnostics.append(_diag("rap_receipt.rollback.invalid", "Unknown hold state rejects.", "rollback", "receipt.rollbackHold.holdState"))
        elif hold.get("rollbackRequired") or hold.get("holdState") != "none" or hold.get("killSwitchRef"):
            diagnostics.append(_diag("rap_receipt.rollback.required", "Rollback or hold criteria are active.", "rollback", "receipt.rollbackHold"))
    return diagnostics


def _assurance_verdict(receipt: dict | None, trace: dict, payment_result: dict, policy_allowed: bool,
                       structural: list[dict]) -> dict:
    diagnostics: list[dict] = []
    if not policy_allowed:
        diagnostics.append(_diag("rap_receipt.authority.scope_mismatch", "Delegated authority denied this resource; no payment/work receipt may be accepted.", "authority", "policyDecision"))
    if not payment_result.get("ok"):
        refusal = payment_result.get("arenaRefusal") or payment_result.get("reason") or "missing"
        diagnostics.append(_diag(f"rap_assurance.payment_observation.{refusal}", payment_result.get("message", "payment observation did not verify"), "payment", "paymentObservation"))
    if receipt is None:
        diagnostics.append(_diag("rap_receipt.envelope.required", "No RAP receipt was emitted for this denied/no-payment path.", "envelope", "receipt"))
    else:
        diagnostics.extend(structural)
        diagnostics.extend(_validate_receipt_semantics(receipt))
        recomputed = _trace_hash(trace)
        if trace.get("traceHash") != recomputed:
            diagnostics.append(_diag("rap_assurance.evidence.trace_tampered", "Trace content does not hash to its advertised traceHash.", "evidence", "trace"))
        if _get_path(receipt, "serviceOutcome", "responseHash") != trace.get("traceHash"):
            diagnostics.append(_diag("rap_assurance.evidence.trace_hash_mismatch", "Receipt service responseHash is not the presented trace hash.", "evidence", "receipt.serviceOutcome.responseHash"))
        if _get_path(receipt, "metadata", "paymentObservationGrantEligible") is not False:
            diagnostics.append(_diag("rap_assurance.boundary.grant_evidence", "Preview observations must stay grantEligible=false.", "boundary", "receipt.metadata.paymentObservationGrantEligible"))
    if any(diag["code"] not in HOLD_CODES for diag in diagnostics):
        decision = "reject"
    elif diagnostics:
        decision = "hold"
    else:
        decision = "accept"
    return {"decision": decision, "diagnostics": diagnostics}


def validate_assurance(receipt: dict | None, trace: dict, payment_result: dict,
                       policy_allowed: bool = True) -> dict:
    """Public verdict: always runs its own structural pass over the receipt."""
    return _assurance_verdict(receipt, trace, payment_result, policy_allowed,
                              _validate_receipt_layers(receipt) if receipt is not None else [])


def _scenario_fixture(scenario: str, fixture: dict) -> tuple[dict, dict | None]:
    parsed = copy.deepcopy(fixture["parsedTransaction"])
    expected = copy.deepcopy(fixture["expected"])
    replay_store = None
    if scenario == "wrong-mint":
        wrong = "WrongAuddMint1111111111111111111111111111111"
        info = _paying_instruction_info(parsed, expected)
        _break_field(info, "mint", wrong, "transfer instruction mint")
        _break_field(_destination_balance(parsed, info), "mint", wrong, "destination token balance mint")
    elif scenario == "wrong-payee":
        info = _paying_instruction_info(parsed, expected)
        _break_field(_destination_balance(parsed, info), "owner", expected["authority"],
                     "destination token account owner")
    elif scenario == "duplicate-replay":
        replay_store = ReplayStore()
    _assert_scenario_refuses(scenario, parsed, expected)
    return {"expected": expected, "parsedTransaction": parsed}, replay_store


def _payment_for_scenario(scenario: str, fixture: dict | None = None) -> dict:
    fixture = fixture if fixture is not None else load_payment_fixture()
    case, replay_store = _scenario_fixture(scenario, fixture)
    if scenario == "authorization-denied":
        return _no_payment_attempt("authorization_denied", "policy denied before payment preparation; no payment observation exists")
    if scenario == "duplicate-replay" and replay_store is not None:
        first = verify_spl_transfer_checked_fixture(case["parsedTransaction"], case["expected"], replay_store=replay_store)
        second = verify_spl_transfer_checked_fixture(case["parsedTransaction"], case["expected"], replay_store=replay_store)
        second["firstAttempt"] = first
        return second
    return verify_spl_transfer_checked_fixture(case["parsedTransaction"], case["expected"])


def _receipt_artifact(receipt: dict | None, decision: str, structural: list[dict]) -> dict:
    """What the emitted JSON actually is, read off the document, not the verdict.

    A receipt whose payment was genuinely observed and whose evidence layers are
    canonically complete stays a receipt even when assurance refuses it: the
    refusal is semantic (eval failed, replay, tampered trace), not structural.
    An unobserved payment leaves its evidence layers incomplete, so the same
    structural pass that reports it also classifies the artifact.
    """
    if receipt is None:
        return {"kind": "not-emitted", "label": "no receipt candidate (denied before payment)"}
    if structural:
        return {"kind": "invalid-candidate", "label": "invalid RAP Assurance receipt candidate"}
    if decision == "accept":
        return {"kind": "receipt", "label": "RAP Assurance receipt"}
    if decision == "hold":
        return {"kind": "verified-rejected-receipt", "label": "verified RAP Assurance receipt — held, not accepted"}
    return {"kind": "verified-rejected-receipt", "label": "verified RAP Assurance receipt — rejected, not accepted"}


def _tamper_trace(trace: dict) -> dict:
    tampered = copy.deepcopy(trace)
    if tampered.get("turns"):
        tampered["turns"][0]["probe_strength"] = tampered["turns"][0].get("probe_strength", 0) + 7
    else:
        tampered["reason"] = tampered.get("reason", "") + " tampered"
    # Intentionally keep the original traceHash to model an edited replay file.
    return tampered


def build_assurance_preview(
    bot_a: dict,
    bot_b: dict,
    *,
    scenario: str = "valid-receipt",
    seed: int = 2,
    hire_a: dict | None = None,
    hire_b: dict | None = None,
    entered_a: str | None = None,
    entered_b: str | None = None,
    external_deployment: bool | None = None,
) -> dict:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown RAP Assurance preview scenario {scenario!r}")

    trace = run_vault_match(
        bot_a,
        bot_b,
        seed=seed,
        hire_a=hire_a,
        hire_b=hire_b,
        entered_a=entered_a,
        entered_b=entered_b,
    )
    fixture = load_payment_fixture()
    payment_result = _payment_for_scenario(scenario, fixture)
    policy_allowed = scenario != "authorization-denied"
    eval_status = "failed" if scenario == "refund-gate-failed" else "pass"
    duplicate = scenario == "duplicate-replay"
    receipt = None if scenario == "authorization-denied" else _build_receipt(
        trace,
        payment_result,
        scenario,
        eval_status=eval_status,
        duplicate_payment=duplicate,
        policy_allowed=policy_allowed,
        fixture=fixture,
    )
    presented_trace = _tamper_trace(trace) if scenario == "tampered-trace" else trace
    structural = _validate_receipt_layers(receipt) if receipt is not None else []
    assurance = _assurance_verdict(receipt, presented_trace, payment_result, policy_allowed, structural)
    gates_passed = eval_status == "pass" and policy_allowed
    attested = eval_status == "pass" and policy_allowed
    settlement = chain.settle_match(trace, gates_passed, attested, "fixture-operator", "arena-referee", 100_000_000)
    if assurance["decision"] != "accept" and scenario != "refund-gate-failed":
        settlement.update({
            "decision": "blocked",
            "instruction": "no_release",
            "reason": "RAP Assurance did not accept the combined payment/work evidence; no payout or reputation update is modeled",
            "inputs": {"transportOk": trace.get("result") in ("decisive", "draw"),
                       "requiredGatesPassed": gates_passed,
                       "attestationConfirmed": attested,
                       "winner": trace.get("winner")},
        })
    if not policy_allowed:
        settlement.update({
            "instruction": "no_payment_prepared",
            "reason": "delegated authority denied before payment; no transfer or work claim exists",
            "inputs": {"transportOk": False, "requiredGatesPassed": False,
                       "attestationConfirmed": False, "winner": trace.get("winner")},
        })

    return {
        "previewFormat": PREVIEW_FORMAT_VERSION,
        # Stays truthful whether the preview is served locally or, once an
        # operator both enables it and declares a hosted context, from a hosted
        # deploy: the fixture claim holds in both. Whether the deploy is
        # external is carried by the derived boundary flag, never assumed here.
        "label": "Solana Devnet Preview — deterministic fixture, no live value",
        "scenario": {"id": scenario, **SCENARIOS[scenario]},
        "boundary": boundary_flags(external_deployment),
        "canonicalRefs": dict(CANONICAL_REFS),
        "devnetMetadata": {
            "programs": dict(chain.DEVNET_PROGRAMS),
            "pdaMode": chain.PDA_MODE,
            "source": "read-only metadata from core.chain; no RPC lookup performed",
        },
        "adapters": {
            "adl": {
                "source": "existing Arena ADL loader + pinned ADL v0.2 schema",
                "botA": weigh_competitor(bot_a),
                "botB": weigh_competitor(bot_b),
                "hireA": weigh_competitor(hire_a) if hire_a else None,
                "hireB": weigh_competitor(hire_b) if hire_b else None,
            },
            "paymentObservation": {
                "fixtureId": fixture["fixtureId"],
                "boundary": fixture["boundary"],
                "arenaPreviewLabels": preview_labels(),
                "result": payment_result,
            },
            "receiptIntegrity": {
                "canonicalTaxonomy": "reddiagent-lab rap_receipt.* diagnostics",
                "result": assurance,
            },
        },
        "trace": presented_trace,
        "receipt": receipt,
        "receiptArtifact": _receipt_artifact(receipt, assurance["decision"], structural),
        "settlement": settlement,
        "assertions": [
            {
                "id": "payment-transfer-metadata",
                "label": "Payment proof",
                "status": "pass" if payment_result.get("ok") else "fail",
                "text": "The fixture payment observation matches exact network, mint, payee, amount, authority, memo, and replay slot." if payment_result.get("ok") else payment_result.get("message"),
                "boundary": "This proves only fixture transfer metadata, not RAP work success or live AUDD settlement.",
            },
            {
                "id": "rap-assurance-paid-work",
                "label": "RAP Assurance",
                "status": "pass" if assurance["decision"] == "accept" else assurance["decision"],
                "text": "Authority, resource authorization, payment evidence, settlement proof metadata, work output, eval, replay, privacy accounting, dispute, and rollback layers are jointly checked.",
                "boundary": "Payment alone never releases reputation or payout in the preview.",
            },
            {
                "id": "settlement-decision",
                "label": "Settlement decision",
                "status": settlement["decision"],
                "text": settlement["reason"],
                "boundary": "Projection only; nothing is submitted and no custody exists.",
            },
        ],
        "contribution": {
            "fixtures": "fixtures/assurance/",
            "tests": "tests/test_arena.py assurance preview checks",
            "docs": "docs/DEVNET-PREVIEW-RAP-ASSURANCE.md",
            "rule": "Add a minimal deterministic fixture, document exactly what is simulated/read-only/blocked, and prove the behavior through a public API or core-adapter test.",
        },
    }
