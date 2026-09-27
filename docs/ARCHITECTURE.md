# Architecture

The package is deliberately small and standard-library-only:

- `cli` wires bootstrap, dialogue, and memory operations.
- `storage` owns SQLite connections and applies immutable numbered SQL
  migrations, one transaction per migration. The migration ledger rejects
  unknown future versions.
- `persona` loads a local persona file and provides a neutral default. An
  explicit flag installs the optional public seed sample.
- `engine` defines a synchronous generation contract and deterministic mock.
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
multi-process access. There are no tools with host capabilities.
