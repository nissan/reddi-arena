#!/usr/bin/env python3
"""
Reddi Arena — web backend.

Thin HTTP layer over the SAME core/arena.py the CLI uses. No game logic lives
here; it only marshals JSON. Stdlib only (http.server) so it runs anywhere with
no install.

Boundaries carry through from the core: dry-run rail, ARENA-CREDIT prizes,
provisional x-arena.price. This server does not call any model provider or
touch any wallet. Its only outbound network call is the optional signup email
via Resend — entirely env-gated (RESEND_API_KEY/RESEND_FROM) and absent by
default, so a bare deploy still reaches no network.
"""

from __future__ import annotations

import glob
import hmac
import json
import os
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from core import chain  # noqa: E402
from core.arena import (  # noqa: E402
    run_vault_match, evaluate_hire, weigh_competitor, advertised_price,
    load_adl, ARENA_CURRENCY, ARENA_RAIL,
)

# Writable data directory. Railway's filesystem is ephemeral unless a volume is
# mounted, so DATA_DIR lets an operator point this at a persistent volume
# (e.g. DATA_DIR=/data with a Railway volume mounted there). Without a volume,
# the leaderboard and waitlist reset on redeploy — stated plainly in the UI.
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "core"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
LEDGER = DATA_DIR / "ledger.json"
WAITLIST = DATA_DIR / "waitlist.json"
PERSISTENT = bool(os.environ.get("DATA_DIR"))

# Operator token for the waitlist admin endpoints. Unset = the endpoints do
# not exist (404), so the deploy fails closed rather than open.
ADMIN_TOKEN = os.environ.get("ARENA_ADMIN_TOKEN", "")


def mask_email(email):
    local, _, domain = email.partition("@")
    return (local[:2] + "***@" + domain) if domain else "***"


# Optional Resend-backed email on new signups. With RESEND_API_KEY or
# RESEND_FROM unset, no email is attempted and no network is reached — signup
# behaves exactly as before. Sending is best-effort in a background thread; a
# Resend failure can never fail or delay the signup response.
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "")  # e.g. "Reddi Arena <arena@example.com>"
WAITLIST_NOTIFY_EMAIL = os.environ.get("WAITLIST_NOTIFY_EMAIL", "")


def build_waitlist_emails(email, position, roles, from_addr, notify_addr):
    """Pure builder for the Resend payloads a new signup produces."""
    msgs = []
    if from_addr:
        msgs.append({
            "from": from_addr,
            "to": [email],
            "subject": "You're on the Reddi Arena early-access list",
            "text": (
                f"You're in — position {position} on the Reddi Arena "
                f"early-access waitlist (roles: {', '.join(roles)}).\n\n"
                "While you wait:\n"
                "- Watch a match and browse the mercenary market: "
                "https://reddi-arena-production.up.railway.app/play\n"
                "- Read the spec your bot will be written in: "
                "https://agent-protocol.reddi.tech/spec\n\n"
                "Prizes are ARENA-CREDIT on the dry-run rail — no real money. "
                "Your address is used only for early-access updates, never "
                "sold or shared; reply to this email to be removed."
            ),
        })
        if notify_addr:
            msgs.append({
                "from": from_addr,
                "to": [notify_addr],
                "subject": f"[arena] waitlist signup #{position}",
                "text": (f"New early-access signup: {email}\n"
                         f"roles: {', '.join(roles)}\n"
                         f"position: {position}"),
            })
    return msgs


def send_waitlist_emails(email, position, roles):
    if not (RESEND_API_KEY and RESEND_FROM):
        return
    payloads = build_waitlist_emails(
        email, position, roles, RESEND_FROM, WAITLIST_NOTIFY_EMAIL)

    def _send():
        for p in payloads:
            try:
                req = urllib.request.Request(
                    "https://api.resend.com/emails",
                    data=json.dumps(p).encode(),
                    headers={"Authorization": f"Bearer {RESEND_API_KEY}",
                             "Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=10)
                print(f"[waitlist] email sent to {mask_email(p['to'][0])}",
                      flush=True)
            except Exception as exc:  # best-effort: log, never raise
                print(f"[waitlist] email to {mask_email(p['to'][0])} "
                      f"failed: {exc}", flush=True)

    threading.Thread(target=_send, daemon=True).start()


def bots():
    out = []
    for path in sorted(glob.glob(str(ROOT / "adl" / "antweight-*.adl.yaml"))):
        d = load_adl(path)
        cert = weigh_competitor(d)
        xa = d.get("extensions", {}).get("x-arena", {})
        out.append({
            "id": Path(path).name,
            "name": d["metadata"]["name"],
            "description": d["metadata"]["description"],
            "au": cert["soloAU"], "class": cert["soloClass"],
            "league": xa.get("league", "rookie"),
            "strategy": xa.get("strategy", {}),
        })
    return out


def mercs():
    out = []
    for path in sorted(glob.glob(str(ROOT / "adl" / "mercenary-*.adl.yaml"))):
        d = load_adl(path)
        cert = weigh_competitor(d)
        price = advertised_price(d)
        xa = d.get("extensions", {}).get("x-arena", {})
        out.append({
            "id": Path(path).name,
            "name": d["metadata"]["name"],
            "description": d["metadata"]["description"],
            "au": cert["soloAU"],
            "price": price, "grants": xa.get("grants", {}),
        })
    return out


def record(trace):
    ledger = json.load(open(LEDGER)) if LEDGER.exists() else {"matches": [], "standings": {}}
    ledger["matches"].append({"competitors": trace["competitors"], "winner": trace["winner"],
                              "seed": trace["seed"], "hash": trace["traceHash"]})
    for name in trace["competitors"]:
        ledger["standings"].setdefault(name, {"wins": 0, "losses": 0, "draws": 0, "credits": 0})
    if trace["winner"]:
        loser = [c for c in trace["competitors"] if c != trace["winner"]][0]
        ledger["standings"][trace["winner"]]["wins"] += 1
        ledger["standings"][trace["winner"]]["credits"] += 10
        ledger["standings"][loser]["losses"] += 1
    else:
        for name in trace["competitors"]:
            ledger["standings"][name]["draws"] += 1
    json.dump(ledger, open(LEDGER, "w"), indent=2)
    return ledger


def leaderboard():
    if not LEDGER.exists():
        return {"matches": 0, "standings": []}
    ledger = json.load(open(LEDGER))
    rows = sorted(ledger["standings"].items(),
                  key=lambda kv: (kv[1]["wins"], kv[1]["credits"]), reverse=True)
    return {"matches": len(ledger["matches"]),
            "standings": [{"name": n, **s} for n, s in rows]}


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200, ctype="application/json"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def _admin_ok(self):
        # Accepts Authorization: Bearer <token> or ?token=<token>. With no
        # ARENA_ADMIN_TOKEN configured, admin routes are indistinguishable
        # from unknown paths.
        if not ADMIN_TOKEN:
            return False
        auth = self.headers.get("Authorization", "")
        supplied = auth[7:] if auth.startswith("Bearer ") else \
            parse_qs(urlparse(self.path).query).get("token", [""])[0]
        return hmac.compare_digest(supplied, ADMIN_TOKEN)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html", "/landing", "/landing.html"):
            page = "landing.html" if path in ("/", "/landing", "/landing.html") else "index.html"
            return self._send((ROOT / "web" / "static" / page).read_bytes(), ctype="text/html")
        if path in ("/play", "/arena", "/app"):
            return self._send((ROOT / "web" / "static" / "index.html").read_bytes(),
                              ctype="text/html")
        if path == "/api/meta":
            return self._send({"currency": ARENA_CURRENCY, "rail": ARENA_RAIL,
                               "persistent": PERSISTENT,
                               "priceNote": "x-arena.price is provisional pending ADL v0.3 (F-007)"})
        if path == "/api/health":
            return self._send({"ok": True, "persistent": PERSISTENT})
        if path == "/api/bots":
            return self._send(bots())
        if path == "/api/market":
            return self._send(mercs())
        if path == "/api/leaderboard":
            return self._send(leaderboard())
        if path == "/api/waitlist":
            # Operator-only read; never exposed without a configured token.
            if not self._admin_ok():
                return self._send({"error": "not found"}, 404)
            entries = json.load(open(WAITLIST)) if WAITLIST.exists() else []
            return self._send({"count": len(entries), "entries": entries,
                               "persistent": PERSISTENT})
        return self._send({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length) or "{}")
        adl_dir = ROOT / "adl"

        if path == "/api/draft":
            comp = load_adl(adl_dir / req["bot"])
            merc = load_adl(adl_dir / req["hire"])
            res = evaluate_hire(comp, merc, entered_class=req.get("class", "Antweight"))
            return self._send({
                "allowed": res.allowed, "reason": res.reason,
                "soloAU": res.solo_au, "fieldedAU": res.fielded_au, "auDelta": res.au_delta,
                "enteredClass": res.entered_class, "fieldedClass": res.fielded_class,
                "price": res.price,
            })

        if path == "/api/waitlist":
            email = (req.get("email") or "").strip().lower()
            if "@" not in email or "." not in email.split("@")[-1]:
                return self._send({"ok": False, "error": "invalid email"}, 400)
            entries = json.load(open(WAITLIST)) if WAITLIST.exists() else []
            existing = next((e for e in entries if e["email"] == email), None)
            if existing:
                existing["roles"] = sorted(set(existing["roles"]) | set(req.get("roles") or []))
                pos = entries.index(existing) + 1
            else:
                entries.append({"email": email, "roles": req.get("roles") or ["compete"]})
                pos = len(entries)
            json.dump(entries, open(WAITLIST, "w"), indent=2)
            if existing is None:  # confirmation email on first signup only
                send_waitlist_emails(email, pos, req.get("roles") or ["compete"])
            # Masked signup line for the host's deploy logs, so the operator
            # sees activity without polling the file. Full addresses stay in
            # waitlist.json only ("never sold or shared" landing promise).
            print(f"[waitlist] signup {mask_email(email)} "
                  f"roles={','.join(req.get('roles') or ['compete'])} "
                  f"position={pos} total={len(entries)}", flush=True)
            return self._send({"ok": True, "position": pos, "persistent": PERSISTENT})

        if path == "/api/waitlist/remove":
            # Operator-only removal — backs the landing page's deletion
            # promise. Same fail-closed auth as the admin read.
            if not self._admin_ok():
                return self._send({"error": "not found"}, 404)
            email = (req.get("email") or "").strip().lower()
            entries = json.load(open(WAITLIST)) if WAITLIST.exists() else []
            kept = [e for e in entries if e["email"] != email]
            removed = len(entries) - len(kept)
            if removed:
                json.dump(kept, open(WAITLIST, "w"), indent=2)
                print(f"[waitlist] removed {mask_email(email)} "
                      f"total={len(kept)}", flush=True)
            return self._send({"ok": True, "removed": removed})

        if path == "/api/chain":
            a = load_adl(adl_dir / req["botA"])
            b = load_adl(adl_dir / req["botB"])
            trace = run_vault_match(a, b, seed=int(req.get("seed", 2)))
            proj = chain.project_match(
                trace, a, b, "OwnerA1111", "OwnerB2222", "Judge3333",
                gates_passed=bool(req.get("gatesPassed", True)),
                attestation_confirmed=bool(req.get("attested", True)))
            proj["auddPlan"] = chain.audd_purse_plan(
                "50.00", "OwnerB2222", "OwnerB2222-settle", "2026-12-31T23:59:59Z")
            return self._send(proj)

        if path == "/api/fight":
            a = load_adl(adl_dir / req["botA"])
            b = load_adl(adl_dir / req["botB"])
            ha = load_adl(adl_dir / req["hireA"]) if req.get("hireA") else None
            hb = load_adl(adl_dir / req["hireB"]) if req.get("hireB") else None
            trace = run_vault_match(a, b, seed=int(req.get("seed", 0)), hire_a=ha, hire_b=hb)
            record(trace)
            return self._send(trace)

        return self._send({"error": "not found"}, 404)


def main():
    # PORT is injected by the host (Railway); argv is the local override.
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"Reddi Arena listening on {host}:{port}  "
          f"(dry-run rail, ARENA-CREDIT prizes, persistent={PERSISTENT})", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
