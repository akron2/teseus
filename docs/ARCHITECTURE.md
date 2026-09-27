# Architecture

The package is deliberately small and standard-library-only:

- `cli` wires bootstrap, dialogue, and memory operations.
- `storage` owns SQLite connections and applies immutable numbered SQL
  migrations, one transaction per migration. The migration ledger rejects
  unknown future versions.
- `persona` loads a local persona file and provides a neutral default. An
  explicit flag installs the optional public seed sample.
- `engine` defines the synchronous `generate(text, persona_name) -> EngineReply`
  contract and deterministic default mock. `openai_compatible` implements that
  contract with standard-library HTTPS chat-completions and a bounded timeout.
- `telegram` is a separately invoked long-polling transport. It accepts private
  text messages, checks sender IDs against the configured owner allowlist, then
  calls the dialogue handler. It has no guest mode and does not expose an HTTP
  listener.
- `memory` handles explicit proposals, deterministic selection, reversible
  forgetting, and an append-only event journal.

Current-turn messages are stored as conversation history. They are not silently
converted to long-term memory. A caller must explicitly propose a memory item;
the selection cycle keeps a bounded set and records forget/restore events.
Forget currently means excluded from active retrieval, not secure erasure: the
item and audit event remain in the local database so the decision is reversible.

SQLite data is private runtime state and lives outside source control. The
database is created locally with foreign keys enabled. This version does not
claim multi-user isolation, encrypted-at-rest storage, or safe concurrent
multi-process access. There are no tools with host capabilities. Provider
selection is environment-only and opt-in; Telegram additionally requires an
explicit enable flag and command. Adapter transports are injectable for offline
unit tests. Adapter errors are reduced to generic messages rather than
including provider bodies, request URLs, or exception details. Neither adapter
logs credentials, prompts, or full responses.

The provider transmits the current user turn and persona name to the configured
endpoint; it does not retrieve conversation history or memory. Telegram long
polling sends the bot token in the HTTPS Bot API URL, as required by that API.
Only private chats whose chat ID equals an allowlisted sender ID are dispatched.
