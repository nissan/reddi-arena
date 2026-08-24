# GE02 — GitHub relation sync: issue-link audit

Evidence for graph node **GE02** ("Sync native GitHub relations for the issue
graph"). `planning/graph.yaml` remains the source of truth; this records the
mirror created on GitHub. Regenerate the desired plan with
`python3 tools/sync_github_relations.py`.

Applied **2026-08-24**.

## Epic issues created (one per graph epic)

Each epic issue carries a `<!-- graph-epic: Exx -->` marker (so a re-run of the
planner can find it), a task-list of its member nodes as `#N` references, the
`dependsOn` edges as readable text, and the `epic` + `graph-epic` labels.

| epic | epic issue | member nodes (sub-issue refs) |
|---|---|---|
| E01 | [#77](https://github.com/nissan/reddi-arena/issues/77) | #1 A1, #2 A2, #3 A3 |
| E02 | [#78](https://github.com/nissan/reddi-arena/issues/78) | #4 A4, #5 A5, #6 A6 |
| E03 | [#79](https://github.com/nissan/reddi-arena/issues/79) | #7 A7, #8 A8 |
| E04 | [#80](https://github.com/nissan/reddi-arena/issues/80) | #9 B1, #10 B2, #11 B3 |
| E05 | [#81](https://github.com/nissan/reddi-arena/issues/81) | #12 B4, #13 B5 |
| E06 | [#82](https://github.com/nissan/reddi-arena/issues/82) | #14 B6, #15 B7 |
| E07 | [#83](https://github.com/nissan/reddi-arena/issues/83) | #16 C1, #17 C2 |
| E08 | [#84](https://github.com/nissan/reddi-arena/issues/84) | #18 C3, #19 C4 |
| E09 | [#85](https://github.com/nissan/reddi-arena/issues/85) | #20 C5, #21 C6, #22 C7 |
| E10 | [#86](https://github.com/nissan/reddi-arena/issues/86) | #23 C8, #24 C9 |
| E11 | [#87](https://github.com/nissan/reddi-arena/issues/87) | #25 D1, #26 D2 |
| E12 | [#88](https://github.com/nissan/reddi-arena/issues/88) | #27 D3, #28 D4 |
| E13 | [#89](https://github.com/nissan/reddi-arena/issues/89) | #29 E1I, #30 E2I |
| E14 | [#90](https://github.com/nissan/reddi-arena/issues/90) | #31 E3I, #32 E4I |
| E15 | [#91](https://github.com/nissan/reddi-arena/issues/91) | #33 F1, #34 F2 |
| E16 | [#92](https://github.com/nissan/reddi-arena/issues/92) | #35 F3, #36 F4 |

16 epics, 36 node sub-issue references, 52 `dependsOn` edges recorded as text.

## Relation mechanism (and the API boundary)

The GE02 objective scopes native relations to "**where the API supports them**".

- **Epic → node links:** the epic issue body uses a `#N` task-list, which
  GitHub renders as tracked / sub-issue links visible from both the epic and
  the member issue. The member issues additionally already carry `epic:Exx`
  labels (grouping is visible from the child side too).
- **The formal REST sub-issue API was NOT usable here:** `sub_issue_write`
  requires each child's internal database `id`, and the available read tools
  (`issue_read get`, `list_issues`, `search_issues`) expose only the issue
  `number`, not the internal `id` — a direct attempt with the number returned
  `404`. So the body-task-list mechanism (which produces the same visible
  relation) was used instead of the REST hierarchy call. If a token-based path
  that yields internal ids becomes available, `sync_github_relations.py` can be
  extended to promote the task-list links to formal sub-issues.
- **`dependsOn` (blocked-by):** kept as readable text in each epic body. Native
  issue-dependency links are not in the API surface this repo uses — exactly
  the "where the API supports them" carve-out — so they remain textual
  redundancy alongside the canonical `graph.yaml`.

## No volatile GitHub state written back

`planning/graph.yaml` is unchanged by the sync except for GE02's own
`status` flip (a planning-status change, not GitHub state). The planner reads
the graph and never writes to it (`tests/test_arena.py` GE02 checks assert the
file is byte-identical after `build_plan()`).
