# Reddi Arena — Weight Class Specification v0.1

**Status:** frozen (v0.1, `arena-weights-v0.1`, frozen 2026-08-16 under issue
A4). Arena-local. Not an ADL semantic. Nothing here modifies or extends
canonical ADL v0.2; the formula is a *consumer* of a validated document.
Changes to the AU table, class bands, or coupling go through a v0.2 formula
spec with a new `weightsVersion` — never a mid-season edit. Historical
certificates stay interpretable through their recorded `weightsVersion`.

**Boundary:** a weight certificate is an eligibility input. It authorizes no
provider call, no credential, no network access, no MCP resolution, no wallet,
no payment, and no execution.

---

## Why weight exists

Combat robotics solved the problem the Arena has: without weight classes, the
biggest machine always wins and nobody learns anything. The Arena's equivalent
of mass is **declared capability**, which makes the formula a proof point rather
than a game mechanic bolted on top:

- Weight is computed **only** from a schema-valid ADL document.
- Any two implementations must produce the same number from the same document.
- A capability that is not declared does not count toward weight — and,
  because of the runtime binding in issue `E1I`, also cannot be used.

That last line is the whole argument. It is what makes ADL a contract rather
than documentation, and it is the single most valuable thing the Arena proves.

## Arena Units (AU)

| Component | AU |
|---|---|
| Chassis base | 20 |
| `contextWindow` | 6 per started 8,000 tokens |
| `maxOutputTokens` | 3 per started 512 tokens |
| `toolCalling` | 4 |
| `structuredOutput` | 3 |
| `jsonMode` | 2 |
| `streaming` | 1 |
| modality `text` | 0 |
| modality `embedding` | 6 |
| modality `image` / `audio` | 12 each |
| Each tool | 8 base + side-effect surcharge + 2 if `auditLevel: full` |
| Side-effect `none` / `read` / `write` / `external` / `payment` | 0 / 2 / 8 / 14 / 20 |
| Each function | 5 |
| Each skill | 4 |
| Data source by type: `file` / `url` / `api` / `database` / `vector-index` / `mcp` | 3 / 6 / 8 / 10 / 12 / 14 |
| Data source trust `approved` / `unknown` / `untrusted` | 0 / +4 / +6 |
| Memory `session` / `persistent` / `external` | 0 / 15 / 25 |
| Each eligible policy | **−2** (floor −20) |
| Each x402 payment intent | 25 |

### The policy credit is deliberate

Declaring explicit policies makes a bot *lighter*. Good hygiene is a competitive
advantage, not a tax. To stop credit-farming, a policy earns credit only if it
either carries `effect: deny` or is referenced by a declared capability via
`policyRefs`. Padding with no-op allow policies is the first exploit an analyst
should try — it is issue `A6`, test `T-013`.

### Coupled weight for hires

```
coupledAU = ceil(specialistSoloAU × 0.6) + 10
```

The 0.6 coupling factor says a hired specialist costs less than owning the
capability outright; the flat 10 is integration overhead. This is what makes the
draft a real decision instead of a free power-up.

### Hire depth (draft rule)

A fielded specialist cannot itself field sub-hires: the transitive hire depth
cap is **1** in v0.1. Deeper chains are refused at draft with the cap stated,
before any weighing occurs — an adversarial chain of any length is rejected in
constant time. This is a draft-eligibility rule, not part of the frozen AU
formula; raising the cap is a v0.2 formula-spec question because coupled
weight would then need a composition rule.

## Class bands

| Class | AU ceiling |
|---|---|
| Antweight | 100 |
| Beetleweight | 250 |
| Hobbyweight | 500 |
| Featherweight | 900 |
| Middleweight | 1,800 |
| Heavyweight | unbounded |

Two figures are recorded per match:

- **Solo AU** — the bot alone. Determines which class it may *enter*.
- **Fielded AU** — after hires. Must remain inside the entered class.

## Worked example

The two reference documents in `adl/`, computed by `tools/weigh_in.py`:

```
antweight-vault-defender          62 AU   Antweight
mercenary-source-auditor          91 AU   Antweight
antweight + 1 hire               127 AU   Beetleweight   ← CLASS BUMP
```

The defender is a legal Antweight on its own. Hiring the auditor adds
`ceil(91 × 0.6) + 10 = 65 AU` and pushes it to 127 — out of the class it
entered. At draft, that hire is **refused**, with the AU delta shown to the
player (issue `C4`, test `T-011`).

This is the strategic core of the game, and it is computed entirely from two
declaration documents with no execution involved.

## Capability hash

Each certificate carries `sha256` over the canonicalised certificate body. The
runtime binds to that exact hash. A bot cannot be weighed in one configuration
and fielded in another (`E1I`, `T-079`).

## Known limitations

1. **The formula is a scoring function, so it will be optimised against.**
   `A6` is the standing exploit review. Version the formula; never change it
   mid-season.
2. **Declared context is not consumed context.** A bot can under-declare
   `contextWindow` to make weight. Static weighing cannot catch this; runtime
   measurement in `E2I` can, and routes to human review rather than auto-ban.
3. **Coefficients are guesses.** They are calibrated to make the reference
   example instructive, not to reflect real compute cost. Expect `v0.2` after
   the first season's balance data (`B7`).
4. **Canonicalisation is Arena-local.** If the lab adopts a canonical hashing
   scheme (e.g. via the capability-hash-linkage work), Arena must switch to it
   and treat this as a projection.
