#!/usr/bin/env python3
"""Claims-discipline copy lint over public Arena surfaces (issue F4).

T-094: no public surface claims audit completion, mainnet readiness, or
production status. Assertive phrases are banned; the same words inside an
explicit negation ("makes no claim ... of production readiness") are the
disclosure the discipline *wants*, so negated lines are exempt. The Railway
domain contains the word "production" and is allowlisted as a hostname, not
a claim.

T-095: capability claims cite evidence — the README carries a release-state
banner that names the test suite and CI, and the landing page carries its
suite-asserted disclosures.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent

SURFACES = (
    [ROOT / "README.md", ROOT / "QUICKSTART.md"]
    + sorted((ROOT / "tutorials").glob("*.md"))
    + sorted((ROOT / "web" / "static").glob("*.html"))
)

BANNED = [
    r"fully\s+audited", r"security\s+audit\s+(passed|complete)",
    r"audit\s+complete", r"mainnet[-\s]ready", r"production[-\s]ready",
    r"production[-\s]grade", r"enterprise[-\s](ready|grade)",
    r"battle[-\s]tested",
]
NEGATION = re.compile(r"no claim|makes no|not\b|never\b|nothing here|without\b",
                      re.I)
ALLOWLIST = ["reddi-arena-production.up.railway.app"]

errors = []

for path in SURFACES:
    text = path.read_text()
    for allowed in ALLOWLIST:
        text = text.replace(allowed, "")
    for lineno, line in enumerate(text.splitlines(), 1):
        for pattern in BANNED:
            if re.search(pattern, line, re.I) and not NEGATION.search(line):
                errors.append(f"T-094 {path.relative_to(ROOT)}:{lineno}: "
                              f"assertive claim matches banned /{pattern}/: "
                              f"{line.strip()[:80]}")

readme = (ROOT / "README.md").read_text()
if "**Release state:**" not in readme:
    errors.append("T-095 README.md: release-state banner missing")
else:
    banner = readme.split("**Release state:**", 1)[1].split("\n\n", 1)[0]
    if "tests/test_arena.py" not in banner or "CI" not in banner:
        errors.append("T-095 README.md: release-state banner must cite the "
                      "test suite and CI as its evidence")
landing = (ROOT / "web" / "static" / "landing.html").read_text()
for marker in ("x402-dry-run", "no claim of security audit"):
    if marker not in landing:
        errors.append(f"T-095 landing.html: required disclosure {marker!r} missing")

if errors:
    print("CLAIMS LINT FAIL")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"CLAIMS LINT PASS — {len(SURFACES)} public surfaces, "
      f"{len(BANNED)} banned patterns, banner + disclosures present")
