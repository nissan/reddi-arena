#!/usr/bin/env python3
"""
Reddi Arena — render markdown projections from the canonical plan.

Mirrors the ADL philosophy: one canonical source, many loss-aware projections.
Never hand-edit the generated files; edit plan/backlog.yaml and re-render.
"""

from __future__ import annotations

import yaml

PLAN = "plan/backlog.yaml"
BANNER = "<!-- GENERATED from plan/backlog.yaml by tools/render_plan.py — do not hand-edit. -->\n"


def load() -> dict:
    with open(PLAN) as fh:
        return yaml.safe_load(fh)


def index(plan: dict):
    phases = {p["id"]: p for p in plan["phases"]}
    lanes = {s["id"]: s for s in plan["swimlanes"]}
    issues, issue_epic = {}, {}
    for epic in plan["epics"]:
        for issue in epic["issues"]:
            issues[issue["id"]] = issue
            issue_epic[issue["id"]] = epic
    tests = {t["id"]: t for t in plan["tests"]}
    return phases, lanes, issues, issue_epic, tests


def render_roadmap(plan: dict) -> str:
    phases, lanes, issues, issue_epic, _ = index(plan)
    out = [BANNER, f"# Reddi Arena — Roadmap ({plan['planVersion']}, {plan['dated']})\n"]
    out.append(f"> {plan['relationToLab'].strip()}\n")

    out.append("## Phases\n")
    out.append("| Phase | Name | Intent | Exit gate | Schedulable |")
    out.append("|---|---|---|---|---|")
    for p in plan["phases"]:
        sched = "Yes" if p.get("schedulable", True) else "**BLOCKED**"
        out.append(f"| {p['id']} | {p['name']} | {p['intent'].strip()} | {p['exitGate'].strip()} | {sched} |")
    out.append("")

    out.append("## Swimlanes\n")
    out.append("| Lane | Name | Charter |")
    out.append("|---|---|---|")
    for s in plan["swimlanes"]:
        out.append(f"| {s['id']} | {s['name']} | {s['charter'].strip()} |")
    out.append("")

    out.append("## Epics by phase and swimlane\n")
    for pid, phase in phases.items():
        epics = [e for e in plan["epics"] if e["phase"] == pid]
        if not epics:
            out.append(f"### {pid} — {phase['name']}\n\n_No scheduled epics._\n")
            continue
        out.append(f"### {pid} — {phase['name']}\n")
        out.append("| Epic | Lane | Name | Outcome | Issues |")
        out.append("|---|---|---|---|---|")
        for e in epics:
            ids = ", ".join(i["id"] for i in e["issues"])
            out.append(f"| {e['id']} | {e['swimlane']} | {e['name']} | {e['outcome'].strip()} | {ids} |")
        out.append("")

    out.append("## Dependency graph\n")
    out.append("```mermaid")
    out.append("graph LR")
    for pid, phase in phases.items():
        member_issues = [i["id"] for i in issues.values()
                         if issue_epic[i["id"]]["phase"] == pid]
        if not member_issues:
            continue
        out.append(f"  subgraph {pid}[\"{pid} · {phase['name']}\"]")
        for iid in member_issues:
            label = issues[iid]["title"][:44]
            out.append(f"    {iid}[\"{iid}<br/>{label}\"]")
        out.append("  end")
    for iid, issue in issues.items():
        for dep in issue.get("dependsOn") or []:
            out.append(f"  {dep} --> {iid}")
    out.append("```\n")

    roots = [i for i, d in issues.items() if not (d.get("dependsOn") or [])]
    out.append(f"**Start set (no dependencies):** {', '.join(sorted(roots))}\n")
    return "\n".join(out)


def render_backlog(plan: dict) -> str:
    phases, lanes, issues, _, tests = index(plan)
    out = [BANNER, f"# Reddi Arena — Backlog ({plan['planVersion']})\n"]
    out.append("Every issue carries: rationale, dependencies, an explicit boundary "
               "(what it does **not** authorize), tasks, acceptance criteria, and the "
               "automated tests that constitute doneness.\n")

    for epic in plan["epics"]:
        lane = lanes[epic["swimlane"]]["name"]
        out.append(f"---\n\n## {epic['id']} — {epic['name']}\n")
        out.append(f"**Lane:** {epic['swimlane']} {lane}  |  **Phase:** {epic['phase']} "
                   f"{phases[epic['phase']]['name']}\n")
        out.append(f"**Outcome:** {epic['outcome'].strip()}\n")
        for issue in epic["issues"]:
            deps = ", ".join(issue.get("dependsOn") or []) or "none"
            out.append(f"### {issue['id']} — {issue['title']}\n")
            out.append(f"*Why:* {issue['rationale'].strip()}\n")
            out.append(f"*Depends on:* {deps}\n")
            out.append(f"*Boundary:* {issue['boundary'].strip()}\n")
            out.append("**Tasks**\n")
            for task in issue.get("tasks") or []:
                out.append(f"- [ ] {task}")
            out.append("\n**Acceptance criteria**\n")
            for crit in issue.get("acceptance") or []:
                out.append(f"- [ ] {crit}")
            out.append("\n**Doneness tests**\n")
            for tid in issue.get("tests") or []:
                t = tests[tid]
                out.append(f"- `{tid}` ({t['type']}) — {t['asserts']}")
            out.append("")
    return "\n".join(out)


def render_tests(plan: dict) -> str:
    _, _, issues, issue_epic, _ = index(plan)
    out = [BANNER, f"# Reddi Arena — Automated Doneness Tests ({plan['planVersion']})\n"]
    out.append("An issue is done when its tests pass in CI. Nothing is done because a "
               "planning ticket closed — that failure mode is exactly what the "
               "2026-08-01 operational correction was about.\n")

    by_type: dict[str, list[dict]] = {}
    for t in plan["tests"]:
        by_type.setdefault(t["type"], []).append(t)

    out.append("## Coverage by test type\n")
    out.append("| Type | Count | Purpose |")
    out.append("|---|---|---|")
    purpose = {
        "contract": "Asserts a declared contract holds exactly as specified.",
        "determinism": "Asserts identical inputs always yield identical outputs.",
        "property": "Asserts an invariant across generated inputs (hypothesis).",
        "unit": "Asserts a single computation against golden values.",
        "integration": "Asserts components compose correctly across a boundary.",
        "adversarial": "Attempts to break a control; passes only if the control holds.",
        "e2e": "Asserts whole-system behaviour over realistic play.",
    }
    for ttype in sorted(by_type):
        out.append(f"| {ttype} | {len(by_type[ttype])} | {purpose.get(ttype, '')} |")
    out.append("")

    out.append("## Test register\n")
    out.append("| Test | Type | Automation | Asserts | Proves done |")
    out.append("|---|---|---|---|---|")
    for t in plan["tests"]:
        targets = ", ".join(t["provesDoneFor"])
        out.append(f"| {t['id']} | {t['type']} | {t['automation']} | {t['asserts']} | {targets} |")
    out.append("")

    out.append("## Phase exit gates\n")
    out.append("| Phase | Exit gate | Tests that must be green |")
    out.append("|---|---|---|")
    for phase in plan["phases"]:
        if not phase.get("schedulable", True):
            out.append(f"| {phase['id']} | {phase['exitGate'].strip()} | n/a — not scheduled |")
            continue
        phase_tests = sorted({
            tid
            for iid, issue in issues.items()
            if issue_epic[iid]["phase"] == phase["id"]
            for tid in issue.get("tests") or []
        })
        out.append(f"| {phase['id']} | {phase['exitGate'].strip()} | {', '.join(phase_tests)} |")
    out.append("")
    return "\n".join(out)


def main() -> int:
    plan = load()
    for path, body in [
        ("docs/ROADMAP.md", render_roadmap(plan)),
        ("docs/BACKLOG.md", render_backlog(plan)),
        ("docs/TEST-PLAN.md", render_tests(plan)),
    ]:
        with open(path, "w") as fh:
            fh.write(body)
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
