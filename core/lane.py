"""Bounded execution lane (issue B1 / tests T-019..T-022).

The lane is the ONLY component permitted to execute a capability, and only
for declared, policy-matched, locally-bound invocations. It is pure and
deterministic: no clock, no randomness, no IO — "execution" in the dry-run
arena means returning an authorized invocation record that the match engine
acts on. Everything else is a refusal, and every decision (allow or refuse)
emits an event carrying subject, resource, action, and reason (T-022).

Fail-closed order of checks:
  0. binding escape (E1I)      -> refuse "binding-mismatch"         (T-077)
  1. undeclared tool           -> refuse "undeclared-tool"          (T-019)
  2. matching deny policy      -> refuse "denied-by-policy"
  3. no matching allow policy  -> refuse "no-matching-policy"       (T-020)
  4. policy invocation limit   -> refuse "invocation-limit-exceeded"
  5. egress: allowlist empty or host absent -> refuse "egress-refused" (T-021)

A capability disguised as a skill (A6 vector 4) is not in harness.tools and
therefore hits check 1 — the runtime half of that containment story.
"""
from __future__ import annotations


class ExecutionLane:
    def __init__(self, doc: dict, bound_hash: str | None = None,
                 live_hash: str | None = None):
        """bound_hash: capability hash from the weigh-in certificate this lane
        is bound to. live_hash: hash recomputed from the document actually
        being fielded. A mismatch is an escape attempt (E1I): the lane emits a
        binding refusal and refuses every subsequent invocation — a bot cannot
        be weighed in one configuration and fielded in another (T-077)."""
        # Defensive reads: a malformed (non-mapping) container reads as empty
        # rather than raising AttributeError (audit E2). The engine's fault
        # check forfeits such a document; the lane must not crash constructing.
        def _m(x):
            return x if isinstance(x, dict) else {}
        self.subject = "agent:" + (_m(doc.get("metadata")).get("name") or "unknown")
        harness = _m(doc.get("harness"))
        self.tools = {t.get("id"): t for t in harness.get("tools") or []
                      if isinstance(t, dict)}
        self.policies = [p for p in (harness.get("policies") or []) if isinstance(p, dict)]
        network = _m(_m(harness.get("runtime")).get("network"))
        self.egress_allowlist = list(network.get("allowlist") or [])
        self.events: list[dict] = []
        self._invocations: dict[str, int] = {}
        self.bound_hash = bound_hash
        self.escaped = (bound_hash is not None and live_hash is not None
                        and bound_hash != live_hash)
        if bound_hash is not None:
            self._event("declaration", "bind", not self.escaped,
                        "bound to weighed certificate" if not self.escaped else
                        "binding-mismatch: fielded document differs from "
                        "weighed certificate")

    # -- internals ----------------------------------------------------------
    def _event(self, resource: str, action: str, allowed: bool, reason: str) -> dict:
        event = {"subject": self.subject, "resource": resource, "action": action,
                 "allowed": allowed, "reason": reason}
        self.events.append(event)
        return event

    def _matching(self, resource: str, action: str, effect: str) -> list[dict]:
        return [p for p in self.policies
                if p.get("resource") == resource and p.get("action") == action
                and p.get("effect") == effect]

    # -- the only execution surface ----------------------------------------
    def invoke(self, tool_id: str, action: str = "invoke") -> dict:
        resource = f"tool:{tool_id}"
        if self.escaped:
            return self._event(resource, action, False, "binding-mismatch")
        if tool_id not in self.tools:
            return self._event(resource, action, False, "undeclared-tool")
        if self._matching(resource, action, "deny"):
            return self._event(resource, action, False, "denied-by-policy")
        allows = self._matching(resource, action, "allow")
        if not allows:
            return self._event(resource, action, False, "no-matching-policy")
        cap = min((p.get("limits", {}).get("maxInvocations") for p in allows
                   if p.get("limits", {}).get("maxInvocations") is not None),
                  default=None)
        used = self._invocations.get(tool_id, 0)
        if cap is not None and used >= cap:
            return self._event(resource, action, False, "invocation-limit-exceeded")
        self._invocations[tool_id] = used + 1
        return self._event(resource, action, True, "declared, policy-matched")

    def request_egress(self, host: str) -> dict:
        resource = f"egress:{host}"
        if host in self.egress_allowlist:
            return self._event(resource, "egress", True, "host on allowlist")
        reason = ("empty egress allowlist" if not self.egress_allowlist
                  else "host not on allowlist")
        return self._event(resource, "egress", False, f"egress-refused: {reason}")


def find_tool(doc: dict, fragment: str) -> str | None:
    """First declared tool id containing the fragment (case-insensitive).
    Tolerates a malformed harness/tools (audit E2): non-mapping entries are
    skipped rather than raising."""
    harness = doc.get("harness") if isinstance(doc, dict) else None
    tools = harness.get("tools") if isinstance(harness, dict) else None
    for tool in tools or []:
        if isinstance(tool, dict) and fragment.lower() in str(tool.get("id", "")).lower():
            return tool.get("id")
    return None
