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
import time
import urllib.error
import urllib.request
from collections import deque, OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

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

# --- Hardening limits for the public surface --------------------------------
# The service is internet-exposed on Railway with a persistent /data volume, so
# every unauthenticated write path is bounded.
MAX_BODY_BYTES = 64 * 1024          # reject oversized request bodies (slowloris/mem)
MAX_WAITLIST_ENTRIES = 100_000      # cap total stored signups (disk exhaustion)
MAX_LEDGER_MATCHES = 10_000         # ring-buffer match history (disk exhaustion)
SIGNUP_RATE_MAX = 20                # per-client signups allowed within the window
FIGHT_RATE_MAX = 60                 # per-client match writes allowed within the window
SIGNUP_RATE_WINDOW = 60.0           # seconds
SOCKET_READ_TIMEOUT = 15.0          # per-connection read timeout
MAX_RATE_KEYS = 20_000              # hard cap on the rate-limit map (LRU-evicted)

# Stores share these across the ThreadingHTTPServer's handler threads: one lock
# serializes the read-modify-write of every JSON store so concurrent requests
# cannot lose entries or observe a half-written file.
_STORE_LOCK = threading.RLock()
# Per-client hit timestamps for a lightweight fixed-window rate limit. The key
# is derived from a spoofable X-Forwarded-For, so the map is an LRU with a HARD
# size cap: an attacker rotating the forwarded value churns their own buckets
# out in O(1) and can never grow the map past MAX_RATE_KEYS (evicting a
# legitimate bucket only fails open — that client simply gets a fresh window).
_RATE_LOCK = threading.Lock()
_SIGNUP_HITS: "OrderedDict[str, deque]" = OrderedDict()


def _read_json(path, default):
    if not path.exists():
        return default
    with open(path) as fh:
        return json.load(fh)


def _write_json_atomic(path, obj):
    """Write via a temp file + os.replace so a concurrent reader never sees a
    truncated file, and a crash mid-write cannot corrupt the store. fsync the
    data and the directory so the persistent-volume durability claim holds
    across a power loss."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    try:
        dir_fd = os.open(str(path.parent), os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except (OSError, AttributeError):
        pass  # directory fsync is best-effort (not all platforms/filesystems)


def safe_adl_path(name):
    """Resolve an ADL filename to a path INSIDE adl/ or return None.

    The caller-supplied bot/hire fields reach open() — without this, an
    absolute path or ../ traversal reads arbitrary files (path traversal /
    DoS via /dev/zero). Only a bare .yaml/.yml file directly in adl/ passes.
    Any malformed name (NUL byte, over-long) resolves to None, never an
    exception — the caller relies on this to return a clean 400.
    """
    adl_dir = (ROOT / "adl").resolve()
    if not isinstance(name, str) or not name or "/" in name or "\\" in name \
            or "\x00" in name or len(name) > 255:
        return None
    try:
        candidate = (adl_dir / name).resolve()
        if candidate.parent != adl_dir or candidate.suffix not in (".yaml", ".yml"):
            return None
        if not candidate.is_file():
            return None
    except (OSError, ValueError):
        return None
    return candidate


def _client_key(handler):
    """Rate-limit key for the real end client. Behind Railway's edge the TCP
    peer (client_address) is a fixed proxy IP, so keying on it makes the
    limit global (20 requests lock out everyone). Prefer the left-most
    X-Forwarded-For hop — the originating client. It is spoofable, so this
    is a courtesy limit, not a security control; the hard bounds (body cap,
    entry cap, ledger cap) do not depend on it."""
    xff = handler.headers.get("X-Forwarded-For", "")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first[:64]
    peer = handler.client_address[0] if handler.client_address else "?"
    return peer[:64]


def _rate_ok(client_key, limit=None):
    """Fixed-window per-client limit for unauthenticated writes. `limit` is
    the cap for the calling endpoint within SIGNUP_RATE_WINDOW; resolved at
    call time so an operator/test override of the module constant applies.

    The hit map is an LRU with a hard size cap: each operation is O(1), and a
    client rotating a spoofed forwarded-for value can never grow it past
    MAX_RATE_KEYS — its own oldest buckets are evicted first."""
    if limit is None:
        limit = SIGNUP_RATE_MAX
    now = time.monotonic()
    with _RATE_LOCK:
        hits = _SIGNUP_HITS.get(client_key)
        if hits is None:
            hits = deque()
            _SIGNUP_HITS[client_key] = hits
            # Hard cap, O(1): drop the least-recently-used bucket(s).
            while len(_SIGNUP_HITS) > MAX_RATE_KEYS:
                _SIGNUP_HITS.popitem(last=False)
        else:
            _SIGNUP_HITS.move_to_end(client_key)  # mark recently used
        while hits and now - hits[0] > SIGNUP_RATE_WINDOW:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True


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

# api.resend.com sits behind Cloudflare, which bans urllib's default
# "Python-urllib/3.x" signature with HTTP 403 "error code: 1010" before the
# request ever reaches Resend. A real User-Agent is required, not cosmetic.
RESEND_USER_AGENT = "reddi-arena/1.0 (+https://github.com/nissan/reddi-arena)"


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


def resend_request(payload, api_key=None):
    """Build the Resend send request, including the Cloudflare-safe UA."""
    key = RESEND_API_KEY if api_key is None else api_key
    return urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json",
                 "Accept": "application/json",
                 "User-Agent": RESEND_USER_AGENT})


def resend_error_detail(exc):
    """Resend puts the actionable reason (unverified domain, bad key, rate
    limit) in the response body; the bare status line says only "Forbidden".
    Bodies carry no credentials, but truncate anyway."""
    try:
        return exc.read().decode("utf-8", "replace").strip()[:300]
    except Exception:
        return ""


def send_waitlist_emails(email, position, roles):
    if not (RESEND_API_KEY and RESEND_FROM):
        return
    payloads = build_waitlist_emails(
        email, position, roles, RESEND_FROM, WAITLIST_NOTIFY_EMAIL)

    def _send():
        for p in payloads:
            try:
                urllib.request.urlopen(resend_request(p), timeout=10)
                print(f"[waitlist] email sent to {mask_email(p['to'][0])}",
                      flush=True)
            except urllib.error.HTTPError as exc:  # log the reason, never raise
                print(f"[waitlist] email to {mask_email(p['to'][0])} "
                      f"failed: HTTP {exc.code} {resend_error_detail(exc)}",
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
    with _STORE_LOCK:
        ledger = _read_json(LEDGER, {"matches": [], "standings": {}})
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
        # Ring-buffer the match history so an unauthenticated /api/fight loop
        # cannot grow the store without bound (standings stay complete — they
        # are O(competitors), not O(matches)).
        if len(ledger["matches"]) > MAX_LEDGER_MATCHES:
            ledger["matches"] = ledger["matches"][-MAX_LEDGER_MATCHES:]
        _write_json_atomic(LEDGER, ledger)
        return ledger


def leaderboard():
    with _STORE_LOCK:
        ledger = _read_json(LEDGER, None)
    if ledger is None:
        return {"matches": 0, "standings": []}
    rows = sorted(ledger["standings"].items(),
                  key=lambda kv: (kv[1]["wins"], kv[1]["credits"]), reverse=True)
    return {"matches": len(ledger["matches"]),
            "standings": [{"name": n, **s} for n, s in rows]}


class Handler(BaseHTTPRequestHandler):
    # Per-connection socket timeout: a slow/stalled client cannot hold a
    # worker thread open indefinitely (slowloris).
    timeout = SOCKET_READ_TIMEOUT

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
        # Header-only: Authorization: Bearer <token>. Query-string secrets leak
        # through proxies, edge logs, and Referer, so they are not accepted.
        # With no ARENA_ADMIN_TOKEN configured, admin routes are
        # indistinguishable from unknown paths (fail closed).
        if not ADMIN_TOKEN:
            return False
        auth = self.headers.get("Authorization", "")
        supplied = auth[7:] if auth.startswith("Bearer ") else ""
        return hmac.compare_digest(supplied, ADMIN_TOKEN)

    def _read_body(self):
        """Read and JSON-parse the request body, bounded. Returns (obj, None)
        or (None, error_response_already_sent_flag)."""
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            self._send({"error": "bad content-length"}, 400)
            return None, True
        if length > MAX_BODY_BYTES:
            self._send({"error": "request too large"}, 413)
            return None, True
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            return json.loads(raw or "{}"), None
        except (ValueError, UnicodeDecodeError):
            self._send({"error": "invalid JSON"}, 400)
            return None, True

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
            with _STORE_LOCK:
                entries = _read_json(WAITLIST, [])
            return self._send({"count": len(entries), "entries": entries,
                               "persistent": PERSISTENT})
        return self._send({"error": "not found"}, 404)

    def _load_bot(self, name):
        """Resolve a caller-supplied ADL filename safely, or None."""
        path = safe_adl_path(name)
        return load_adl(str(path)) if path else None

    def _seed(self, req, default):
        try:
            return int(req.get("seed", default))
        except (TypeError, ValueError):
            return default

    def do_POST(self):
        path = urlparse(self.path).path
        req, err = self._read_body()
        if err:
            return

        if path == "/api/draft":
            comp = self._load_bot(req.get("bot"))
            merc = self._load_bot(req.get("hire"))
            if comp is None or merc is None:
                return self._send({"error": "unknown bot or hire"}, 400)
            res = evaluate_hire(comp, merc, entered_class=req.get("class", "Antweight"))
            return self._send({
                "allowed": res.allowed, "reason": res.reason,
                "soloAU": res.solo_au, "fieldedAU": res.fielded_au, "auDelta": res.au_delta,
                "enteredClass": res.entered_class, "fieldedClass": res.fielded_class,
                "price": res.price,
            })

        if path == "/api/waitlist":
            if not _rate_ok("signup:" + _client_key(self)):
                return self._send({"ok": False, "error": "rate limited"}, 429)
            email = (req.get("email") or "").strip().lower()
            if not isinstance(email, str) or "@" not in email \
                    or "." not in email.split("@")[-1] or len(email) > 254:
                return self._send({"ok": False, "error": "invalid email"}, 400)
            roles = req.get("roles") or ["compete"]
            if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
                return self._send({"ok": False, "error": "invalid roles"}, 400)
            roles = [r[:40] for r in roles[:20]]
            with _STORE_LOCK:
                entries = _read_json(WAITLIST, [])
                existing = next((e for e in entries if e["email"] == email), None)
                if existing:
                    existing["roles"] = sorted(set(existing["roles"]) | set(roles))
                    pos = entries.index(existing) + 1
                elif len(entries) >= MAX_WAITLIST_ENTRIES:
                    return self._send({"ok": False, "error": "waitlist full"}, 503)
                else:
                    entries.append({"email": email, "roles": roles})
                    pos = len(entries)
                _write_json_atomic(WAITLIST, entries)
                total = len(entries)
            if existing is None:  # confirmation email on first signup only
                send_waitlist_emails(email, pos, roles)
            # Masked signup line for the host's deploy logs, so the operator
            # sees activity without polling the file. Full addresses stay in
            # waitlist.json only ("never sold or shared" landing promise).
            print(f"[waitlist] signup {mask_email(email)} "
                  f"roles={','.join(roles)} position={pos} total={total}", flush=True)
            return self._send({"ok": True, "position": pos, "persistent": PERSISTENT})

        if path == "/api/waitlist/remove":
            # Operator-only removal — backs the landing page's deletion
            # promise. Same fail-closed auth as the admin read.
            if not self._admin_ok():
                return self._send({"error": "not found"}, 404)
            email = (req.get("email") or "").strip().lower()
            with _STORE_LOCK:
                entries = _read_json(WAITLIST, [])
                kept = [e for e in entries if e["email"] != email]
                removed = len(entries) - len(kept)
                if removed:
                    _write_json_atomic(WAITLIST, kept)
                    total = len(kept)
            if removed:
                print(f"[waitlist] removed {mask_email(email)} total={total}", flush=True)
            return self._send({"ok": True, "removed": removed})

        if path == "/api/chain":
            a = self._load_bot(req.get("botA"))
            b = self._load_bot(req.get("botB"))
            if a is None or b is None:
                return self._send({"error": "unknown bot"}, 400)
            trace = run_vault_match(a, b, seed=self._seed(req, 2))
            proj = chain.project_match(
                trace, a, b, "OwnerA1111", "OwnerB2222", "Judge3333",
                gates_passed=bool(req.get("gatesPassed", True)),
                attestation_confirmed=bool(req.get("attested", True)))
            proj["auddPlan"] = chain.audd_purse_plan(
                "50.00", "OwnerB2222", "OwnerB2222-settle", "2026-12-31T23:59:59Z")
            return self._send(proj)

        if path == "/api/fight":
            if not _rate_ok("fight:" + _client_key(self), limit=FIGHT_RATE_MAX):
                return self._send({"error": "rate limited"}, 429)
            a = self._load_bot(req.get("botA"))
            b = self._load_bot(req.get("botB"))
            if a is None or b is None:
                return self._send({"error": "unknown bot"}, 400)
            ha = self._load_bot(req["hireA"]) if req.get("hireA") else None
            hb = self._load_bot(req["hireB"]) if req.get("hireB") else None
            if (req.get("hireA") and ha is None) or (req.get("hireB") and hb is None):
                return self._send({"error": "unknown hire"}, 400)
            # An entered class in the request enforces the draft ceiling: an
            # illegal fielding forfeits before turn 1 (audit E7/L2). Absent, the
            # hire plays (backward-compatible).
            ca = req.get("classA") if isinstance(req.get("classA"), str) else None
            cb = req.get("classB") if isinstance(req.get("classB"), str) else None
            trace = run_vault_match(a, b, seed=self._seed(req, 0), hire_a=ha, hire_b=hb,
                                    entered_a=ca, entered_b=cb)
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
