# Privacy notes

The default profile is generic and the default engine is deterministic mock.
No network calls or credentials are required. Conversations are persisted in
the local SQLite database. Treat that database and any installed profile as
private; the project does not encrypt them.

The live dialogue context consists of messages for a conversation. Recalled
memory is a separate, owner-approved selection and must not be presented as
verbatim live context. The mock does not yet perform automatic retrieval or
summarization. The public seed is an optional synthetic example and can be
omitted or removed. It is not evidence that a running agent has lived those
events.

Memory proposals require an explicit `--remember` action. A selection pass can
forget lower-ranked items, but retains them in the journaled database for
reversal. This is not a secure-delete feature. Guests are absent and must stay
disabled until storage-level namespaces and access-control tests exist.
