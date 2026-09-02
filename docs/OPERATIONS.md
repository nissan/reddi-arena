# Reddi Arena — operations

Operator runbook for the deployed preview at
https://reddi-arena-production.up.railway.app. Covers the early-access
waitlist, its admin endpoints, signup email, and the deploy gotchas that cost
real debugging time.

Nothing here is required to run the Arena locally — see `QUICKSTART.md` for
that. Every variable below is optional, and the service degrades cleanly
without it.

## Environment variables

| Variable | Effect if unset | Notes |
|---|---|---|
| `DATA_DIR` | Stores land in `core/`, which is **wiped on every redeploy** | Set to `/data` with a Railway volume mounted at the same path. `GET /api/meta` and `/api/health` report `persistent: true` only when this is set. |
| `ARENA_ADMIN_TOKEN` | Waitlist admin endpoints return **404** | Fails closed: with no token the routes are indistinguishable from unknown paths, so a misconfigured deploy cannot leak signups. |
| `RESEND_API_KEY` | No signup email is attempted, and the service makes **no outbound network calls at all** | From resend.com. |
| `RESEND_FROM` | Same as above — both this and the key are required before anything sends | Must be on a **Resend-verified domain**, e.g. `Reddi Arena <arena@example.com>`. |
| `WAITLIST_NOTIFY_EMAIL` | No operator notification (the signee still gets their confirmation) | Where "someone signed up" notices go. |
| `REDDI_ENABLE_SOLANA_DEVNET_ASSURANCE_PREVIEW` | The Solana Devnet Preview is **absent**: `/play` omits its tab and panel, and `/api/assurance` returns 404 | Fails closed. Only the exact values `true` or `1` enable it — `True`, `yes`, `on`, and `" true"` do not. **Not sufficient on its own**: the deployment context below must also be declared. Boundaries in `docs/DEVNET-PREVIEW-RAP-ASSURANCE.md`. |
| `REDDI_SOLANA_DEVNET_ASSURANCE_DEPLOYMENT_CONTEXT` | Reads as `off`, so the preview stays absent even with the flag set to `true` | Closed set: `off`, `local`, `hosted`. Anything else — empty, `Local`, `prod`, a typo — reads as `off`. The declaration is what makes the preview's `externalDeployment` boundary flag truthful (`local` → `false`, `hosted` → `true`); with no declaration the flag is not emitted at all. **Setting `hosted` on this internet-facing service publicly exposes the preview and is a separately approved action with reviewed messaging.** |

## Waitlist

Signups are stored as JSON in `$DATA_DIR/waitlist.json`. Full addresses live
there and nowhere else — logs mask them (`ni***@example.com`), and the landing
page promises they are never sold or shared.

### Read the list (operator only)

```bash
curl -H "Authorization: Bearer $ARENA_ADMIN_TOKEN" \
  https://reddi-arena-production.up.railway.app/api/waitlist
# {"count": 3, "entries": [{"email": "...", "roles": ["compete"]}], "persistent": true}
```

`?token=` works too, for a browser. Auth is a constant-time compare.

### Remove someone (operator only)

Backs the landing page's deletion promise — use it when somebody asks off.

```bash
curl -X POST -H "Authorization: Bearer $ARENA_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"someone@example.com"}' \
  https://reddi-arena-production.up.railway.app/api/waitlist/remove
# {"ok": true, "removed": 1}
```

### Noticing signups without polling

Every signup and removal prints a masked line to stdout, visible in the Railway
deploy logs:

```
[waitlist] signup ni***@reddi.tech roles=compete,build position=1 total=1
[waitlist] email sent to ni***@reddi.tech
```

## Signup email

On a **first** signup (role merges on an existing address stay silent) the
service sends, via Resend:

1. a confirmation to the signee — queue position, roles, the
   ARENA-CREDIT/dry-run disclosure, and a reply-to-remove path;
2. an operator notice to `WAITLIST_NOTIFY_EMAIL`, if set.

Sending is **best-effort in a background thread with a 10s timeout**: a Resend
outage, a bad key, or an unverified domain can never fail or delay the signup
response. Failures log the status code *and* the response body, which is where
the actionable reason lives.

### Gotcha: Cloudflare bans the default urllib User-Agent

`api.resend.com` sits behind Cloudflare, which rejects urllib's default
`Python-urllib/3.x` signature with `HTTP 403 error code: 1010` — **before the
request reaches Resend**. The symptom is indistinguishable from an auth or
domain problem unless you read the body.

`RESEND_USER_AGENT` in `web/server.py` exists solely to defeat this, and
`tests/test_arena.py` asserts the header is present and is not `Python-urllib`.
Do not "tidy it away".

### Gotcha: "domain is not verified" means added ≠ verified

Publishing the DNS records is not enough — Resend must also *check* them. If
sends fail with:

```
HTTP 403 {"statusCode":403,"message":"The reddi.tech domain is not verified..."}
```

open https://resend.com/domains and click **Verify DNS Records**. Confirm the
records resolve first (no `dig` needed):

```bash
curl -s "https://dns.google/resolve?name=resend._domainkey.YOURDOMAIN&type=TXT"
curl -s "https://dns.google/resolve?name=send.YOURDOMAIN&type=MX"
```

## Deploying

**This service does not auto-deploy on push.** Merging to `main` does *not*
ship — merged fixes have sat undeployed for hours more than once. Either press
**Deploy** in the Railway dashboard, or enable deploy-on-push in the service's
source settings (recommended; it removes this whole failure mode).

Note that Railway's *Redeploy* action **reuses the previous build**, so it
cannot pick up a new commit. Changing any variable to a new value does force a
fresh build from `main` — a useful lever, but a blunt one.

Attaching or detaching the volume also triggers a redeploy. That is safe once
`/data` is mounted; before it was, a redeploy wiped the waitlist.

A redeploy never turns on the Solana Devnet Preview by itself: neither
`Dockerfile` nor `railway.json` sets the flag above, so unless it has been added
to this service's variables the preview stays absent across builds.

## Backups

The waitlist is backed up daily to a Google Drive folder ("Reddi Arena Waitlist
Backups") by a scheduled agent routine, which writes a new timestamped snapshot
only when the entries change. The Railway volume is the durability guarantee;
Drive is the offline archive behind it.
