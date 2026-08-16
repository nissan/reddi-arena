#!/usr/bin/env python3
"""
Reddi Arena — balance simulation harness.

Implements the format-balance work the plan calls for (issue B7). Answers three
questions with numbers rather than vibes:

  1. Is there a first-mover advantage? (attacker moves first in Vault)
  2. Does any archetype dominate?
  3. Is the power-up overpowered — does hiring win the match by itself?

Deterministic: every run sweeps a fixed seed range, so the report is
reproducible and diffable across changes to the engine or the weight formula.

Run: python3 tools/simulate.py [--seeds 200]
"""

from __future__ import annotations

import argparse
import copy
import json
import statistics

C_DIM = ""
C_DIM_END = ""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from core.arena import run_vault_match, load_adl  # noqa: E402

# Published tolerance bands. A run outside these is a balance FAILURE, and the
# harness exits non-zero so CI catches format drift.
BANDS = {
    "first_mover_advantage": (0.40, 0.60),   # attacker-side win rate must sit near even
    "archetype_dominance_max": 0.70,          # no archetype may exceed this win rate
    "powerup_winrate_max": 0.90,              # a hire must not be an auto-win
    "decisive_rate_min": 0.50,                # matches should mostly resolve, not stall
}

# Archetypes, expressed the way a player would build them: as x-arena strategy.
ARCHETYPES = {
    "balanced":   {"attack": 60, "defense": 60},
    "aggressor":  {"attack": 80, "defense": 40},
    "turtle":     {"attack": 40, "defense": 80},
    "glass-cannon": {"attack": 90, "defense": 25},
    "grinder":    {"attack": 55, "defense": 65},
}


def make_bot(base: dict, name: str, strategy: dict) -> dict:
    bot = copy.deepcopy(base)
    bot["metadata"]["name"] = name
    bot.setdefault("extensions", {}).setdefault("x-arena", {})["strategy"] = strategy
    return bot


def round_robin(base: dict, seeds: int, hire: dict | None = None,
                hire_for: str | None = None) -> dict:
    """Every archetype vs every other, across the seed sweep. Returns raw tallies."""
    names = list(ARCHETYPES)
    wins = {n: 0 for n in names}
    played = {n: 0 for n in names}
    side_a_wins = 0
    decisive = 0
    total = 0
    turn_counts = []

    for i, a_name in enumerate(names):
        for b_name in names[i + 1:]:
            a = make_bot(base, a_name, ARCHETYPES[a_name])
            b = make_bot(base, b_name, ARCHETYPES[b_name])
            for s in range(seeds):
                ha = hire if (hire and hire_for == a_name) else None
                hb = hire if (hire and hire_for == b_name) else None
                t = run_vault_match(a, b, seed=s, hire_a=ha, hire_b=hb)
                total += 1
                played[a_name] += 1
                played[b_name] += 1
                turn_counts.append(len(t["turns"]))
                if t["result"] == "decisive":
                    decisive += 1
                if t["winner"] == a_name:
                    wins[a_name] += 1
                    side_a_wins += 1
                elif t["winner"] == b_name:
                    wins[b_name] += 1

    return {
        "total": total,
        "wins": wins,
        "played": played,
        "winRate": {n: (wins[n] / played[n] if played[n] else 0) for n in names},
        "sideAWinRate": side_a_wins / total if total else 0,
        "decisiveRate": decisive / total if total else 0,
        "meanTurns": statistics.mean(turn_counts) if turn_counts else 0,
    }


def mirror_position_bias(base: dict, seeds: int) -> dict:
    """
    Isolate POSITIONAL advantage from archetype strength by running mirror
    matches: identical strategies on both sides. Any deviation from 50% is
    pure slot bias.

    The naive side-A-win-rate over a round robin is confounded, because
    pairings run i<j so side A is always the earlier-listed archetype. This
    is the honest measurement.
    """
    a_wins = decided = 0
    per_archetype = {}
    for name, strat in ARCHETYPES.items():
        a = make_bot(base, name + "-A", strat)
        b = make_bot(base, name + "-B", strat)
        w = d = 0
        for s in range(seeds):
            t = run_vault_match(a, b, seed=s)
            if t["winner"] is None:
                continue
            d += 1
            if t["winner"] == name + "-A":
                w += 1
        per_archetype[name] = w / d if d else 0
        a_wins += w
        decided += d
    return {"sideAWinRate": a_wins / decided if decided else 0,
            "decided": decided, "perArchetype": per_archetype}


def powerup_impact(base: dict, hire: dict, seeds: int) -> dict:
    """Head-to-head across all archetype pairs: solo vs one side hiring."""
    names = list(ARCHETYPES)
    solo_wins = hired_wins = flips = total = 0
    for i, a_name in enumerate(names):
        for b_name in names:
            if a_name == b_name:
                continue
            a = make_bot(base, a_name, ARCHETYPES[a_name])
            b = make_bot(base, b_name, ARCHETYPES[b_name])
            for s in range(seeds):
                solo = run_vault_match(a, b, seed=s)
                hired = run_vault_match(a, b, seed=s, hire_a=hire)
                total += 1
                if solo["winner"] == a_name:
                    solo_wins += 1
                if hired["winner"] == a_name:
                    hired_wins += 1
                if solo["winner"] != hired["winner"]:
                    flips += 1
    return {
        "matches": total,
        "soloWinRate": solo_wins / total,
        "hiredWinRate": hired_wins / total,
        "lift": (hired_wins - solo_wins) / total,
        "flipRate": flips / total,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    base = load_adl(ROOT / "adl" / "antweight-vault-defender.adl.yaml")
    hire = load_adl(ROOT / "adl" / "mercenary-source-auditor.adl.yaml")

    rr = round_robin(base, args.seeds)
    mirror = mirror_position_bias(base, args.seeds)
    pw = powerup_impact(base, hire, max(args.seeds // 4, 25))

    failures = []
    lo, hi = BANDS["first_mover_advantage"]
    # Measured on MIRROR matches: identical strategies, so any deviation from
    # 50% is pure positional bias rather than archetype strength.
    if not lo <= mirror["sideAWinRate"] <= hi:
        failures.append(f"positional bias {mirror['sideAWinRate']:.3f} outside [{lo}, {hi}] "
                        f"(measured on mirror matches)")
    worst = max(rr["winRate"], key=rr["winRate"].get)
    if rr["winRate"][worst] > BANDS["archetype_dominance_max"]:
        failures.append(f"archetype '{worst}' win rate {rr['winRate'][worst]:.3f} "
                        f"> {BANDS['archetype_dominance_max']}")
    if pw["hiredWinRate"] > BANDS["powerup_winrate_max"]:
        failures.append(f"power-up win rate {pw['hiredWinRate']:.3f} "
                        f"> {BANDS['powerup_winrate_max']} — hire is an auto-win")
    if rr["decisiveRate"] < BANDS["decisive_rate_min"]:
        failures.append(f"decisive rate {rr['decisiveRate']:.3f} < {BANDS['decisive_rate_min']}")

    report = {
        "seedsPerPairing": args.seeds,
        "roundRobin": rr,
        "mirrorPositionBias": mirror,
        "powerUp": pw,
        "bands": BANDS,
        "failures": failures,
        "verdict": "BALANCED" if not failures else "OUT-OF-BAND",
    }

    if args.json:
        print(json.dumps(report, indent=2))
        return 1 if failures else 0

    print(f"BALANCE REPORT — {rr['total']:,} matches, {args.seeds} seeds per pairing\n")
    print(f"  archetype win rates")
    for n, wr in sorted(rr["winRate"].items(), key=lambda kv: -kv[1]):
        flag = "  <-- dominant" if wr > BANDS["archetype_dominance_max"] else ""
        print(f"    {n:14s} {wr:6.1%}  ({rr['wins'][n]:,}/{rr['played'][n]:,}){flag}")

    print(f"\n  positional bias (mirror matches) {mirror['sideAWinRate']:6.1%}  "
          f"band [{BANDS['first_mover_advantage'][0]:.0%}–{BANDS['first_mover_advantage'][1]:.0%}]")
    print(f"    {C_DIM}identical strategies both sides, so this is pure slot advantage{C_DIM_END}")
    print(f"  side-A rate over round robin    {rr['sideAWinRate']:6.1%}  "
          f"(confounded by archetype ordering; not a balance signal)")
    print(f"  decisive (non-draw) rate       {rr['decisiveRate']:6.1%}")
    print(f"  mean turns per match           {rr['meanTurns']:6.2f}")

    print(f"\n  power-up impact ({pw['matches']:,} paired matches)")
    print(f"    win rate solo                {pw['soloWinRate']:6.1%}")
    print(f"    win rate with hire           {pw['hiredWinRate']:6.1%}")
    print(f"    lift                         {pw['lift']:+6.1%}")
    print(f"    outcome flip rate            {pw['flipRate']:6.1%}")

    print()
    if failures:
        print("  VERDICT: OUT-OF-BAND")
        for f in failures:
            print(f"    - {f}")
    else:
        print("  VERDICT: BALANCED — all bands satisfied")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
