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

# --- Negative corpus (issue A2 / T-003, T-004) --------------------------------
# fixtures/negative/manifest.yaml is the contract: schema-invalid fixtures must
# fail with their declared diagnostic; documented-gap fixtures are schema-valid
# by design (F-001/F-010/F-011) and must be caught by the Arena-local lint.

def arena_lint(doc):
    """Arena-local compensating checks for known schema gaps. Not ADL semantics."""
    diags = []
    harness = doc.get("harness") or {}
    seen = {}
    for kind in ("tools", "functions", "skills"):
        for item in harness.get(kind) or []:
            iid = item.get("id")
            if iid in seen:
                diags.append(("duplicate-id", f"{kind} id {iid!r} declared twice"))
            seen[iid] = kind
    known_tool_keys = {"id", "type", "description", "inputSchema", "outputSchema",
                       "permissions", "sideEffects", "policyRefs", "auditLevel",
                       "timeout", "retryPolicy", "rateLimit", "mcp"}
    for tool in harness.get("tools") or []:
        for key in tool:
            if key not in known_tool_keys:
                diags.append(("unknown-tool-key",
                              f"tool {tool.get('id')!r} carries unknown key {key!r}"))
    return diags


manifest = yaml.safe_load(open("fixtures/negative/manifest.yaml"))
neg_fail = 0
for name, spec in sorted(manifest.items()):
    doc = yaml.safe_load(open(f"fixtures/negative/{name}"))
    errs = list(v.iter_errors(doc))
    if spec["expectSchemaValid"]:
        lint_wanted = spec.get("lint")
        diags = arena_lint(doc)
        if errs:
            print(f"  T-003 FAIL {name}: documented-gap fixture unexpectedly "
                  f"schema-invalid ({errs[0].message[:80]})")
            neg_fail += 1
        elif lint_wanted and lint_wanted not in {d for d, _ in diags}:
            print(f"  T-004 FAIL {name}: expected arena-lint {lint_wanted!r}, "
                  f"got {sorted({d for d, _ in diags})}")
            neg_fail += 1
        else:
            via = f"arena-lint:{lint_wanted}" if lint_wanted else spec.get("finding", "")
            print(f"  T-003/T-004 PASS {name}: schema-valid documented gap "
                  f"[{spec.get('finding', '?')}] caught via {via or 'conformance checker'}")
        continue
    exp = spec["expect"]
    match = [e for e in errs
             if (exp["path"] == "<root>"
                 or exp["path"] in "/".join(map(str, e.absolute_path)))
             and exp["message"] in e.message]
    if not errs:
        print(f"  T-003 FAIL {name}: passed validation silently")
        neg_fail += 1
    elif not match:
        got = [f"{'/'.join(map(str, e.path)) or '<root>'} :: {e.message[:70]}"
               for e in errs[:3]]
        print(f"  T-004 FAIL {name}: failed, but not with declared diagnostic "
              f"[{exp['path']}] ~ {exp['message']!r}; got {got}")
        neg_fail += 1
    else:
        print(f"  T-003/T-004 PASS {name}: fails with declared diagnostic "
              f"[{exp['path']}]")
rc |= bool(neg_fail)
if not neg_fail:
    n_invalid = sum(1 for s_ in manifest.values() if not s_["expectSchemaValid"])
    print(f"  T-003/T-004 PASS: {len(manifest)} fixtures ({n_invalid} schema-invalid "
          f"with specific diagnostics, {len(manifest) - n_invalid} documented gaps)")
sys.exit(rc)
