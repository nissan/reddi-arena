#!/usr/bin/env python3
"""Generate the Arena negative-fixture corpus (issue A2 / tests T-003, T-004).

Each fixture is the reference defender document with exactly ONE targeted
break, so it fails validation for the stated reason and nothing else. The
generator verifies every expectation against the pinned schema at generation
time and refuses to write a corpus that does not behave as declared, then
emits fixtures/negative/manifest.yaml — the contract tools/validate_adl.py
and tests/test_arena.py assert against.

Two fixtures are deliberately schema-VALID: they document gaps where the
schema accepts a document it plausibly should not (F-010 duplicate ids,
F-011 unknown keys on security-relevant tool objects — see docs/FINDINGS.md).
For those the Arena-local lint in validate_adl.py supplies the diagnostic.

Boundary (A2): fixtures are review artifacts; they do not define new ADL
semantics. The lint checks are Arena-local compensating controls.
"""
import copy
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "adl" / "antweight-vault-defender.adl.yaml"
OUT = ROOT / "fixtures" / "negative"
SCHEMA = ROOT / "vendor" / "ADL-v0.2.schema.json"

KEEP = {"charge-intent-unbounded.yaml"}  # pre-existing F-001 fixture


def mutations():
    """(fixture-id, reason, expected-path-fragment, expected-message-fragment,
    expect_schema_valid, lint-diagnostic-or-None, mutator)"""

    def m(fn):
        return fn

    return [
        ("missing-apiversion", "apiVersion is required at the root",
         "<root>", "'apiVersion' is a required property", False, None,
         m(lambda d: d.pop("apiVersion"))),
        ("wrong-kind", "kind must be the constant 'Agent'",
         "kind", "'Agent' was expected", False, None,
         m(lambda d: d.update(kind="Robot"))),
        ("metadata-name-uppercase", "metadata.name must match the lowercase slug pattern",
         "metadata/name", "does not match", False, None,
         m(lambda d: d["metadata"].update(name="VaultDefender"))),
        ("metadata-missing-description", "metadata.description is required",
         "metadata", "'description' is a required property", False, None,
         m(lambda d: d["metadata"].pop("description"))),
        ("missing-model", "model is required at the root",
         "<root>", "'model' is a required property", False, None,
         m(lambda d: d.pop("model"))),
        ("model-missing-requirements", "model.requirements is required",
         "model", "'requirements' is a required property", False, None,
         m(lambda d: d["model"].pop("requirements"))),
        ("modality-undeclared-enum", "modalities are a closed enum",
         "model/requirements/modalities/0", "is not one of", False, None,
         m(lambda d: d["model"]["requirements"].update(modalities=["telepathy"]))),
        ("bare-string-instructions", "instructions must be an object, not a bare string (D-01 class)",
         "harness/instructions", "is not of type 'object'", False, None,
         m(lambda d: d["harness"].update(instructions="You are a vault defender."))),
        ("instructions-inline-and-path", "instructions must choose inline OR path, not both",
         "harness/instructions", "is not valid under any of the given schemas", False, None,
         m(lambda d: d["harness"]["instructions"].update(inline="also inline"))),
        ("harness-missing-runtime", "harness.runtime is required (D-15)",
         "harness", "'runtime' is a required property", False, None,
         m(lambda d: d["harness"].pop("runtime"))),
        ("tool-dotted-id", "ids may not contain dots (D-04)",
         "harness/tools/0/id", "does not match", False, None,
         m(lambda d: d["harness"]["tools"][0].update(id="vault.seal"))),
        ("tool-missing-description", "tool.description is required",
         "harness/tools/0", "'description' is a required property", False, None,
         m(lambda d: d["harness"]["tools"][0].pop("description"))),
        ("source-file-missing-path", "type:file sources require a separate path (D-07)",
         "harness/dataSources/0", "'path' is a required property", False, None,
         m(lambda d: d["harness"]["dataSources"][0].pop("path"))),
        ("source-ref-prefix-mismatch", "sourceRef must carry the file: prefix for file sources (D-07)",
         "harness/dataSources/0/sourceRef", "does not match", False, None,
         m(lambda d: d["harness"]["dataSources"][0].update(
             sourceRef="./fixtures/vault/match-brief.md"))),
        ("source-citation-as-string", "citationRequired is a boolean, not a keyword (D-05)",
         "harness/dataSources/0/citationRequired", "is not of type 'boolean'", False, None,
         m(lambda d: d["harness"]["dataSources"][0].update(citationRequired="required"))),
        ("source-check-as-string", "sourceCheck is an object with required/expectation (D-06)",
         "harness/dataSources/0/sourceCheck", "is not of type 'object'", False, None,
         m(lambda d: d["harness"]["dataSources"][0].update(sourceCheck="required"))),
        ("memory-retention-object", "memory.retention is a string; scope is separate (D-12)",
         "harness/memory/retention", "is not of type 'string'", False, None,
         m(lambda d: d["harness"]["memory"].update(retention={"days": 30}))),
        ("policy-scope-bad-type", "policy scope.type is a closed enum (D-10)",
         "harness/policies/0/scope/type", "is not one of", False, None,
         m(lambda d: d["harness"]["policies"][0]["scope"].update(type="current"))),
        ("policy-enforcement-bad-phase", "enforcement phase enum excludes pre-invocation (D-11)",
         "harness/policies/0/enforcement/phase", "is not one of", False, None,
         m(lambda d: d["harness"]["policies"][0]["enforcement"].update(
             phase="pre-invocation"))),
        ("observability-unknown-event", "observability event names are a closed enum (D-13)",
         "harness/observability/events", "is not one of", False, None,
         m(lambda d: d["harness"]["observability"]["events"].append(
             {"name": "match.started", "type": "trace", "required": True,
              "evidenceRef": "trace:arena/vault/match"}))),
        ("extensions-unprefixed-namespace", "extension namespaces must be x- prefixed",
         "extensions", "'arena'", False, None,
         m(lambda d: d.setdefault("extensions", {}).update(
             arena={"format": "vault"}))),
        ("duplicate-tool-id", "two tools share one id — schema accepts this (F-010 gap)",
         None, None, True, "duplicate-id",
         m(lambda d: d["harness"]["tools"].append(
             copy.deepcopy(d["harness"]["tools"][0])))),
        ("tool-sideeffect-singular-typo",
         "sideEffect (singular typo) silently accepted on a tool — schema accepts "
         "unknown tool keys (F-011 gap); the declared side effects vanish",
         None, None, True, "unknown-tool-key",
         m(lambda d: d["harness"]["tools"][0].update(
             sideEffect=d["harness"]["tools"][0].pop("sideEffects")))),
    ]


def main() -> int:
    schema = json.loads(SCHEMA.read_bytes())
    validator = Draft202012Validator(schema)
    base = yaml.safe_load(BASE.read_text())

    for old in OUT.glob("*.yaml"):
        if old.name not in KEEP and old.name != "manifest.yaml":
            old.unlink()

    manifest = {"charge-intent-unbounded.yaml": {
        "reason": "minimal charge intent with no envelope — schema-valid, "
                  "conformance Level 0 fail (F-001)",
        "expectSchemaValid": True,
        "lint": None,
        "finding": "F-001",
    }}
    failures = 0
    for fid, reason, epath, emsg, expect_valid, lint, mutate in mutations():
        doc = copy.deepcopy(base)
        mutate(doc)
        errs = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        name = f"{fid}.yaml"
        if expect_valid:
            if errs:
                print(f"GEN FAIL {fid}: expected schema-valid, got "
                      f"{errs[0].message[:100]}")
                failures += 1
                continue
        else:
            match = [e for e in errs
                     if (epath == "<root>" or epath in "/".join(map(str, e.absolute_path))
                         or epath in "/".join(map(str, e.path)))
                     and emsg in e.message]
            if not match:
                got = [f"{'/'.join(map(str, e.path)) or '<root>'} :: {e.message[:90]}"
                       for e in errs[:4]]
                print(f"GEN FAIL {fid}: expected [{epath}] ~ {emsg!r}; got {got}")
                failures += 1
                continue
        (OUT / name).write_text(yaml.safe_dump(doc, sort_keys=False,
                                               allow_unicode=True))
        manifest[name] = {"reason": reason, "expectSchemaValid": expect_valid,
                          "lint": lint}
        if not expect_valid:
            manifest[name]["expect"] = {"path": epath, "message": emsg}
        if expect_valid and fid == "duplicate-tool-id":
            manifest[name]["finding"] = "F-010"
        if expect_valid and fid == "tool-sideeffect-singular-typo":
            manifest[name]["finding"] = "F-011"

    if failures:
        print(f"{failures} generation failures — corpus NOT fully written")
        return 1
    (OUT / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=True,
                                                      allow_unicode=True, width=88))
    print(f"wrote {len(manifest)} manifest entries "
          f"({sum(1 for v in manifest.values() if not v['expectSchemaValid'])} "
          f"schema-invalid, {sum(1 for v in manifest.values() if v['expectSchemaValid'])} "
          f"documented-gap)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
