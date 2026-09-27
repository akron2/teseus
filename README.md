# Teseus Harness

A local, single-owner harness for a personal agent with **memory, forgetting,
and initiative**. This local-only release candidate provides bootstrap,
versioned SQLite state, persona loading, a deterministic mock dialogue, and
explicit memory-selection journaling. Optional adapters provide
OpenAI-compatible chat-completions over HTTPS and owner-only Telegram text
polling. It uses Python 3.11+ and the standard library; the default mock needs
no network, provider account, or secret.

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

## Optional model provider

The `Engine` contract is synchronous `generate(text, persona_name) ->
EngineReply`. `MockEngine` remains the default and never uses the network. To
select the optional OpenAI-compatible adapter, configure `HARNESS_ENGINE`,
`HARNESS_OPENAI_API_KEY`, and `HARNESS_OPENAI_MODEL` in the process environment;
`HARNESS_OPENAI_BASE_URL` defaults to `https://api.openai.com/v1` and
`HARNESS_OPENAI_TIMEOUT` defaults to 30 seconds (allowed range: 0.1–120). The
adapter sends only the current turn and persona name, and does not log prompts,
keys, response bodies, or provider errors. Provider requests disclose the turn
to the configured service. Dialogue content and responses are stored in local
SQLite as before. Configuration is not read from TOML or `.env` automatically.

```sh
export HARNESS_ENGINE=openai-compatible
export HARNESS_OPENAI_API_KEY  # Set this variable privately before exporting it.
export HARNESS_OPENAI_MODEL='<provider model name>'
PYTHONPATH=src python -m harness dialogue --data-dir ./local-state --text 'Hello'
```

## Optional owner-only Telegram

Telegram is disabled unless explicitly enabled and `telegram-poll` is run. Set
`HARNESS_TELEGRAM_ENABLED=true`, `HARNESS_TELEGRAM_BOT_TOKEN`, and comma-
separated numeric `HARNESS_TELEGRAM_OWNER_IDS` in the environment. Long polling
processes private text messages only; sender IDs are checked against the
allowlist before the dialogue engine is called. Unknown senders receive a
generic denial, and group chats, non-text updates, and malformed updates are
ignored. The token is used only in HTTPS Bot API requests and is not logged.
Never place a real token in source control.

```sh
PYTHONPATH=src python -m harness telegram-poll --data-dir ./local-state
```

Both adapters have mocked-transport unit tests and require no live credentials
or network for the test suite. See [architecture](docs/ARCHITECTURE.md),
[privacy](docs/PRIVACY.md), and [threat model](docs/THREATS.md).

## Boundaries and status

- One local owner only. Guests and shared-memory access are unsupported and
  disabled. A prompt is not an access-control boundary.
- Web, attachments, mail, background consolidation, and task execution are not
  included. The provider and Telegram integrations above are optional and
  disabled by default.
- There is no shell/tool executor, host-write capability, privileged mode, or
  automatic external action. Initiative is a suggestion requiring a person.
- The seed-memory is a public, synthetic example expressing a ship metaphor,
  selective/forgettable memory, context versus recollection, reversibility,
  verifiable trust, and bounded initiative. It contains no private dialogue.
- This release candidate has a local-only history. Do not publish until an
  owner confirms copyright ownership/attribution, the Apache-2.0 choice, the
  product name, and every staged artifact. Attribution remains an explicit
  release blocker; see [review](REVIEW.md).

See [architecture](docs/ARCHITECTURE.md), [privacy](docs/PRIVACY.md),
[threat model](docs/THREATS.md), and [security reporting](SECURITY.md).
