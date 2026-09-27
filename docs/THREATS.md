# Threat and trust notes

## In scope

This slice runs locally under the invoking user's operating-system account and
stores messages and optional memory in SQLite. Inputs may contain hostile text.
The mock treats them only as text; the optional remote model may interpret
them. Provider and Telegram adapters add network and credential boundaries.

## Defaults

- Mock only by default. Provider and Telegram adapters are opt-in; there is no
  web server, guest mode, or tool execution.
- Memory is opt-in per proposal. Selection/forgetting is explicit and
  reversible; the journal is not secure deletion.
- No claim of tenant isolation or sandboxing. Do not expose this local database
  to another user or service.
- Initiative can suggest a next step, never authorize or execute one.

## Known limitations

Filesystem permissions depend on the host. SQLite is not encrypted. The
selection score is a deterministic demonstration, not a semantic relevance or
consent classifier. The provider receives the current turn and persona name;
there is no prompt redaction, provider retention control, or automatic history
retrieval. Telegram uses HTTPS long polling, an environment-only bot token, and
a sender allowlist checked before model dispatch; it ignores groups but cannot
protect content if the owner account or Telegram itself is compromised. There
is no backup protocol, retention scheduler, or secure erase. Keep integrations
disabled unless their data flows are accepted and reassess before sharing state.
