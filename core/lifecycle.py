"""Match lifecycle state machine (issue B2 / tests T-023..T-025).

Deterministic lifecycle is the precondition for replayable evidence: a trace
is only auditable if the path that produced it is one of a small, closed set
of legal paths. This module makes that structural. States and transitions are
data; the ONLY way to move between them is `advance()`, which refuses illegal
transitions by raising — so an illegal lifecycle path is unreachable (T-025),
not merely discouraged.

Lifecycle events are evidence, not adjudication: the engine decides outcomes,
the lifecycle records which defined path was taken and refuses undefined ones.

States:
  scheduled -> weighing -> binding -> in-progress -> {decided, forfeit, draw}
                              \\-> {forfeit, void}   (binding escape, faulty
                                                     strategy declaration)

Terminal states are absorbing: nothing transitions out of them, so every
match ends in exactly one defined terminal state (T-023).
"""
from __future__ import annotations

TERMINAL = frozenset({"decided", "forfeit", "draw", "void"})

LEGAL: dict[str, frozenset] = {
    "scheduled": frozenset({"weighing"}),
    "weighing": frozenset({"binding"}),
    # Escape attempts and faulty declarations are resolved at binding, before
    # any turn runs; a void (both sides at fault) can only arise here.
    "binding": frozenset({"in-progress", "forfeit", "void"}),
    "in-progress": frozenset({"decided", "forfeit", "draw"}),
    "decided": frozenset(),
    "forfeit": frozenset(),
    "draw": frozenset(),
    "void": frozenset(),
}


class IllegalTransition(Exception):
    """Raised on any transition not in LEGAL — including out of a terminal
    state and into an unknown state."""


class MatchLifecycle:
    def __init__(self):
        self.state = "scheduled"
        self.history: list[dict] = []

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL

    def advance(self, to: str, reason: str) -> dict:
        if to not in LEGAL:
            raise IllegalTransition(f"unknown lifecycle state: {to!r}")
        if to not in LEGAL[self.state]:
            raise IllegalTransition(
                f"illegal transition {self.state!r} -> {to!r}: legal targets "
                f"are {sorted(LEGAL[self.state]) or 'none (terminal state)'}")
        entry = {"from": self.state, "to": to, "reason": reason}
        self.history.append(entry)
        self.state = to
        return entry

    def snapshot(self) -> dict:
        """Trace projection: final state plus the full transition history."""
        return {"state": self.state, "terminal": self.terminal,
                "history": list(self.history)}
