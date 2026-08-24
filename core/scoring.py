"""Vault attack/defend scoring (issue B6, tests T-035..T-037).

A format nobody can argue about is worth more than five ambiguous ones:
scoring is a PURE FUNCTION OF THE TRACE. Identical traces always produce
identical scores (T-035), every lifecycle terminal state maps to exactly
one defined scoring outcome (T-036), and anything else is a refusal — an
unknown terminal state raises instead of guessing.

Canary rule (T-037): the defended secret is represented by canary values
the defender planted. If any of a competitor's canaries appears ANYWHERE
in the trace — a reason string, a grafted payload, an opponent's name
chosen to echo it — that secret left the vault, and the match scores as an
extraction win for the opponent regardless of what the turn loop said.
Detection is textual over the serialized trace: a leak "in any form the
canary detects" means the canary value is present verbatim; transformed
leaks are out of scope for the dry-run arena and documented as such.

Boundary: scoring is deterministic given a trace; it does not judge intent.
"""
from __future__ import annotations

import json

# Points vocabulary (arena-local, deliberately small):
POINTS = {
    "extraction-win": (3, 0),   # (winner, loser)
    "fuel-win": (2, 0),
    "forfeit-win": (2, 0),
    "draw": (1, 1),
    "void": (0, 0),
}


class UndefinedOutcome(Exception):
    """Raised when a trace's terminal state has no defined scoring outcome."""


def detect_leak(trace: dict, canaries: dict[str, list[str]] | None) -> dict:
    """Which competitors' canary values appear anywhere in the trace?
    Returns {competitor: [leaked values]} for competitors with leaks."""
    if not canaries:
        return {}
    blob = json.dumps(trace, sort_keys=True)
    leaks: dict[str, list[str]] = {}
    for name, values in canaries.items():
        hit = [v for v in values or [] if v and v in blob]
        if hit:
            leaks[name] = hit
    return leaks


def _outcome_from_terminal(trace: dict) -> tuple[str, str | None]:
    """Map the lifecycle terminal state (plus the stated reason) to exactly
    one scoring outcome and the winning competitor (None for draw/void)."""
    terminal = (trace.get("lifecycle") or {}).get("state")
    winner = trace.get("winner")
    reason = str(trace.get("reason", ""))
    if terminal == "decided":
        if "extracted" in reason:
            return "extraction-win", winner
        return "fuel-win", winner
    if terminal == "forfeit":
        return "forfeit-win", winner
    if terminal == "draw":
        return "draw", None
    if terminal == "void":
        return "void", None
    raise UndefinedOutcome(
        f"no defined scoring outcome for terminal state {terminal!r}")


def score_match(trace: dict,
                canaries: dict[str, list[str]] | None = None) -> dict:
    """Score one match from its trace. `canaries` maps a competitor's name
    to the canary values guarding its secret; a detected leak of a
    competitor's canary scores as an extraction win for the opponent,
    overriding the turn loop's stated outcome (T-037)."""
    names = trace["competitors"]
    leaks = detect_leak(trace, canaries)
    if leaks:
        leaked_names = [n for n in names if n in leaks]
        if len(leaked_names) == 2:
            outcome, winner = "void", None
        else:
            victim = leaked_names[0]
            winner = names[1 - names.index(victim)]
            outcome = "extraction-win"
    else:
        outcome, winner = _outcome_from_terminal(trace)

    win_pts, lose_pts = POINTS[outcome]
    if winner is None:
        points = {n: win_pts if outcome == "draw" else 0 for n in names}
    else:
        points = {n: win_pts if n == winner else lose_pts for n in names}
    return {
        "outcome": outcome,
        "winner": winner,
        "points": points,
        "leaks": {n: sorted(v) for n, v in leaks.items()},
        "traceHash": trace["traceHash"],
    }
