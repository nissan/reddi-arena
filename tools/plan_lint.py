#!/usr/bin/env python3
"""
Reddi Arena — plan linter.

Treats the programme plan the way ADL treats an agent: as a machine-validatable
contract rather than prose. An independent analyst should be able to run this
and get a deterministic verdict on the plan's structural integrity before
spending any judgement on its content.

Invariants (see plan/backlog.yaml header):
  L1  referential integrity across epics, issues, swimlanes and phases
  L2  the dependency graph is a DAG
  L3  no issue depends on an issue in a later phase
  L4  every issue has >= 1 test and >= 1 acceptance criterion
  L5  every test maps to >= 1 existing issue
  L6  every issue declares an explicit boundary
  L7  no issue sits in a non-schedulable phase
"""

from __future__ import annotations

import sys
from collections import defaultdict

import yaml

PLAN = "plan/backlog.yaml"


def load(path: str = PLAN) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def lint(plan: dict) -> tuple[list[str], dict]:
    failures: list[str] = []

    phases = {p["id"]: p for p in plan["phases"]}
    phase_order = {pid: i for i, pid in enumerate(phases)}
    swimlanes = {s["id"] for s in plan["swimlanes"]}

    issues: dict[str, dict] = {}
    issue_phase: dict[str, str] = {}
    issue_epic: dict[str, str] = {}

    for epic in plan["epics"]:
        if epic["swimlane"] not in swimlanes:
            failures.append(f"L1 {epic['id']}: unknown swimlane {epic['swimlane']}")
        if epic["phase"] not in phases:
            failures.append(f"L1 {epic['id']}: unknown phase {epic['phase']}")
        elif not phases[epic["phase"]].get("schedulable", True):
            failures.append(f"L7 {epic['id']}: sits in non-schedulable phase {epic['phase']}")
        for issue in epic["issues"]:
            iid = issue["id"]
            if iid in issues:
                failures.append(f"L1 duplicate issue id {iid}")
            issues[iid] = issue
            issue_phase[iid] = epic["phase"]
            issue_epic[iid] = epic["id"]

    # L2 / L3 — dependency graph
    graph: dict[str, list[str]] = {i: list(d.get("dependsOn") or []) for i, d in issues.items()}
    for iid, deps in graph.items():
        for dep in deps:
            if dep not in issues:
                failures.append(f"L1 {iid}: depends on unknown issue {dep}")
                continue
            if phase_order[issue_phase[dep]] > phase_order[issue_phase[iid]]:
                failures.append(
                    f"L3 {iid} ({issue_phase[iid]}) depends on {dep} in later phase "
                    f"{issue_phase[dep]}"
                )

    # cycle detection
    WHITE, GREY, BLACK = 0, 1, 2
    colour = defaultdict(int)
    cycles: list[list[str]] = []

    def visit(node: str, stack: list[str]) -> None:
        colour[node] = GREY
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt not in issues:
                continue
            if colour[nxt] == GREY:
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif colour[nxt] == WHITE:
                visit(nxt, stack)
        stack.pop()
        colour[node] = BLACK

    for iid in issues:
        if colour[iid] == WHITE:
            visit(iid, [])
    for cycle in cycles:
        failures.append("L2 dependency cycle: " + " -> ".join(cycle))

    # L4 / L6 — per-issue completeness
    for iid, issue in issues.items():
        if not issue.get("tests"):
            failures.append(f"L4 {iid}: no automated test declared")
        if not issue.get("acceptance"):
            failures.append(f"L4 {iid}: no acceptance criteria declared")
        if not (issue.get("boundary") or "").strip():
            failures.append(f"L6 {iid}: no boundary statement (what it does NOT authorize)")

    # L5 — test coverage integrity
    declared_tests = {t["id"] for t in plan["tests"]}
    for iid, issue in issues.items():
        for tid in issue.get("tests") or []:
            if tid not in declared_tests:
                failures.append(f"L5 {iid}: references undefined test {tid}")
    for test in plan["tests"]:
        targets = test.get("provesDoneFor") or []
        if not targets:
            failures.append(f"L5 {test['id']}: proves nothing done")
        for target in targets:
            if target not in issues:
                failures.append(f"L5 {test['id']}: targets unknown issue {target}")

    # topological order (only meaningful if acyclic)
    order: list[str] = []
    indeg = {i: 0 for i in issues}
    for iid, deps in graph.items():
        for dep in deps:
            if dep in indeg:
                indeg[iid] += 1
    ready = sorted([i for i, d in indeg.items() if d == 0])
    while ready:
        node = ready.pop(0)
        order.append(node)
        for other, deps in graph.items():
            if node in deps:
                indeg[other] -= 1
                if indeg[other] == 0:
                    ready.append(other)
        ready.sort()

    stats = {
        "phases": len(phases),
        "swimlanes": len(swimlanes),
        "epics": len(plan["epics"]),
        "issues": len(issues),
        "tasks": sum(len(i.get("tasks") or []) for i in issues.values()),
        "acceptanceCriteria": sum(len(i.get("acceptance") or []) for i in issues.values()),
        "tests": len(plan["tests"]),
        "criticalPathLength": len(order),
        "topologicalOrder": order,
        "unblockedNow": [i for i, d in graph.items() if not d],
    }
    return failures, stats


def main() -> int:
    plan = load(sys.argv[1] if len(sys.argv) > 1 else PLAN)
    failures, stats = lint(plan)

    print(f"PLAN LINT — {plan['programme']} {plan['planVersion']}")
    print(f"  phases {stats['phases']}  swimlanes {stats['swimlanes']}  "
          f"epics {stats['epics']}  issues {stats['issues']}")
    print(f"  tasks {stats['tasks']}  acceptance criteria {stats['acceptanceCriteria']}  "
          f"tests {stats['tests']}")
    print(f"  issues with no dependencies (startable now): {len(stats['unblockedNow'])}")
    print(f"  topologically ordered issues: {stats['criticalPathLength']}/{stats['issues']}")

    if failures:
        print(f"\n  FAIL — {len(failures)} invariant violation(s):")
        for failure in failures:
            print(f"    - {failure}")
        return 1

    print("\n  PASS — all plan invariants hold (L1-L7).")
    print(f"\n  Suggested start set: {', '.join(sorted(stats['unblockedNow']))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
