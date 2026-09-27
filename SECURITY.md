# Security policy

This is a local-only release candidate. It includes optional, disabled-by-
default provider and owner-only Telegram adapters, but no network listener,
guest mode, or task executor. Please do not put real personal conversations or
credentials into public issues.

Report suspected vulnerabilities privately to the project maintainer through
an owner-designated private channel. Include a concise impact description and
reproduction that uses synthetic data. Do not attach databases, transcripts,
tokens, or private profile files. A response time and supported release policy
have not yet been established.

The local SQLite database and profile are private user data. Back them up and
restrict filesystem access under the operator's control. The mock engine does
not establish provider-side privacy properties. Enabling an adapter creates
the network flows documented in `docs/PRIVACY.md`.
