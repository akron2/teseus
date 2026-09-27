# Teseus Harness

A local, single-owner harness for a personal agent with **memory, forgetting,
and initiative**. This first staging version is a small, runnable vertical
slice: local bootstrap, versioned SQLite schema, persona loading, a deterministic
mock dialogue, and an explicit memory-selection journal. It uses Python 3.11+
and the standard library; no network, provider account, or secret is needed.

## Quick start

From this checkout:

```sh
python3 -m venv .venv
. .venv/bin/activate
PYTHONPATH=src python -m harness bootstrap --data-dir ./local-state
PYTHONPATH=src python -m harness dialogue --data-dir ./local-state --text "Hello, local harness"
PYTHONPATH=src python -m harness memory cycle --data-dir ./local-state
```

The local-state directory is runtime data and must stay private; it is ignored
by Git. Bootstrap makes it owner-only where supported. Use a private directory
outside a shared checkout for real conversations. To opt into the included
public seed example, pass `--seed-teseus` to bootstrap. The example is an
optional, removable ancestor/profile sample, not a required default identity.
Remove an installed sample (including its seeded memory records) and restore
the neutral persona with `PYTHONPATH=src python -m harness seed remove --data-dir ./local-state`.

`dialogue --remember "..."` explicitly proposes one synthetic or owner-provided
fact for memory selection; without that flag, a turn is not saved as a memory.
`memory cycle` ranks active items deterministically, retains up to three, and
marks the rest forgotten while journaling every transition. `memory restore ID`
reverses a forgetting decision and records that reversal. The mock reply is
deterministic and may offer one optional next step; it never executes tools.

For a single self-contained smoke run:

```sh
PYTHONPATH=src python -m harness demo --data-dir ./local-state
```

## Boundaries and status

- One local owner only. Guests and shared-memory access are unsupported and
  disabled. A prompt is not an access-control boundary.
- Telegram, web, external model engines, attachments, mail, background
  consolidation, and task execution are later-stage interfaces, not enabled
  integrations in this slice.
- There is no shell/tool executor, host-write capability, privileged mode, or
  automatic external action. Initiative is a suggestion requiring a person.
- The seed-memory is a public, synthetic example expressing a ship metaphor,
  selective/forgettable memory, context versus recollection, reversibility,
  verifiable trust, and bounded initiative. It contains no private dialogue.
- This staging repository has a fresh, local-only history. Do not publish until
  an owner has reviewed copyright ownership, the Apache-2.0 choice, the product
  name, and every staged artifact.

See [architecture](docs/ARCHITECTURE.md), [privacy](docs/PRIVACY.md),
[threat model](docs/THREATS.md), and [security reporting](SECURITY.md).
