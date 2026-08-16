#!/usr/bin/env python3
"""Execution-DAG linter for planning/graph.yaml (graph-engineering pilot, GE01).

Vendored from the graph-engineering-project-template and extended with the
Arena's invariants:

  G1  every node has title, status, objective, acceptance, tests, boundary
  G2  every dependency exists; no self-dependency; dependsOn is a DAG
  G3  status is one of the declared statuses
  G4  a schedulable node (ready/blocked) never depends on a cancelled node
  G5  a ready node has no unmet dependencies (all deps done)
  G6  a done node records evidence; humanGate decisions require human-approval
      in required evidence
  G7  F1 and F2 stay cancelled (automation pause; docs/REVISED-RECOMMENDATION.md)
"""
from pathlib import Path
import sys

import yaml

path = Path(sys.argv[1] if len(sys.argv) > 1 else
            Path(__file__).resolve().parent.parent / "planning" / "graph.yaml")
data = yaml.safe_load(path.read_text())
nodes = {n["id"]: n for n in data.get("nodes", [])}
statuses = set(data.get("statuses") or
               ["ready", "blocked", "parked", "cancelled", "done"])
errors = []

for nid, n in nodes.items():
    for required in ("title", "status", "objective", "acceptance", "tests", "boundary"):
        if not n.get(required):
            errors.append(f"{nid}: missing {required} [G1]")
    for dep in n.get("dependsOn", []) or []:
        if dep not in nodes:
            errors.append(f"{nid}: unknown dependency {dep} [G2]")
        elif dep == nid:
            errors.append(f"{nid}: self dependency [G2]")
        elif (nodes[dep].get("status") == "cancelled"
              and n.get("status") in ("ready", "blocked")):
            errors.append(f"{nid}: schedulable but depends on cancelled {dep} [G4]")
    if n.get("status") not in statuses:
        errors.append(f"{nid}: invalid status {n.get('status')!r} [G3]")
    if n.get("status") == "ready":
        unmet = [d for d in n.get("dependsOn", []) or []
                 if d in nodes and nodes[d].get("status") != "done"]
        if unmet:
            errors.append(f"{nid}: ready with unmet deps {unmet} [G5]")
    if n.get("status") == "done" and not (n.get("evidence") or {}).get("recorded"):
        errors.append(f"{nid}: done without recorded evidence [G6]")
    if n.get("humanGate") and "human-approval" not in ((n.get("evidence") or {})
                                                       .get("required") or []):
        errors.append(f"{nid}: humanGate without human-approval evidence [G6]")

for fid in ("F1", "F2"):
    if fid in nodes and nodes[fid].get("status") != "cancelled":
        errors.append(f"{fid}: must remain cancelled [G7]")

colour = {nid: 0 for nid in nodes}
stack = []


def visit(nid):
    colour[nid] = 1
    stack.append(nid)
    for dep in nodes[nid].get("dependsOn", []) or []:
        if dep not in nodes:
            continue
        if colour[dep] == 1:
            cycle = stack[stack.index(dep):] + [dep]
            errors.append("dependency cycle: " + " -> ".join(cycle) + " [G2]")
        elif colour[dep] == 0:
            visit(dep)
    stack.pop()
    colour[nid] = 2


for nid in nodes:
    if colour[nid] == 0:
        visit(nid)

if errors:
    print("GRAPH LINT FAIL")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)

ready = sorted(nid for nid, n in nodes.items() if n.get("status") == "ready")
print(f"GRAPH LINT PASS — {len(nodes)} nodes; READY frontier: {', '.join(ready)}")
