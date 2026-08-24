"""Token fuel accounting (issue B4 / tests T-029..T-031).

Fuel accounting is deterministic bookkeeping, not billing: the meter is the
single place fuel is charged, every charge is an itemized ledger entry, and
the ledger reconciles exactly with the emitted trace (T-031). The antweight
fuel model is unchanged — a turn costs the same 60 tokens it always did —
but the cost is now metered as prompt + completion components against the
declared caps instead of being a bare subtraction in the turn loop.

Per-turn cost model (deterministic reference values):
  prompt      40 tokens  (context assembly for the turn)
  completion  20 tokens  (the move itself; metered against maxOutputTokens)

Budget gate (T-029): a pre-match eval gate at the DECLARED thresholds.
A bot whose declared maxOutputTokens cannot cover one turn's completion, or
whose fuel cap cannot cover one full turn, exceeds its own declaration the
moment it plays — so the gate fails it before the first turn as a defined
outcome, never mid-match as a surprise.

Sputter (T-030): fuel exhaustion is a defined outcome, never an exception.
  * remaining < prompt cost           -> "sputter-pre"  (nothing charged)
  * prompt <= remaining < full turn   -> "sputter-mid"  (prompt charged,
    the completion never happens — the ledger records the partial turn)
"""
from __future__ import annotations

TURN_PROMPT_COST = 40
TURN_COMPLETION_COST = 20
TURN_COST = TURN_PROMPT_COST + TURN_COMPLETION_COST


def budget_gate(doc: dict, cap: int) -> dict:
    """Pre-match budget-check eval gate at the declared thresholds.

    `cap` is the effective fuel cap already read (and fault-checked) by the
    engine. Returns {"passed", "cap", "perTurnCost", "reason"}."""
    requirements = (doc.get("model") or {}).get("requirements") or {}
    declared_out = requirements.get("maxOutputTokens")
    if declared_out is not None and TURN_COMPLETION_COST > declared_out:
        return {"passed": False, "cap": cap, "perTurnCost": TURN_COST,
                "reason": (f"budget gate: per-turn completion "
                           f"{TURN_COMPLETION_COST} tokens exceeds declared "
                           f"maxOutputTokens {declared_out}")}
    if TURN_COST > cap:
        return {"passed": False, "cap": cap, "perTurnCost": TURN_COST,
                "reason": (f"budget gate: per-turn cost {TURN_COST} tokens "
                           f"exceeds declared fuel cap {cap}")}
    return {"passed": True, "cap": cap, "perTurnCost": TURN_COST,
            "reason": "budget gate: one full turn fits the declared caps"}


class FuelMeter:
    """Per-competitor fuel meter. The ONLY component that charges fuel."""

    def __init__(self, cap: int):
        self.cap = cap
        self.ledger: list[dict] = []

    @property
    def spent(self) -> int:
        return sum(e["prompt"] + e["completion"] for e in self.ledger)

    @property
    def remaining(self) -> int:
        return self.cap - self.spent

    def charge(self, turn: int) -> dict:
        """Charge one turn. Returns {"outcome", "prompt", "completion"} where
        outcome is "ok" | "sputter-pre" | "sputter-mid". Sputter is a defined
        outcome — the meter never overdraws and never raises."""
        if self.remaining < TURN_PROMPT_COST:
            return {"outcome": "sputter-pre", "prompt": 0, "completion": 0}
        if self.remaining < TURN_COST:
            entry = {"turn": turn, "prompt": TURN_PROMPT_COST, "completion": 0}
            self.ledger.append(entry)
            return {"outcome": "sputter-mid", "prompt": TURN_PROMPT_COST,
                    "completion": 0}
        entry = {"turn": turn, "prompt": TURN_PROMPT_COST,
                 "completion": TURN_COMPLETION_COST}
        self.ledger.append(entry)
        return {"outcome": "ok", "prompt": TURN_PROMPT_COST,
                "completion": TURN_COMPLETION_COST}

    def snapshot(self) -> dict:
        """Trace projection — reconciles by construction (T-031)."""
        return {"cap": self.cap, "spent": self.spent,
                "remaining": self.remaining, "ledger": list(self.ledger)}
