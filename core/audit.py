"""Undeclared-capability reliance detection (issue E2I, tests T-080/T-081).

The subtler cheat is not declaring a tool but relying on capacity beyond the
declared envelope. Detection here is a PURE FUNCTION OVER TRACE EVIDENCE:
every match trace already carries the declared envelope and the actual usage
(B4's fuelAccounting ledger) plus every lane decision (B1/E1I laneEvents),
so declared-versus-actual is measurable on any match without touching live
state — detection over evidence, deliberately, so a third party can rerun
the audit from the published trace alone.

Boundary (hard): detection flags a discrepancy; adjudication is a separate
human-reviewed step. A flagged report's disposition is "review-required" —
this module contains no ban mechanism, and T-081 asserts that structurally.
"""
from __future__ import annotations

# Published tolerance: overrun is "sustained" when signals appear in at
# least this many matches of an audited series. One bad match is noise;
# a pattern is a discrepancy worth human eyes.
OVERRUN_TOLERANCE = 3

# The dispositions that exist. There is deliberately no "ban".
DISPOSITIONS = ("no-action", "review-required")


def audit_match(trace: dict, name: str) -> dict:
    """Measure declared-versus-actual usage for one competitor in one match,
    from the trace alone (T-080). Returns the measurements and any reliance
    signals — attempts or pressure beyond the declared envelope."""
    accounting = (trace.get("fuelAccounting") or {}).get(name) or {}
    cap = accounting.get("cap", 0)
    spent = accounting.get("spent", 0)
    lane_events = (trace.get("laneEvents") or {}).get(name) or []

    undeclared = [e for e in lane_events
                  if e.get("reason") == "undeclared-tool"]
    escapes = [e for e in lane_events
               if "binding-mismatch" in str(e.get("reason", ""))]
    # Envelope exhaustion is read STRUCTURALLY (a sputter turn attributed to
    # this competitor), never from a reason substring — a prefix name would
    # otherwise raise a false signal against the innocent (audit T6). Actual
    # overspend (spent > cap) is also a signal regardless of the current
    # engine's prose (audit T7), so a third-party trace with genuine overrun
    # is caught even without a sputter.
    exhausted = any(t.get("attacker") == name and t.get("strategy") == "sputter"
                    for t in trace.get("turns") or [])
    overspent = (spent > cap) if cap else (spent > 0)

    signals = []
    if undeclared:
        signals.append({"kind": "undeclared-invocation-attempt",
                        "count": len(undeclared)})
    if escapes:
        signals.append({"kind": "binding-escape", "count": len(escapes)})
    if exhausted:
        signals.append({"kind": "declared-envelope-exhausted", "count": 1})
    if overspent:
        signals.append({"kind": "declared-envelope-overspent",
                        "count": 1, "spent": spent, "cap": cap})

    return {
        "competitor": name,
        "declaredCap": cap,
        "spent": spent,
        "utilization": round(spent / cap, 4) if cap else 0.0,
        "signals": signals,
    }


def flag_sustained(audits: list[dict]) -> dict:
    """Aggregate a series of per-match audits for one competitor and flag
    sustained overrun with the measured delta (T-081). The only escalation
    is routing to human review — never an automatic ban.

    All audits must be for the SAME competitor: the result is labelled with
    audits[0]'s name and the deltas are summed, so mixing competitors would
    silently attribute one bot's overruns to another. A mixed series is a
    caller error and fails loudly rather than mislabelling (audit T12)."""
    competitors = {a.get("competitor") for a in audits}
    if len(competitors) > 1:
        raise ValueError(
            f"flag_sustained aggregates one competitor's audits; got mixed "
            f"competitors {sorted(str(c) for c in competitors)}")
    with_signals = [a for a in audits if a["signals"]]
    delta: dict[str, int] = {}
    for a in with_signals:
        for s in a["signals"]:
            delta[s["kind"]] = delta.get(s["kind"], 0) + s["count"]
    flagged = len(with_signals) >= OVERRUN_TOLERANCE
    return {
        "competitor": audits[0].get("competitor") if audits else None,
        "matchesAudited": len(audits),
        "matchesWithSignals": len(with_signals),
        "measuredDelta": delta,
        "tolerance": OVERRUN_TOLERANCE,
        "flagged": flagged,
        "disposition": "review-required" if flagged else "no-action",
        "adjudication": ("flag only: a human reviews flagged competitors; "
                         "no automatic enforcement exists in this module"),
    }
