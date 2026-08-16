#!/usr/bin/env python3
"""Validate Arena ADL documents against the pinned canonical schema (issue A1 / test T-001)."""
import glob, hashlib, json, sys, yaml
from jsonschema import Draft202012Validator

PINNED = "679a5c3ecfb18f80374aff59190456ea51b94f845ee9d84a3e96f419100af0ed"
SCHEMA = "vendor/ADL-v0.2.schema.json"

raw = open(SCHEMA, "rb").read()
digest = hashlib.sha256(raw).hexdigest()
print(f"schema sha256 {digest}")
if digest != PINNED:
    print(f"  T-002 FAIL: schema drifted from pinned {PINNED}")
    sys.exit(1)
print("  T-002 PASS: schema matches pinned hash")

v = Draft202012Validator(json.loads(raw))
rc = 0
for path in sorted(glob.glob("adl/*.yaml")):
    errs = sorted(v.iter_errors(yaml.safe_load(open(path))), key=lambda e: list(e.path))
    status = "PASS" if not errs else "FAIL"
    print(f"  T-001 {status}: {path} ({len(errs)} errors)")
    for e in errs[:10]:
        print(f"      {'/'.join(map(str, e.path)) or '<root>'} :: {e.message[:140]}")
    rc |= bool(errs)

for path in sorted(glob.glob("fixtures/negative/*.yaml")):
    errs = list(v.iter_errors(yaml.safe_load(open(path))))
    # charge-intent fixture is expected to PASS schema — that is the finding.
    note = ("schema-valid (F-001 schema case; the conformance checker "
            "does reject it — see docs/FINDINGS.md)") if not errs else f"{len(errs)} errors"
    print(f"  negative-fixture {path}: {note}")
sys.exit(rc)
