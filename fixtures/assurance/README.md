# RAP Assurance preview fixtures

These fixtures back the local Solana Devnet Preview in `/play`.

- `audd-transfer-checked.json` is a deterministic parsed `TransferChecked` fixture shaped after the canonical `@reddi/x402-solana` read-only observer tests.
- It is not a live RPC observation, not an official AUDD mint observation, not grant evidence, not custody, and not settlement finality.
- Negative preview scenarios mutate this fixture in memory to demonstrate wrong mint, wrong payee, tamper, and replay refusal outcomes.

Contribution path: add a minimal fixture here, document its boundary, then add an executable check in `tests/test_arena.py` that exercises the public preview API or core assurance adapter.
