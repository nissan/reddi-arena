#!/usr/bin/env python3
"""One-time migration: plan/backlog.yaml -> planning/graph.yaml (graph-v1).

Run once for the graph-engineering pilot (node GE01). After migration,
planning/graph.yaml is the canonical execution graph; plan/backlog.yaml is
retained as the superseded fuller design (its own header already says so) and
still backs the generated spdd/ prompt artifacts, which remain the binding
per-node context. Statuses and scheduling live in the graph from now on.

Rerunning regenerates the migrated portion deterministically and re-appends
the governance nodes; it will overwrite hand edits to planning/graph.yaml.
"""
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plan" / "backlog.yaml"
OUT = ROOT / "planning" / "graph.yaml"

# Mirrors tools/generate_prompts.py (docs/REVISED-RECOMMENDATION.md).
STRUCK = {"F1", "F2"}          # violate the 2026-07-26 automation pause
PARKED_PHASES = {"P2", "P3", "P4"}  # parked behind the 2026-08-31 launch

# Lane -> default file surfaces for collision checks. Coarse by design; a
# node executor narrows them in its claim if needed.
LANE_SURFACES = {
    "SL-A": ["adl/", "fixtures/", "vendor/", "tools/", "docs/", "tests/"],
    "SL-B": ["core/", "tests/"],
    "SL-C": ["core/", "web/", "tests/"],
    "SL-D": ["web/", "tests/"],
    "SL-E": ["core/", "tests/"],
    "SL-F": ["docs/", "tools/", "README.md", "tests/"],
}

# Decision gates added by the pilot: parked lanes reopen only through an
# explicit human decision node (graph topology, not a buried question).
DECISION_GATES = {
    "DEC-C-UNPARK": ["C1"],          # rest of SL-C chains off C1/C3
    "DEC-D-UNPARK": ["D1", "D3"],
    "DEC-E-UNPARK": ["E3I"],         # E4I chains off E3I
}


def node_type(issue_id: str) -> str:
    if issue_id.startswith("DEC-"):
        return "decision"
    if issue_id == "A6":
        return "verification"
    return "implementation"


def main() -> None:
    plan = yaml.safe_load(PLAN.read_text())
    done = set()
    issues = []
    for epic in plan["epics"]:
        for issue in epic["issues"]:
            issue["_epic"] = epic["id"]
            issue["_lane"] = epic["swimlane"]
            issue["_phase"] = epic["phase"]
            issues.append(issue)
            if issue.get("status") == "done":
                done.add(issue["id"])

    gate_of = {iid: gate for gate, iids in DECISION_GATES.items() for iid in iids}

    nodes = []
    for issue in issues:
        iid = issue["id"]
        deps = list(issue.get("dependsOn", []))
        if iid in gate_of:
            deps.append(gate_of[iid])
        if iid in STRUCK:
            status = "cancelled"
        elif issue.get("status") == "done":
            status = "done"
        elif issue["_phase"] in PARKED_PHASES:
            status = "parked"
        elif all(d in done for d in deps):
            status = "ready"
        else:
            status = "blocked"
        tests = []
        for tid in issue.get("tests", []):
            if status == "done":
                cmd = "python3 tools/validate_adl.py && python3 tests/test_arena.py"
            else:
                cmd = (f"python3 tests/test_arena.py  "
                       f"# implement {tid} per docs/TEST-PLAN.md; keep suite green")
            tests.append({"id": tid, "command": cmd})
        node = {
            "id": iid,
            "type": node_type(iid),
            "title": issue["title"],
            "status": status,
            "objective": " ".join(str(issue.get("rationale", "")).split()),
            "epic": issue["_epic"],
            "lane": issue["_lane"],
            "phase": issue["_phase"],
            "parent": None,
            "dependsOn": deps,
            "acceptance": issue.get("acceptance", []),
            "tests": tests,
            "evidence": {"required": [
                "test-output",
                "pr-review",
                f"spdd artifact (spdd/prompt/*-{iid.lower()}-*.md) Sync Log updated",
            ]},
            "boundary": " ".join(str(issue.get("boundary", "")).split()),
            "surfaces": {"allow": LANE_SURFACES[issue["_lane"]], "deny": ["artifacts/"]},
            "humanGate": False,
        }
        if status == "cancelled":
            node["note"] = ("STRUCK per docs/REVISED-RECOMMENDATION.md - violates the "
                            "2026-07-26 automation pause. Never schedule. Any successor "
                            "on-chain lane must be a NEW decision node with explicit "
                            "operator approval.")
        if status == "done":
            node["evidence"]["recorded"] = [" ".join(str(issue.get("evidence", "")).split())]
        nodes.append(node)

    for gate, gated in DECISION_GATES.items():
        lane = gated[0][0]
        nodes.append({
            "id": gate,
            "type": "decision",
            "title": f"Decide whether to un-park the SL-{lane} lane after the 2026-08-31 launch",
            "status": "parked",
            "objective": ("Record the consequential go/no-go for this parked lane as an ADR "
                          "with rationale, scope, and any narrowed mandate. For SL-C the "
                          "decision is tied to the ADL v0.3 price-discovery intake "
                          "(reddiagent-lab#440 / #389 seed 2)." if lane == "C" else
                          "Record the consequential go/no-go for this parked lane as an ADR "
                          "with rationale, scope, and any narrowed mandate."),
            "parent": None,
            "dependsOn": [],
            "informs": gated,
            "acceptance": [
                "ADR records options, tradeoffs, decision, and consequences.",
                "Human approval is recorded on the GitHub issue.",
            ],
            "tests": [{"id": f"{gate}-T1", "command": f"test -f docs/adr/{gate}.md"}],
            "evidence": {"required": [f"docs/adr/{gate}.md", "human-approval"]},
            "boundary": ("Not before the 2026-08-31 launch. Deciding does not implement; "
                         "gated nodes stay parked until this node is done."),
            "surfaces": {"allow": ["docs/adr/", "planning/"], "deny": []},
            "humanGate": True,
        })

    # The governance nodes below are a verbatim snapshot of the graph-engineering
    # pilot as it was executed. GE01's "CLAUDE.md" references are that historical
    # record: today CLAUDE.md is a one-line import and AGENTS.md is the direct
    # authority for the node workflow and hard boundaries. Completed-node text is
    # deliberately NOT rewritten when the authority file moves, so this snapshot
    # stays trustworthy as evidence; planning/graph.yaml also carries recorded
    # evidence and done statuses this generator does not emit, which is why
    # rerunning it is an archival re-derivation, not a maintenance step. Both
    # halves are enforced by the "planning-graph re-derivation" checks in
    # tests/test_arena.py.
    nodes.extend([
        {
            "id": "GE01",
            "type": "implementation",
            "title": "Adopt graph engineering: canonical execution graph, lint, role prompts",
            "status": "ready",
            "objective": ("Land planning/graph.yaml as the canonical execution graph "
                          "(migrated from plan/backlog.yaml), tools/graph_lint.py as a "
                          "test gate, and the four role prompts; wire the workflow into "
                          "CLAUDE.md."),
            "parent": None,
            "dependsOn": [],
            "produces": ["artifact:planning/graph.yaml"],
            "acceptance": [
                "planning/graph.yaml lints clean and encodes every backlog issue, the "
                "decision gates for parked lanes, and F1/F2 as cancelled.",
                "tools/graph_lint.py validates statuses, required fields, and DAG acyclicity.",
                "planning/prompts/ carries bootstrap, node-executor, supervisor, and "
                "retrospective prompts adapted to this repo.",
                "CLAUDE.md documents the node workflow (claim, branch node/<ID>-<slug>, "
                "PR evidence boundary, rebase gate).",
                "Full arena suite stays green.",
            ],
            "tests": [
                {"id": "GE01-T1", "command": "python3 tools/graph_lint.py"},
                {"id": "GE01-T2", "command": "python3 tests/test_arena.py"},
            ],
            "evidence": {"required": ["test-output", "pr-review"]},
            "boundary": ("Process only. No crons, loops, or packet/gate/handoff/signoff "
                         "scripts (2026-07-26 automation pause). Does not change any game "
                         "or spec behavior, and does not un-park any lane."),
            "surfaces": {"allow": ["planning/", "tools/", "docs/adr/", "CLAUDE.md"],
                         "deny": ["core/", "web/", "adl/"]},
            "humanGate": False,
        },
        {
            "id": "GE02",
            "type": "implementation",
            "title": "Sync native GitHub relations for the issue graph",
            "status": "blocked",
            "dependsOn": ["GE01"],
            "objective": ("Mirror graph edges onto GitHub: epic parent issues with "
                          "sub-issue links, and blocked-by relations where the API "
                          "supports them; text depends-on lines remain as readable "
                          "redundancy."),
            "parent": None,
            "acceptance": [
                "Each epic is a GitHub issue with its nodes attached as sub-issues.",
                "Dependency relations visible on GitHub match graph.yaml dependsOn.",
                "No volatile GitHub state is written back into planning/graph.yaml.",
            ],
            "tests": [{"id": "GE02-T1",
                       "command": "python3 tools/graph_lint.py  # graph unchanged by sync"}],
            "evidence": {"required": ["pr-review", "issue-link-audit"]},
            "boundary": "Metadata sync only; creates no workflow automation.",
            "surfaces": {"allow": ["planning/", "tools/"], "deny": []},
            "humanGate": False,
        },
        {
            "id": "GE03",
            "type": "verification",
            "title": "Pilot meta-retrospective: promote, adjust, or abandon the graph template",
            "status": "blocked",
            "dependsOn": ["GE01"],
            "objective": ("After 3-5 executable nodes complete full claim->PR->retrospective "
                          "cycles, mine the audit trail with planning/prompts/"
                          "30-retrospective.md and recommend PROJECT-SPECIFIC vs "
                          "TEMPLATE-CANDIDATE changes. Promotion to reddiagent-lab or "
                          "reddi-agent-protocol requires this node."),
            "parent": None,
            "acceptance": [
                "At least 3 nodes have completed the full cycle with evidence.",
                "Retrospective classifies recommendations and records the promote/adjust/"
                "abandon decision with human approval.",
            ],
            "tests": [{"id": "GE03-T1", "command": "test -f docs/adr/GE03-pilot-verdict.md"}],
            "evidence": {"required": ["docs/adr/GE03-pilot-verdict.md", "human-approval"]},
            "boundary": ("Recommends only; template promotion to other repos is a separate "
                         "decision in those repos."),
            "surfaces": {"allow": ["docs/adr/", "planning/"], "deny": []},
            "humanGate": True,
        },
    ])

    header = (
        "# Reddi Arena — canonical execution graph (graph-v1)\n"
        "# Migrated from plan/backlog.yaml by tools/plan_to_graph.py (node GE01).\n"
        "# This file is now the source of truth for scheduling and status.\n"
        "# plan/backlog.yaml is retained as the superseded fuller design and still\n"
        "# backs the generated spdd/ prompt artifacts (binding per-node context).\n"
        "# Lint: python3 tools/graph_lint.py   Rules: planning/prompts/00-bootstrap.md\n"
        "# Do not record volatile GitHub state (PR numbers, worktrees, CI) here.\n"
    )
    doc = {
        "version": "graph-v1",
        "project": "reddi-arena",
        "defaultBranch": "main",
        "policies": {
            "oneIssuePerExecutableNode": True,
            "oneWorktreePerClaimedNode": True,
            "onePrimaryPRPerNode": True,
            "requireLinearHistory": True,
            "preferredMerge": "rebase",
            "requireRetrospective": True,
            "doneRequiresEvidence": True,
            "maxParallelNodes": 2,
        },
        "nodeTypes": ["discovery", "decision", "design", "implementation",
                      "verification", "documentation", "release"],
        "statuses": ["ready", "blocked", "parked", "cancelled", "done"],
        "nodes": nodes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(header + yaml.safe_dump(doc, sort_keys=False, width=88,
                                           allow_unicode=True))
    print(f"wrote {OUT.relative_to(ROOT)} with {len(nodes)} nodes")


if __name__ == "__main__":
    sys.exit(main())
