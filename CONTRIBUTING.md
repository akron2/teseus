# Contributing

Keep the default install local, deterministic, and credential-free. Changes to
memory, persona handling, persistence, or future integrations need tests for
consent, deletion/reversal, and privacy boundaries. Never contribute real
conversation-derived fixtures, credentials, personal identifiers, machine
configuration, or generated runtime state.

Before proposing a change, run:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/harness-pycache python -m compileall -q src tests
PYTHONPATH=src python -c 'import harness, harness.cli, harness.engine, harness.memory, harness.openai_compatible, harness.persona, harness.storage, harness.telegram'
python scripts/release_guard.py
```

External adapters and capabilities require tests with mocked transports and a
threat/privacy review; model instructions alone cannot grant access or enforce
isolation. Do not invent a copyright holder or attribution. The project is
licensed under Apache-2.0; retain verified notices where applicable.
