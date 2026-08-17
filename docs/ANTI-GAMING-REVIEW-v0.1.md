# Anti-Gaming Review — AU Weight Formula v0.1 (issue A6)

**Status:** review complete, 2026-08-17. **Advisory to formula v0.2 only** —
nothing here changes `arena-weights-v0.1` mid-season (A6 boundary). Every
vector below is locked in the suite (T-013, T-014) so a regression in any
"bounded" verdict is a failing build.

## Vectors tried

| # | Vector | Verdict | Mechanism |
|---|---|---|---|
| 1 | Pad with no-op `effect: deny` policies to shed AU | **Bounded** | Deny policies always earn credit (−2 each), but the credit floor clamps total hygiene credit at −20 AU. Fifty padded policies buy exactly what ten buy. |
| 2 | Pad with unreferenced `effect: allow` policies | **Neutralized** | Allow policies earn credit only when referenced by a declared capability via `policyRefs`. Unreferenced padding earns 0. |
| 3 | Farm credit by declaring capability + referencing policy | **Self-defeating** | The cheapest capability (a `sideEffects: none` tool, +8 AU) costs more than the −2 credit its policy earns. Net weight always increases. |
| 4 | Redeclare a tool as a `skill` to understate weight | **OPEN — v0.2 item** | A skill is flat 4 AU with no side-effect surcharge; the same capability as a tool is 8+ AU. Static weighing cannot inspect skill semantics. Containment is layered, not formulaic: the disguised capability is not in `harness.tools`, so the E1I runtime binding refuses its invocation, and reliance beyond the declared envelope routes to E2I detection. The weight *understatement* itself remains, and is the top candidate for v0.2 (e.g. skill AU keyed on a declared skill `type`). |
| 5 | Reuse an honest certificate for a mutated document | **Bounded** | The capability hash covers the canonicalised certificate; any smuggling mutation changes the hash, so a certificate weighed on the honest document cannot be presented for the padded one (static half of E1I binding). |
| 6 | Under-declare `contextWindow` / `maxOutputTokens` | **OPEN — runtime item** | Already recorded as Known Limitation 2 in the weight spec: static weighing cannot catch consumption above declaration; E2I runtime measurement routes discrepancies to human review. |

## Recommendations for formula v0.2 (advisory)

1. Key skill AU on a declared skill `type` (reference vs executable) or fold
   skills into the tool surcharge model — closes vector 4's understatement.
2. Consider a per-capability credit cap in addition to the global floor, so
   deny-credit cannot concentrate on a single risky capability.
3. Keep the referenced-only rule for allow policies exactly as is — vector 2's
   neutralization is the formula's best anti-gaming property and should be
   stated as a design invariant, not an implementation detail.

Upstream note: no new spec findings — all vectors are Arena-formula-local.
The review feeds `B7` balance data and the v0.2 formula spec, nothing else.
