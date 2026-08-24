#!/usr/bin/env python3
"""
Reddi Arena CLI — `arena`

Get into a competition arena from the terminal:

    arena validate  <bot.yaml>              schema + conformance
    arena weigh     <bot.yaml> [--hire M]   weight class and AU breakdown
    arena market                            browse power-up specialists for hire
    arena draft     <bot.yaml> --hire M --class Antweight
    arena fight     <botA> <botB> [--hire-a M] [--seed N]
    arena replay    <trace.json>            annotated, turn-by-turn learning view
    arena leaderboard                       standings from played matches

Prizes are ARENA-CREDIT on the x402-dry-run rail. No real value, no live rail.
Specialist prices use the provisional x-arena.price extension (finding F-007).
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from core import chain  # noqa: E402
from core.arena import (  # noqa: E402
    run_vault_match, evaluate_hire, weigh_competitor, advertised_price,
    load_adl, LEAGUE_TIERS, ARENA_CURRENCY, ARENA_RAIL,
)

LEDGER = ROOT / "core" / "ledger.json"


# ------------------------------- styling ----------------------------------
class C:
    B = "\033[1m"; DIM = "\033[2m"; R = "\033[0m"
    G = "\033[32m"; Y = "\033[33m"; RED = "\033[31m"; CY = "\033[36m"; MAG = "\033[35m"

    @staticmethod
    def off():
        for k in ("B", "DIM", "R", "G", "Y", "RED", "CY", "MAG"):
            setattr(C, k, "")


if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
    C.off()


def bar(value: int, lo: int, hi: int, width: int = 24) -> str:
    span = max(hi - lo, 1)
    filled = max(0, min(width, round((value - lo) / span * width)))
    return "█" * filled + "·" * (width - filled)


# ------------------------------- commands ---------------------------------
def cmd_validate(args):
    import subprocess
    bundle = Path("/tmp/bundle/adl-v0.2.0-beta")
    doc = load_adl(args.bot)
    name = doc["metadata"]["name"]
    print(f"{C.B}{name}{C.R}")
    # schema
    import yaml
    from jsonschema import Draft202012Validator
    schema = json.load(open(ROOT / "vendor" / "ADL-v0.2.schema.json"))
    errs = list(Draft202012Validator(schema).iter_errors(doc))
    if errs:
        print(f"  {C.RED}schema: {len(errs)} error(s){C.R}")
        for e in errs[:8]:
            print(f"    {'/'.join(map(str, e.path)) or '<root>'} :: {e.message[:120]}")
        return 1
    print(f"  {C.G}schema: valid{C.R}")
    # conformance (if bundle present)
    checker = bundle / "scripts" / "adl_v02_conformance.py"
    if checker.exists():
        out = subprocess.run([sys.executable, str(checker), str(Path(args.bot).resolve())],
                             cwd=bundle, capture_output=True, text=True).stdout
        try:
            r = json.loads(out)[0]
            col = C.G if r["status"] == "pass" else C.RED
            print(f"  {col}conformance: L{r['achievedLevel']}/{r['requestedLevel']} {r['status']}{C.R}")
        except Exception:
            print(f"  {C.DIM}conformance: checker output unparsed{C.R}")
    else:
        print(f"  {C.DIM}conformance: bundle not present, skipped{C.R}")
    league = (doc.get("extensions", {}).get("x-arena", {}) or {}).get("league")
    if league:
        print(f"  {C.CY}league:{C.R} {league}")
    return 0


def cmd_weigh(args):
    doc = load_adl(args.bot)
    hires = [load_adl(h) for h in (args.hire or [])]
    cert = weigh_competitor(doc, hires)
    print(f"{C.B}WEIGH-IN{C.R}  {cert['agent']}")
    for row in cert["breakdown"]:
        sign = C.G if row["au"] < 0 else C.R
        print(f"  {sign}{row['au']:>5}{C.R}  {C.DIM}{row['item']}{C.R}")
    print(f"  {'-'*34}")
    print(f"  solo    {C.B}{cert['soloAU']:>4} AU{C.R}  {cert['soloClass']}")
    if hires:
        col = C.Y if cert["classBumped"] else C.R
        print(f"  fielded {col}{cert['fieldedAU']:>4} AU{C.R}  {cert['fieldedClass']}"
              + (f"  {C.Y}CLASS BUMP{C.R}" if cert["classBumped"] else ""))
    print(f"  {C.DIM}hash {cert['capabilityHash'][:23]}…{C.R}")
    return 0


def cmd_market(args):
    print(f"{C.B}POWER-UP MARKET{C.R}  {C.DIM}specialists for hire — prices in {ARENA_CURRENCY} "
          f"on {ARENA_RAIL}{C.R}")
    print(f"{C.DIM}  prices use the provisional x-arena.price extension (F-007){C.R}\n")
    listings = sorted(glob.glob(str(ROOT / "adl" / "mercenary-*.adl.yaml")))
    if not listings:
        print("  (no specialists listed yet)")
        return 0
    for path in listings:
        m = load_adl(path)
        cert = weigh_competitor(m)
        price = advertised_price(m)
        xa = m.get("extensions", {}).get("x-arena", {})
        grants = xa.get("grants", {})
        amt = price["amount"]
        print(f"  {C.MAG}{m['metadata']['name']}{C.R}")
        print(f"    {m['metadata']['description'][:76]}")
        pv = f"{amt} {price['currency']} {price.get('unit','')}" if amt is not None else "unpriced"
        print(f"    price {C.CY}{pv}{C.R} {C.DIM}(provisional){C.R}   solo {cert['soloAU']} AU")
        if grants:
            print(f"    grants: {C.G}+{grants.get('defenseBonus','?')} defense{C.R} — "
                  f"{grants.get('capability','')}")
        print()
    return 0


def cmd_draft(args):
    comp = load_adl(args.bot)
    merc = load_adl(args.hire)
    res = evaluate_hire(comp, merc, entered_class=args._class)
    head = f"{C.G}ALLOWED{C.R}" if res.allowed else f"{C.RED}REFUSED{C.R}"
    print(f"{C.B}DRAFT{C.R}  {comp['metadata']['name']} + {merc['metadata']['name']}  [{head}]")
    print(f"  {res.solo_au} AU solo  ->  {res.fielded_au} AU fielded  (+{res.au_delta})")
    print(f"  entered {res.entered_class}  ->  fielded {res.fielded_class}")
    print(f"  price {C.CY}{res.price['amount']} {res.price['currency']}{C.R} {C.DIM}(provisional){C.R}")
    print(f"  {res.reason}")
    return 0 if res.allowed else 2


def cmd_fight(args):
    a = load_adl(args.bot_a)
    b = load_adl(args.bot_b)
    hire_a = load_adl(args.hire_a) if args.hire_a else None
    hire_b = load_adl(args.hire_b) if args.hire_b else None
    # When an entered class is stated, run_vault_match enforces the draft
    # class ceiling — an illegal fielding forfeits before turn 1 (audit E7/L2).
    trace = run_vault_match(a, b, seed=args.seed, hire_a=hire_a, hire_b=hire_b,
                            entered_a=getattr(args, "class_a", None),
                            entered_b=getattr(args, "class_b", None))

    print(f"{C.B}VAULT MATCH{C.R}  {trace['competitors'][0]} {C.DIM}vs{C.R} {trace['competitors'][1]}"
          f"  {C.DIM}seed {trace['seed']}{C.R}")
    if hire_a:
        print(f"  {C.MAG}{trace['competitors'][0]} powered up with {hire_a['metadata']['name']}{C.R}")
    if hire_b:
        print(f"  {C.MAG}{trace['competitors'][1]} powered up with {hire_b['metadata']['name']}{C.R}")
    print()
    for t in trace["turns"]:
        icon = {"extract": "⚔", "probe": "·", "sputter": "✗"}.get(t["strategy"], "·")
        res = f"{C.RED}EXTRACTED{C.R}" if t["outcome"] == "extracted" else f"{C.DIM}held{C.R}"
        if t["strategy"] == "sputter":
            print(f"  t{t['n']:>2} {icon} {t['attacker']} {C.Y}out of fuel{C.R}")
        else:
            print(f"  t{t['n']:>2} {icon} {t['attacker'][:24]:24s} probe {t['probe_strength']:>3} "
                  f"vs def {t['defense_strength']:>3}  {res}")
    print()
    if trace["winner"]:
        print(f"  {C.G}{C.B}WINNER: {trace['winner']}{C.R}  — {trace['reason']}")
    else:
        print(f"  {C.Y}DRAW{C.R} — {trace['reason']}")
    print(f"  {C.DIM}prize pool paid in {trace['prizeCurrency']} on {trace['rail']}{C.R}")

    if args.out:
        json.dump(trace, open(args.out, "w"), indent=2)
        print(f"  {C.DIM}trace -> {args.out}{C.R}")
    _record(trace)
    return 0


def cmd_replay(args):
    trace = json.load(open(args.trace))
    print(f"{C.B}REPLAY{C.R}  {trace['competitors'][0]} vs {trace['competitors'][1]}  "
          f"{C.DIM}seed {trace['seed']} · hash {trace['traceHash'][:16]}…{C.R}\n")
    print(f"  {C.B}Pit-crew read{C.R}")
    turns = trace["turns"]
    decisive = turns[-1]
    if decisive["strategy"] == "extract":
        loser = [c for c in trace["competitors"] if c != trace["winner"]][0]
        print(f"  The match turned on turn {decisive['n']}: {decisive['attacker']}'s probe "
              f"({decisive['probe_strength']}) beat the defense ({decisive['defense_strength']}).")
        print(f"  {C.CY}Lesson for {loser}:{C.R} your defense was {decisive['defense_strength']} "
              f"when the winning probe was {decisive['probe_strength']}. A source-auditor hire "
              f"adds +15 defense — enough to flip a margin this close. Try `arena market`.")
    elif decisive["strategy"] == "sputter":
        print(f"  {decisive['attacker']} ran out of fuel on turn {decisive['n']}. "
              f"{C.CY}Lesson:{C.R} raise contextWindow (your fuel cap) or spend probes more slowly.")
    else:
        print(f"  Went the distance. Decided on fuel efficiency. "
              f"{C.CY}Lesson:{C.R} tighten your token budget to win these.")
    print(f"\n  {C.DIM}every line above maps to a recorded turn; nothing inferred beyond the trace{C.R}")
    return 0


def cmd_chain(args):
    """Show exactly what a match WOULD write on-chain. Writes nothing."""
    a = load_adl(ROOT / "adl" / args.bot_a)
    b = load_adl(ROOT / "adl" / args.bot_b)
    trace = run_vault_match(a, b, seed=args.seed)
    proj = chain.project_match(trace, a, b, args.owner_a, args.owner_b, args.judge,
                               gates_passed=not args.fail_gate,
                               attestation_confirmed=not args.no_attest)
    print(f"{C.B}CHAIN PROJECTION{C.R}  {C.DIM}{proj['mode']} — nothing is submitted{C.R}\n")

    print(f"  {C.B}Registry{C.R}  {C.DIM}{proj['programs']['registry'][:20]}…{C.R}")
    for r in proj["registrations"]:
        ar = r["args"]
        print(f"    register_agent  {ar['agent_type']:9s} {ar['model']:18s} "
              f"rate {ar['rate_lamports']:>10} lamports")
        for w in r["warnings"]:
            print(f"      {C.Y}! {w}{C.R}")

    e = proj["escrow"]
    print(f"\n  {C.B}Escrow{C.R}  {C.DIM}{proj['programs']['escrow'][:20]}…{C.R}")
    print(f"    lock_escrow  {e['args']['amount']:,} lamports  status {e['status']}")

    at = proj["attestation"]
    print(f"\n  {C.B}Attestation{C.R}  {C.DIM}{proj['programs']['attestation'][:20]}…{C.R}")
    print(f"    attest_quality  scores {at['args']['scores']}")

    s_ = proj["settlement"]
    col = C.G if s_["decision"] == "release" else C.Y
    print(f"\n  {C.B}Settlement{C.R}")
    print(f"    transport ok={s_['inputs']['transportOk']}  gates={s_['inputs']['requiredGatesPassed']}"
          f"  attested={s_['inputs']['attestationConfirmed']}")
    print(f"    -> {col}{s_['decision'].upper()}{C.R} via {s_['instruction']}")
    print(f"    {C.DIM}{s_['reason']}{C.R}")

    print(f"\n  {C.B}Commit-reveal rating{C.R}  {C.DIM}{proj['rating']['scheme']}{C.R}")
    for st in proj["rating"]["steps"]:
        if "commitment" in st:
            print(f"    commit  {st['by']:20s} {st['commitment'][:20]}…")
        else:
            ok = f"{C.G}verified{C.R}" if st["verifies"] else f"{C.RED}MISMATCH{C.R}"
            print(f"    reveal  {st['by']:20s} score {st['score']}  {ok}")

    fp = proj["onChainFootprint"]
    print(f"\n  {C.B}On-chain footprint{C.R}")
    print(f"    {C.G}written{C.R}     {', '.join(fp['written'][:3])}…")
    print(f"    {C.RED}not written{C.R} {', '.join(fp['notWritten'][:3])}…")

    if args.audd:
        plan = chain.audd_purse_plan(args.audd, args.owner_b, args.owner_b + "-settle",
                                     "2026-12-31T23:59:59Z")
        print(f"\n  {C.B}AUDD purse plan{C.R}  {C.DIM}{plan['schemaVersion']}{C.R}")
        print(f"    {plan['amount']} AUDD on {plan['network']}  mode {C.Y}{plan['paymentMode']}{C.R}")
        print(f"    failure {plan['failurePolicy']['mode']} · refund {plan['refundPolicy']['mode']}")
        print(f"    {C.DIM}{plan['_boundary']}{C.R}")

    if args.out:
        json.dump(proj, open(args.out, "w"), indent=2)
        print(f"\n  {C.DIM}projection -> {args.out}{C.R}")
    print(f"\n  {C.Y}Nothing was submitted.{C.R} {C.DIM}Devnet writes need explicit operator "
          f"approval with scoped wallet, tx count, and spend cap.{C.R}")
    return 0


def _record(trace):
    ledger = json.load(open(LEDGER)) if LEDGER.exists() else {"matches": [], "standings": {}}
    ledger["matches"].append({
        "competitors": trace["competitors"], "winner": trace["winner"],
        "seed": trace["seed"], "hash": trace["traceHash"],
    })
    for name in trace["competitors"]:
        s = ledger["standings"].setdefault(name, {"wins": 0, "losses": 0, "draws": 0, "credits": 0})
    if trace["winner"]:
        loser = [c for c in trace["competitors"] if c != trace["winner"]][0]
        ledger["standings"][trace["winner"]]["wins"] += 1
        ledger["standings"][trace["winner"]]["credits"] += 10
        ledger["standings"][loser]["losses"] += 1
    else:
        for name in trace["competitors"]:
            ledger["standings"][name]["draws"] += 1
    json.dump(ledger, open(LEDGER, "w"), indent=2)


def cmd_leaderboard(args):
    if not LEDGER.exists():
        print("No matches played yet. Run `arena fight`.")
        return 0
    ledger = json.load(open(LEDGER))
    rows = sorted(ledger["standings"].items(),
                  key=lambda kv: (kv[1]["wins"], kv[1]["credits"]), reverse=True)
    print(f"{C.B}LEADERBOARD{C.R}  {C.DIM}{len(ledger['matches'])} matches · "
          f"credits in {ARENA_CURRENCY}{C.R}\n")
    print(f"  {'#':>2} {'bot':30s} {'W':>3} {'L':>3} {'D':>3} {'credits':>8}")
    for i, (name, s) in enumerate(rows, 1):
        print(f"  {i:>2} {name[:30]:30s} {s['wins']:>3} {s['losses']:>3} {s['draws']:>3} "
              f"{C.CY}{s['credits']:>8}{C.R}")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="arena", description="Reddi Arena")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate"); p.add_argument("bot"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("weigh"); p.add_argument("bot"); p.add_argument("--hire", action="append")
    p.set_defaults(fn=cmd_weigh)
    p = sub.add_parser("market"); p.set_defaults(fn=cmd_market)
    p = sub.add_parser("draft"); p.add_argument("bot"); p.add_argument("--hire", required=True)
    p.add_argument("--class", dest="_class", default="Antweight"); p.set_defaults(fn=cmd_draft)
    p = sub.add_parser("fight"); p.add_argument("bot_a"); p.add_argument("bot_b")
    p.add_argument("--hire-a", dest="hire_a"); p.add_argument("--hire-b", dest="hire_b")
    p.add_argument("--class-a", dest="class_a",
                   help="entered class for A; enforces the draft ceiling on --hire-a")
    p.add_argument("--class-b", dest="class_b",
                   help="entered class for B; enforces the draft ceiling on --hire-b")
    p.add_argument("--seed", type=int, default=0); p.add_argument("--out")
    p.set_defaults(fn=cmd_fight)
    p = sub.add_parser("replay"); p.add_argument("trace"); p.set_defaults(fn=cmd_replay)
    p = sub.add_parser("leaderboard"); p.set_defaults(fn=cmd_leaderboard)
    p = sub.add_parser("chain", help="show what a match would write on-chain (writes nothing)")
    p.add_argument("bot_a"); p.add_argument("bot_b")
    p.add_argument("--seed", type=int, default=2)
    p.add_argument("--owner-a", dest="owner_a", default="OwnerA1111")
    p.add_argument("--owner-b", dest="owner_b", default="OwnerB2222")
    p.add_argument("--judge", default="Judge3333")
    p.add_argument("--audd", help="also emit an AUDD purse plan for this amount, e.g. 50.00")
    p.add_argument("--fail-gate", action="store_true", help="simulate a failed required eval gate")
    p.add_argument("--no-attest", action="store_true", help="simulate attestation not confirmed")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_chain)

    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
