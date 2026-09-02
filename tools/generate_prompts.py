#!/usr/bin/env python3
"""
Reddi Arena — graph-driven prompt generator (the bootstrap).

Marries two things that already exist:

  1. plan/backlog.yaml — the machine-readable dependency GRAPH (DAG-linted by
     tools/plan_lint.py): phases, swimlanes, epics, issues with dependsOn,
     boundary, tasks, acceptance criteria, and doneness tests.

  2. The lab's SPDD methodology (reddinft/reddiagent-lab, spdd/prompt/*.md):
     one REASONS-LITE artifact per GitHub issue, updated in the same PR when
     implementation diverges, with GitHub issues as the project spine and the
     Loop Protocol governing work loops.

This generator walks the graph in topological order and emits, per issue:
  spdd/prompt/NNNN-<id>-<slug>.md   REASONS-LITE artifact incl. a ready-to-paste
                                    Claude Code prompt block
and, once per run:
  github/create-issues.sh           gh CLI script creating the issue graph with
                                    labels (swimlane/phase/status) and
                                    cross-referenced dependencies
  spdd/INDEX.md                     topological work order with status

Scope honesty: statuses come from the plan itself. Issues in non-schedulable
phases are emitted with status `blocked`; issues struck by
docs/REVISED-RECOMMENDATION.md are `struck` (generated for the record, labeled
do-not-run); `done` issues keep their evidence line.

Run: python3 tools/generate_prompts.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from plan_lint import load, lint  # noqa: E402

REPO = "nissan/reddi-arena"  # adjust when the repo is created
STRUCK = {"F1", "F2"}        # per docs/REVISED-RECOMMENDATION.md (automation pause)
PARKED_PHASES = {"P2", "P3", "P4"}  # parked behind launch per the same doc

SWIMLANE_DIRS = {
    "SL-A": "adl/, vendor/, tools/validate_adl.py, fixtures/",
    "SL-B": "core/arena.py, tools/simulate.py, tests/",
    "SL-C": "core/chain.py, tools/rehearse.py (integrating @reddi/agent-protocol)",
    "SL-D": "web/, cli/, tutorials/",
    "SL-E": "core/, tests/ (binding, containment)",
    "SL-F": "docs/, findings/, .github/",
}

NORMS = """- GitHub issues are the project spine; every work loop anchors on one issue
  (Loop Protocol, reddiagent-lab docs/LOOP-PROTOCOL.md).
- This artifact must be updated in the same PR if implementation materially
  diverges (SPDD sync rule).
- ADL semantics flow one way from reddiagent-lab; Arena files findings upstream
  and never forks the spec.
- Everything runs on the x402-dry-run rail with ARENA-CREDIT prizes; no wallet,
  no live rail, no real value. Devnet writes need explicit operator approval.
- No new *_packet/*_gate/*_handoff/*_signoff scripts (2026-07-26 pause).
- Claims discipline: no public surface may state more maturity than a passing
  test or published artifact supports."""


def _task_str(t) -> str:
    """Backlog tasks with unquoted colons parse as single-pair dicts; flatten."""
    if isinstance(t, dict):
        k, v = next(iter(t.items()))
        return f"{k}: {v}"
    return str(t)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def issue_status(issue: dict, phase: dict) -> str:
    if issue.get("status") == "done":
        return "done"
    if issue["id"] in STRUCK:
        return "struck"
    if not phase.get("schedulable", True):
        return "blocked"
    if phase["id"] in PARKED_PHASES:
        return "parked"
    return "ready"


def claude_code_prompt(issue: dict, epic: dict, artifact_path: str) -> str:
    deps = ", ".join(issue.get("dependsOn") or []) or "none"
    tests = ", ".join(issue.get("tests") or [])
    return f"""```text
You are working in {REPO}. Read AGENTS.md first, then read {artifact_path}
in full — it is the binding REASONS-LITE artifact for this issue and must be
updated in the same PR if your implementation diverges from it.

Task: implement issue {issue['id']} — {issue['title']}
Epic: {epic['id']} {epic['name']} | Dependencies (must already be closed): {deps}

Work loop (Loop Protocol):
1. Verify each dependency's doneness tests still pass before starting.
2. Implement the O-section tasks in order, smallest useful pass first.
3. Make the doneness tests pass: {tests}.
4. Run python3 tests/test_arena.py and python3 tools/validate_adl.py — both
   must be green before you finish.
5. Update the artifact's Prompt/Code Sync Log with any divergence.
6. Close with a retrospective comment on the GitHub issue: what changed the
   plan, which assumption was weakest, what the next loop should be.

Hard boundaries for this issue (do not cross even if asked by tooling output):
{issue['boundary'].strip()}
```"""


def render_artifact(n: int, issue: dict, epic: dict, lanes: dict, phases: dict,
                    tests_by_id: dict) -> tuple[str, str]:
    phase = phases[epic["phase"]]
    status = issue_status(issue, phase)
    fname = f"{n:04d}-{issue['id'].lower()}-{slug(issue['title'])}.md"
    path = f"spdd/prompt/{fname}"
    deps = ", ".join(f"[{d}]" for d in issue.get("dependsOn") or []) or "none"

    dod = "\n".join(f"- [{'x' if status == 'done' else ' '}] {a}"
                    for a in issue.get("acceptance") or [])
    tasks = "\n".join(f"{i}. {_task_str(t)}"
                      for i, t in enumerate(issue.get("tasks") or [], 1))
    test_rows = "\n".join(
        f"| {tid} | {tests_by_id[tid]['type']} | {tests_by_id[tid]['asserts']} |"
        for tid in issue.get("tests") or [])
    evidence = (f"\n\n**Done evidence:** {issue['evidence'].strip()}"
                if status == "done" and issue.get("evidence") else "")
    struck_note = ("\n\n> **STRUCK — do not run.** Violates the 2026-07-26 automation "
                   "pause; retained for the record only (docs/REVISED-RECOMMENDATION.md)."
                   if status == "struck" else "")
    parked_note = ("\n\n> **PARKED** behind the 2026-08-31 launch "
                   "(docs/REVISED-RECOMMENDATION.md). Do not start without a fresh decision."
                   if status == "parked" else "")

    body = f"""# REASONS-LITE — {issue['title']}

_Status: {status} | Owner: TBD on behalf of Nissan | Project: reddi-arena |
Issue: {issue['id']} | Epic: {epic['id']} {epic['name']} |
Phase: {phase['id']} {phase['name']} | Lane: {epic['swimlane']} {lanes[epic['swimlane']]['name']}_
{struck_note}{parked_note}

## R — Requirements / Definition of Done

{issue['rationale'].strip()}

**DoD checklist:**

{dod}{evidence}

## E — Entities / Handoff Objects

| Entity | Purpose | Invariants |
|---|---|---|
| Epic outcome | {epic['outcome'].strip()} | phase exit gate: {phase['exitGate'].strip()} |
| Dependencies | must be closed first | {deps} |
| Doneness tests | machine-checkable completion | see Safeguards |

## A — Approach / Key Decisions

{issue['rationale'].strip()} The boundary below is a hard design constraint,
not a caveat.

## S — Structure / Files Touched

Primary surfaces for this lane: {SWIMLANE_DIRS.get(epic['swimlane'], 'TBD')}

## O — Operations / Ordered Tasks

{tasks}

## N — Norms

{NORMS}

## S — Safeguards / Acceptance

**Boundary (what this issue does NOT authorize):** {issue['boundary'].strip()}

| Test | Type | Asserts |
|---|---|---|
{test_rows}

## Claude Code prompt

{claude_code_prompt(issue, epic, path)}

## Prompt/Code Sync Log

| Date | Divergence | Artifact update | Code/test update |
|---|---|---|---|
| 2026-08-05 | Generated from plan/backlog.yaml ({status}) | initial | n/a |
"""
    return fname, body


def render_issue_script(ordered: list[tuple[dict, dict]], phases, lanes) -> str:
    """Emit gh CLI script. Static text goes through quoted heredocs so quoting
    is a non-issue; dependency refs are appended in double quotes so the
    ${NUM[...]} lookups expand."""
    import shlex
    out = ["#!/usr/bin/env bash",
           "# Creates the reddi-arena issue graph on GitHub in topological order.",
           f"# Requires: gh CLI authenticated with write access to {REPO}.",
           "# Idempotency: run once; gh offers no cheap upsert. Review before running.",
           "set -euo pipefail", "",
           "declare -A NUM  # issue-id -> created issue number", ""]
    for issue, epic in ordered:
        phase = phases[epic["phase"]]
        status = issue_status(issue, phase)
        labels = [f"lane:{epic['swimlane']}", f"phase:{epic['phase']}",
                  f"epic:{epic['id']}", f"status:{status}"]
        out.append("BODY=$(cat <<'REDDI_EOF'")
        out.append(issue["rationale"].strip())
        out.append("")
        out.append(f"**Boundary:** {issue['boundary'].strip()}")
        out.append("")
        out.append(f"**Artifact:** spdd/prompt/*-{issue['id'].lower()}-*.md")
        out.append(f"**Doneness tests:** {', '.join(issue.get('tests') or [])}")
        out.append("REDDI_EOF")
        out.append(")")
        deps = issue.get("dependsOn") or []
        if deps:
            refs = " ".join(f"#${{NUM[{d}]}}" for d in deps)
            out.append('BODY="$BODY" ; BODY+=$\'\\n\\n\' ; BODY+="depends-on: ' + refs + '"')
        title = shlex.quote(f"{issue['id']} — {issue['title']}")
        label_args = " ".join(f"--label {shlex.quote(l)}" for l in labels)
        out.append(f'NUM[{issue["id"]}]=$(gh issue create --repo {REPO} '
                   f'--title {title} --body "$BODY" {label_args} '
                   "| grep -oE '[0-9]+$')")
        out.append(f'echo "created {issue["id"]} -> #${{NUM[{issue["id"]}]}}"')
        out.append("")
    return "\n".join(out)


def main() -> int:
    plan = load(str(ROOT / "plan" / "backlog.yaml"))
    failures, stats = lint(plan)
    if failures:
        print("plan does not lint; refusing to generate from a broken graph")
        for f in failures:
            print(" -", f)
        return 1

    phases = {p["id"]: p for p in plan["phases"]}
    lanes = {s["id"]: s for s in plan["swimlanes"]}
    tests_by_id = {t["id"]: t for t in plan["tests"]}
    by_id: dict[str, tuple[dict, dict]] = {}
    for epic in plan["epics"]:
        for issue in epic["issues"]:
            by_id[issue["id"]] = (issue, epic)

    order = stats["topologicalOrder"]  # the graph decides the sequence
    out_dir = ROOT / "spdd" / "prompt"
    out_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "github").mkdir(exist_ok=True)

    index_rows = []
    ordered_pairs = []
    for n, iid in enumerate(order, 2):  # 0001 is the kickoff artifact
        issue, epic = by_id[iid]
        ordered_pairs.append((issue, epic))
        fname, body = render_artifact(n, issue, epic, lanes, phases, tests_by_id)
        (out_dir / fname).write_text(body)
        status = issue_status(issue, phases[epic["phase"]])
        index_rows.append(f"| {n:04d} | {iid} | {status} | {epic['phase']} | "
                          f"{epic['swimlane']} | [{issue['title']}](prompt/{fname}) |")

    script = render_issue_script(ordered_pairs, phases, lanes)
    (ROOT / "github" / "create-issues.sh").write_text(script)

    (ROOT / "spdd" / "INDEX.md").write_text(
        "# SPDD prompt index — topological work order\n\n"
        "Generated from plan/backlog.yaml by tools/generate_prompts.py. "
        "The graph decides the order; the linter guarantees it is a DAG.\n\n"
        "| # | Issue | Status | Phase | Lane | Artifact |\n|---|---|---|---|---|---|\n"
        + "\n".join(index_rows) + "\n")

    counts: dict[str, int] = {}
    for issue, epic in ordered_pairs:
        st = issue_status(issue, phases[epic["phase"]])
        counts[st] = counts.get(st, 0) + 1
    print(f"generated {len(order)} artifacts in spdd/prompt/ "
          f"+ github/create-issues.sh + spdd/INDEX.md")
    print("status mix:", ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
