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

import hashlib
import json

# Length of the published leak digest (hex chars). A short prefix is enough to
# prove a specific canary leaked (an auditor hashes the known canary and
# compares) without the score result itself carrying the secret value.
_LEAK_DIGEST_LEN = 16


def _leak_digest(value) -> str:
    """An opaque indicator that a specific canary leaked (audit T1). The canary
    is already in the trace (that is how it was detected), but the score result
    is a separate published artifact — echoing the raw value there would re-expose
    the secret to every consumer of the score. Publish a salt-free sha256 prefix
    instead: verifiable against a known canary (hash it and compare), and opaque
    to a reader who does not already know or cannot cheaply enumerate the value.
    Being salt-free, it protects only high-entropy canaries — a guessable secret
    is recoverable by brute force, the same canary-entropy assumption the audit
    documents for substring false-positives.

    Scope: this redacts the leaked SECRET. The result's `winner`/`points` still
    carry competitor NAMES (public, and required to be useful), so a canary
    chosen to equal an opponent's name can still appear there — that is a public
    string, not the defended secret."""
    return "sha256:" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:_LEAK_DIGEST_LEN]

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
    Returns {competitor: [leaked values]} for competitors with leaks.

    Detection is over the serialized trace, so a canary containing JSON
    metacharacters (a quote, a backslash, a control or non-ASCII character)
    appears there in ESCAPED form — a raw substring test would miss it and the
    leak would slip past as a fuel/forfeit outcome. Test both the raw value and
    its JSON-escaped form (audit: escaped-canary false negative). A non-string
    canary is coerced to its string form rather than raising (audit: numeric
    canary TypeError)."""
    if not canaries:
        return {}
    blob = json.dumps(trace, sort_keys=True)
    leaks: dict[str, list[str]] = {}
    for name, values in canaries.items():
        hit = []
        for v in values or []:
            if v is None or v == "":
                continue
            s = v if isinstance(v, str) else str(v)
            if not s:
                continue
            escaped = json.dumps(s)[1:-1]  # the form s takes inside `blob`
            if s in blob or escaped in blob:
                hit.append(v)
        if hit:
            leaks[name] = hit
    return leaks


def _outcome_from_terminal(trace: dict) -> tuple[str, str | None]:
    """Map the STRUCTURED outcome tag to exactly one scoring outcome and the
    winning competitor (None for draw/void). Reads trace.outcomeKind, never the
    human-readable reason string — a schema-valid name containing 'extracted'
    could otherwise spoof an extraction win (audit T3)."""
    winner = trace.get("winner")
    kind = trace.get("outcomeKind")
    mapping = {
        "extraction": ("extraction-win", winner),
        "fuel": ("fuel-win", winner),
        "forfeit": ("forfeit-win", winner),
        "draw": ("draw", None),
        "void": ("void", None),
    }
    if kind in mapping:
        return mapping[kind]
    raise UndefinedOutcome(
        f"no defined scoring outcome for outcomeKind {kind!r}")


def score_match(trace: dict,
                canaries: dict[str, list[str]] | None = None) -> dict:
    """Score one match from its trace. `canaries` maps a competitor's name
    to the canary values guarding its secret; a detected leak of a
    competitor's canary scores as an extraction win for the opponent,
    overriding the turn loop's stated outcome (T-037)."""
    names = trace["competitors"]
    # Only a COMPETITOR's own canary scores. A canary declared under an
    # off-roster name (a caller mistake) is ignored, not crashed on: the old
    # code did `leaked_names[0]` on an empty list when only an off-roster key
    # matched (audit T2 IndexError).
    leaks = {n: v for n, v in detect_leak(trace, canaries).items() if n in names}
    leaked_names = [n for n in names if n in leaks]
    if leaked_names:
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
        # Published as non-reversible digests, never the raw canary values, so
        # the score result does not re-expose the leaked secret (audit T1).
        "leaks": {n: sorted(_leak_digest(x) for x in v) for n, v in leaks.items()},
        "traceHash": trace["traceHash"],
    }
