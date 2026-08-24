"""Conformance-aligned trace event emission with declared redaction
(issue B5, tests T-032..T-034).

The trace is the evidence substrate for receipts, learning mode, and
disputes — this module projects a match trace into the event stream the
competitor's ADL DECLARES (harness.observability.events), so downstream
consumers see the vocabulary the spec promised, not an engine-private one.

Three properties, all deterministic:

  * Complete, ordered, replayable (T-032): one monotonically increasing
    sequence, trace.started first, trace.completed last, and an explicit
    completeness accounting of declared-required events versus emitted —
    a forfeit match that never called a tool reports tool.called as
    missing rather than pretending completeness.
  * Declared redaction, not defaults (T-033): the redaction rules come
    from harness.observability.redaction of the competitor's own document.
    The engine has NO default field list. A document with no declared
    rules gets its payload withheld entirely — fail closed, not stored
    unredacted.
  * No secret survives (T-034): redaction is two-level. Declared fields
    are masked wherever they appear (any nesting, dicts or lists), and
    every VALUE that appeared under a declared field is then scrubbed
    from every string in the stream — so a secret echoed under some
    other key is caught too. A canary planted anywhere a declared field
    reaches cannot appear in the stored stream.

Boundary: a trace records what happened. Emission neither establishes
task success beyond the engine's stated outcome nor touches reputation.
"""
from __future__ import annotations

import copy
import json

REDACTED = "[REDACTED:{field}]"
WITHHELD = ("payload withheld: document declares no redaction rules; "
            "storing unredacted payloads is not permitted (fail closed)")


def declared_events(doc: dict) -> list[dict]:
    obs = (doc.get("harness") or {}).get("observability") or {}
    return list(obs.get("events") or [])


def declared_redaction(doc: dict) -> dict | None:
    obs = (doc.get("harness") or {}).get("observability") or {}
    rules = obs.get("redaction")
    if not rules or not rules.get("fields"):
        return None
    return {"mode": rules.get("mode"), "fields": list(rules["fields"])}


def _collect_leaves(v, out: list) -> None:
    """Every scalar leaf reachable under a declared-secret value. A secret
    declared as a structured value (a credentials object, a list of keys) hides
    its actual secrets in its leaves; collecting only the container would let a
    leaf echoed elsewhere survive the scrub (audit: structured-secret bypass)."""
    if isinstance(v, (str, int, float)):
        out.append(str(v))
    elif isinstance(v, dict):
        for item in v.values():
            _collect_leaves(item, out)
    elif isinstance(v, list):
        for item in v:
            _collect_leaves(item, out)


def _collect_secret_values(obj, fields: set, out: list) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in fields:
                _collect_leaves(v, out)
            _collect_secret_values(v, fields, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_secret_values(item, fields, out)


def _mask_fields(obj, fields: set):
    if isinstance(obj, dict):
        return {k: (REDACTED.format(field=k) if k in fields
                    else _mask_fields(v, fields)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mask_fields(item, fields) for item in obj]
    return obj


def _scrub_values(obj, secrets: list):
    if isinstance(obj, dict):
        return {k: _scrub_values(v, secrets) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_scrub_values(item, secrets) for item in obj]
    if isinstance(obj, str):
        for s in secrets:
            if s and s in obj:
                obj = obj.replace(s, "[SCRUBBED]")
        return obj
    return obj


def redact_payload(payload: dict, rules: dict | None):
    """Apply DECLARED redaction to a payload. No declaration -> the payload
    is withheld entirely (fail closed), never stored unredacted."""
    if rules is None:
        return {"withheld": WITHHELD}
    fields = set(rules["fields"])
    secrets: list = []
    _collect_secret_values(payload, fields, secrets)
    # Scrub longest-first (ties broken deterministically): replacing a short
    # secret that is a prefix/substring of a longer one first would bite a chunk
    # out of the longer secret and leave its tail exposed (audit: order-
    # dependent scrub leak). De-duplicated so the pass is stable.
    secrets = sorted({s for s in secrets if s}, key=lambda s: (-len(s), s))
    masked = _mask_fields(copy.deepcopy(payload), fields)
    return _scrub_values(masked, secrets)


def emit_events(trace: dict, doc_a: dict, doc_b: dict,
                payloads: dict | None = None) -> dict:
    """Project a match trace into the declared observability event stream.

    payloads: optional {competitor-name: dict} runtime payload attached to
    that competitor's task event — redacted per that competitor's own
    declared rules before it enters the stream.

    Returns {"stream": [...], "completeness": {name: {...}}} — both fully
    deterministic functions of the inputs (replayable, T-032).
    """
    docs = {trace["competitors"][0]: doc_a, trace["competitors"][1]: doc_b}
    payloads = payloads or {}
    stream: list[dict] = []

    def emit(name: str, competitor: str | None, payload: dict) -> None:
        stream.append({"seq": len(stream), "event": name,
                       "competitor": competitor, "payload": payload})

    emit("trace.started", None, {"seed": trace["seed"],
                                 "competitors": trace["competitors"]})
    reason = str(trace.get("reason", ""))
    # Attribution reads the STRUCTURED atFault list, never `name in reason` —
    # a prefix name would otherwise frame the innocent (audit T6).
    at_fault_set = set(trace.get("atFault") or [])
    # Budget-gate pass/fail is read from the STRUCTURED budgetGateFailed list,
    # never from a reason substring — a name containing "budget gate" would
    # otherwise mislabel a sputter forfeit (audit review minor).
    gate_failed_set = set(trace.get("budgetGateFailed") or [])
    for name in trace["competitors"]:
        emit("eval.checked", name, {"gate": "budget-check",
                                    "passed": name not in gate_failed_set})
    for name in trace["competitors"]:
        for e in (trace.get("laneEvents") or {}).get(name) or []:
            emit("policy.checked", name,
                 {k: e[k] for k in ("resource", "action", "allowed", "reason")})
            if e["allowed"] and e["action"] == "invoke":
                emit("tool.called", name, {"resource": e["resource"]})
    terminal = (trace.get("lifecycle") or {}).get("state")
    for name in trace["competitors"]:
        at_fault = name in at_fault_set
        event = "task.failed" if at_fault else "task.completed"
        payload = {"outcome": terminal, "reason": reason,
                   "winner": trace.get("winner")}
        if name in payloads:
            payload["runtime"] = redact_payload(payloads[name],
                                                declared_redaction(docs[name]))
        emit(event, name, payload)
    emit("trace.completed", None, {"traceHash": trace["traceHash"]})

    # task.completed / task.failed are both declared required but are
    # outcomes of the same completion — exactly one occurs per match, so
    # either satisfies the other's requirement.
    alternatives = {"task.completed": "task.failed",
                    "task.failed": "task.completed"}
    completeness = {}
    for name, doc in docs.items():
        required = [e["name"] for e in declared_events(doc) if e.get("required")]
        present = {e["event"] for e in stream
                   if e["competitor"] in (None, name)}
        completeness[name] = {
            "declaredRequired": required,
            "missing": [r for r in required
                        if r not in present
                        and alternatives.get(r) not in present],
        }
    return {"stream": stream, "completeness": completeness}


def stream_contains(emitted: dict, value: str) -> bool:
    """Adversarial helper (T-034): does the serialized stored stream
    contain the value anywhere?"""
    return value in json.dumps(emitted, sort_keys=True)
