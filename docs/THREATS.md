# Threat and trust notes

## In scope

This slice runs locally under the invoking user's operating-system account and
stores messages and optional memory in SQLite. Inputs may contain hostile text;
the mock treats them only as text. Future engines, channels, and tools would
add separate trust boundaries.

## Defaults

- Mock only; no credentials, network, web server, Telegram, guests, or tools.
- Memory is opt-in per proposal. Selection/forgetting is explicit and
  reversible; the journal is not secure deletion.
- No claim of tenant isolation or sandboxing. Do not expose this local database
  to another user or service.
- Initiative can suggest a next step, never authorize or execute one.

## Known limitations

Filesystem permissions depend on the host. SQLite is not encrypted. The
selection score is a deterministic demonstration, not a semantic relevance or
consent classifier. There is no external-engine redaction, backup protocol,
retention scheduler, or secure erase yet. Reassess the threat model before
adding any integration or sharing state.
