"""
QI Mail Setup — Cloudflare Email Routing + DNS for quiddityinnovations.com
==========================================================================
Creates the inbound mail plumbing for Renne.Santiago@QuiddityInnovations.com.

Idempotent: safe to run repeatedly. Reports what already exists and only
creates what is missing. Never prints the API token.

Usage:
    python C:\\QIH\\tools\\qi_mail_setup.py            # dry run - shows planned changes
    python C:\\QIH\\tools\\qi_mail_setup.py --apply    # actually make the changes

Requires C:\\QIH\\secrets\\cloudflare_dns_email.env with a token scoped:
    Zone:Read, DNS:Edit, Email Routing Rules:Edit, Email Routing Addresses:Edit
"""
import sys
import json
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")

ENV_FILE = r"C:\QIH\secrets\cloudflare_dns_email.env"
ZONE_NAME = "quiddityinnovations.com"
DESTINATION = "Rennesan@gmail.com"

# Addresses to create. Cloudflare normalises the local part to lowercase;
# the address remains case-insensitive for senders, so "Renne.Santiago@..."
# on a business card still delivers here.
ADDRESSES = [
    ("renne.santiago", "Primary business address"),
    ("dmarc", "DMARC aggregate report collector - keeps XML reports filterable"),
]

DMARC_NAME = "_dmarc"
DMARC_VALUE = "v=DMARC1; p=none; rua=mailto:dmarc@quiddityinnovations.com; fo=1"

APPLY = "--apply" in sys.argv

changes_made = []
changes_planned = []


def load_env():
    cfg = {}
    with open(ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


CFG = load_env()
TOKEN = CFG.get("CLOUDFLARE_API_TOKEN", "")
ACCOUNT_ID = CFG.get("CLOUDFLARE_ACCOUNT_ID", "")

if not TOKEN:
    print("[FAIL] No CLOUDFLARE_API_TOKEN in " + ENV_FILE)
    print("       Paste the token after the '=' sign, then re-run.")
    sys.exit(1)


def call(path, method="GET", body=None):
    url = "https://api.cloudflare.com/client/v4" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return json.loads(raw)
        except Exception:
            return {"success": False, "errors": [{"message": raw[:300]}]}
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}


def die(label, resp):
    print("[FAIL] " + label)
    print("       " + json.dumps(resp.get("errors", resp))[:400])
    sys.exit(1)


print("=" * 68)
print("QI MAIL SETUP  -  " + ZONE_NAME)
print("MODE: " + ("APPLY (changes will be made)" if APPLY else "DRY RUN (no changes)"))
print("=" * 68)

# ---------------------------------------------------------------- zone lookup
resp = call("/zones?name=" + ZONE_NAME)
if not resp.get("success"):
    die("Cannot list zones - token likely missing Zone:Read", resp)
if not resp.get("result"):
    print("[FAIL] Token is valid but sees no zone named " + ZONE_NAME)
    print("       Check the token's Zone Resources include this specific zone.")
    sys.exit(1)

zone = resp["result"][0]
ZONE_ID = zone["id"]
if not ACCOUNT_ID:
    ACCOUNT_ID = zone.get("account", {}).get("id", "")
print("[ OK ] Zone found: " + ZONE_NAME)
print("       account: " + str(zone.get("account", {}).get("name")))

# ------------------------------------------------- email routing enabled check
resp = call("/zones/%s/email/routing" % ZONE_ID)
if not resp.get("success"):
    die("Cannot read Email Routing settings - token missing Email Routing Rules", resp)
routing = resp.get("result", {})
if not routing.get("enabled"):
    print("[WARN] Email Routing reports enabled=%s status=%s"
          % (routing.get("enabled"), routing.get("status")))
    print("       MX records are already live, so this is likely a scope quirk.")
else:
    print("[ OK ] Email Routing is enabled (status=%s)" % routing.get("status"))

# ------------------------------------------------------- destination addresses
dest_verified = False
if ACCOUNT_ID:
    resp = call("/accounts/%s/email/routing/addresses" % ACCOUNT_ID)
    if resp.get("success"):
        for r in resp.get("result", []):
            if r.get("email", "").lower() == DESTINATION.lower():
                dest_verified = bool(r.get("verified"))
        print("[ OK ] Destination %s: %s"
              % (DESTINATION, "VERIFIED" if dest_verified else "not yet verified"))
        if not dest_verified:
            print("       -> Cloudflare must email a verification link to this address.")
    else:
        print("[WARN] Cannot read destination addresses (token missing account scope)")
        print("       " + json.dumps(resp.get("errors"))[:200])

# ----------------------------------------------------------------- rules
resp = call("/zones/%s/email/routing/rules" % ZONE_ID)
if not resp.get("success"):
    die("Cannot read routing rules", resp)

existing = {}
print("\n--- Existing routing rules ---")
if not resp.get("result"):
    print("    (none)")
for r in resp.get("result", []):
    matchers = r.get("matchers", [{}])
    actions = r.get("actions", [{}])
    val = matchers[0].get("value", "(catch-all)")
    tgt = actions[0].get("value", [""])
    tgt = tgt[0] if isinstance(tgt, list) and tgt else tgt
    existing[str(val).lower()] = r
    print("    %-45s -> %s" % (val, tgt))

print("\n--- Address rules ---")
for local, purpose in ADDRESSES:
    full = "%s@%s" % (local, ZONE_NAME)
    if full.lower() in existing:
        print("[SKIP] %s already routed" % full)
        continue
    payload = {
        "actions": [{"type": "forward", "value": [DESTINATION]}],
        "matchers": [{"type": "literal", "field": "to", "value": full}],
        "enabled": True,
        "name": purpose,
        "priority": 0,
    }
    if not APPLY:
        print("[PLAN] create %s -> %s" % (full, DESTINATION))
        changes_planned.append(full)
        continue
    r = call("/zones/%s/email/routing/rules" % ZONE_ID, "POST", payload)
    if r.get("success"):
        print("[ OK ] created %s -> %s" % (full, DESTINATION))
        changes_made.append(full)
    else:
        print("[FAIL] %s : %s" % (full, json.dumps(r.get("errors"))[:250]))

# ----------------------------------------------------------------- DMARC
print("\n--- DMARC ---")
resp = call("/zones/%s/dns_records?type=TXT&name=%s.%s" % (ZONE_ID, DMARC_NAME, ZONE_NAME))
if not resp.get("success"):
    die("Cannot read DNS records - token missing DNS:Edit", resp)

if resp.get("result"):
    cur = resp["result"][0]
    print("[SKIP] _dmarc already exists:")
    print("       " + cur.get("content", "")[:160])
else:
    payload = {
        "type": "TXT",
        "name": DMARC_NAME,
        "content": DMARC_VALUE,
        "ttl": 3600,
        "comment": "DMARC monitoring - added by qi_mail_setup.py 2026-08-11",
    }
    if not APPLY:
        print("[PLAN] create TXT _dmarc = " + DMARC_VALUE)
        changes_planned.append("_dmarc")
    else:
        r = call("/zones/%s/dns_records" % ZONE_ID, "POST", payload)
        if r.get("success"):
            print("[ OK ] created TXT _dmarc")
            changes_made.append("_dmarc")
        else:
            print("[FAIL] _dmarc : " + json.dumps(r.get("errors"))[:250])

# ----------------------------------------------------------------- summary
print("\n" + "=" * 68)
if APPLY:
    print("APPLIED: %d change(s): %s" % (len(changes_made), ", ".join(changes_made) or "none"))
    if changes_made:
        print("\nNext: send a test message to renne.santiago@%s" % ZONE_NAME)
else:
    print("DRY RUN: %d change(s) pending: %s"
          % (len(changes_planned), ", ".join(changes_planned) or "none"))
    print("Re-run with --apply to execute.")
print("=" * 68)
