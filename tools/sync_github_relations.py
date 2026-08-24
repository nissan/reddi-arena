#!/usr/bin/env python3
"""Plan the native-GitHub mirror of the execution graph (node GE02).

The execution graph (`planning/graph.yaml`) is the source of truth for
scheduling; GitHub carries a *mirror* so the relations are visible where people
read issues. This tool is the deterministic PLANNER: it reads the graph and the
node->issue map (`spdd/INDEX.md`) and emits the desired relation set — one epic
issue per graph epic, each executable node attached as a sub-issue, and the
`dependsOn` edges as text (readable redundancy; native issue-dependency links
are not in the API surface this repo uses, so they stay textual per the GE02
objective).

It WRITES NOTHING — not to GitHub, and not back into `planning/graph.yaml`
(acceptance: "no volatile GitHub state is written back"). The caller applies the
plan through the GitHub API/MCP and can re-run the planner idempotently: pass a
JSON map of already-created epic issues (`--existing`) and the plan marks each
epic create-or-skip. Sub-issue attachment is idempotent at apply time (attaching
an already-attached child is a no-op).

Usage:
    python3 tools/sync_github_relations.py                 # human-readable plan
    python3 tools/sync_github_relations.py --json          # machine plan
    python3 tools/sync_github_relations.py --json --existing '{"E01": 101}'
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "planning" / "graph.yaml"
INDEX = ROOT / "spdd" / "INDEX.md"
EPIC_MARKER = "graph-epic"  # HTML-comment marker so a re-run can find the epic issue


def _load_graph() -> dict:
    import yaml
    return yaml.safe_load(GRAPH.read_text())


def _node_issue_map() -> dict:
    """node id -> GitHub issue number, parsed from spdd/INDEX.md."""
    out: dict[str, int] = {}
    row = re.compile(r"\|\s*\d+\s*\|\s*([A-Za-z0-9]+)\s*\|\s*\[#(\d+)\]")
    for line in INDEX.read_text().splitlines():
        m = row.match(line)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def build_plan(existing: dict[str, int] | None = None) -> dict:
    """Desired GitHub relation set. Pure function of the graph + index files;
    `existing` (epic id -> issue number already created) only annotates each epic
    with create-or-skip and is never persisted."""
    existing = existing or {}
    g = _load_graph()
    nodes = {n["id"]: n for n in g["nodes"]}
    issue_of = _node_issue_map()

    # Group members by epic, preserving graph order.
    epics: dict[str, list[str]] = {}
    for n in g["nodes"]:
        e = n.get("epic")
        if e:
            epics.setdefault(e, []).append(n["id"])

    plan_epics = []
    for epic in sorted(epics):
        members = epics[epic]
        lanes = sorted({nodes[m].get("lane") for m in members if nodes[m].get("lane")})
        phases = sorted({nodes[m].get("phase") for m in members if nodes[m].get("phase")})
        # Sub-issues: every member that has a GitHub issue.
        children = [{"node": m, "issue": issue_of[m], "title": nodes[m].get("title", "")}
                    for m in members if m in issue_of]
        # Edges internal + external to the epic, as text redundancy.
        edges = []
        for m in members:
            for dep in nodes[m].get("dependsOn") or []:
                edges.append({"from": m, "to": dep,
                              "toIssue": issue_of.get(dep)})
        title = (f"Epic {epic}: {', '.join(members)}"
                 + (f"  [{'/'.join(lanes)}" if lanes else "")
                 + (f" {'/'.join(phases)}]" if phases else ("]" if lanes else "")))
        plan_epics.append({
            "epic": epic,
            "title": title,
            "marker": f"<!-- {EPIC_MARKER}: {epic} -->",
            "members": members,
            "subIssues": children,
            "dependsOn": edges,
            "existingIssue": existing.get(epic),
            "action": "skip (exists)" if epic in existing else "create",
        })
    return {
        "project": g.get("project"),
        "epicCount": len(plan_epics),
        "subIssueCount": sum(len(e["subIssues"]) for e in plan_epics),
        "edgeCount": sum(len(e["dependsOn"]) for e in plan_epics),
        "epics": plan_epics,
    }


def epic_body(epic_plan: dict) -> str:
    """The Markdown body for an epic issue — the marker, the member sub-issues,
    and the dependency edges as readable text."""
    lines = [epic_plan["marker"], "",
             f"Mirror of graph epic **{epic_plan['epic']}** "
             f"(`planning/graph.yaml` is the source of truth).", "",
             "## Nodes (sub-issues)"]
    for c in epic_plan["subIssues"]:
        lines.append(f"- [ ] #{c['issue']} — {c['node']}: {c['title']}")
    deps = epic_plan["dependsOn"]
    if deps:
        lines += ["", "## Depends-on (readable redundancy)"]
        for e in deps:
            tgt = f"#{e['toIssue']}" if e["toIssue"] else e["to"]
            lines.append(f"- {e['from']} depends on {e['to']} ({tgt})")
    lines += ["", "_Generated by [Claude Code](https://claude.ai/code) — GE02 relation sync_"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Plan the GitHub mirror of the graph (GE02).")
    ap.add_argument("--json", action="store_true", help="emit the machine plan")
    ap.add_argument("--existing", default="{}",
                    help='JSON map {epic: issueNumber} of epics already created')
    ap.add_argument("--bodies", action="store_true",
                    help="with --json, include the rendered epic body for each epic")
    a = ap.parse_args()
    try:
        existing = json.loads(a.existing)
    except json.JSONDecodeError as e:
        print(f"--existing is not valid JSON: {e}", file=sys.stderr)
        return 2
    plan = build_plan(existing)
    if a.bodies:
        for e in plan["epics"]:
            e["body"] = epic_body(e)
    if a.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0
    print(f"GE02 relation plan — {plan['epicCount']} epics, "
          f"{plan['subIssueCount']} sub-issues, {plan['edgeCount']} depends-on edges")
    for e in plan["epics"]:
        print(f"\n{e['action']:16} {e['title']}")
        for c in e["subIssues"]:
            print(f"    sub-issue #{c['issue']:<3} {c['node']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
