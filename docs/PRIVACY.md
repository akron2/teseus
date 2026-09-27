# Privacy notes

The default profile is generic and the default engine is deterministic mock.
No network calls or credentials are required by default. Conversations are
persisted in the local SQLite database. Treat that database and any installed profile as
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

The optional OpenAI-compatible adapter is selected only by environment and
sends the current turn and persona name to the configured HTTPS provider. It
does not transmit stored conversation history or memory and does not log
prompts, keys, raw response bodies, or full replies. The full conversation turn
and returned reply are still persisted locally; provider retention and handling
are governed by that service and the operator's account/settings.

The optional Telegram poller is disabled by default and requires an explicit
enable flag, bot token, and numeric owner ID allowlist. It checks the Telegram
sender before model dispatch, processes private text messages only, and ignores
group chats. The bot token is sent to Telegram over HTTPS and is never printed
by the adapter. Adapter tests inject mocked transports and make no live
requests.
