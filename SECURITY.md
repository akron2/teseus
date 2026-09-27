# Security policy

This is an early local-only staging slice. No network listener, provider
adapter, guest mode, or task executor is included. Please do not put real
personal conversations or credentials into public issues.

Report suspected vulnerabilities privately to the project maintainer through
an owner-designated private channel. Include a concise impact description and
reproduction that uses synthetic data. Do not attach databases, transcripts,
tokens, or private profile files. A response time and supported release policy
have not yet been established.

The local SQLite database and profile are private user data. Back them up and
restrict filesystem access under the operator's control. The mock engine does
not establish the privacy properties of any future remote adapter.
