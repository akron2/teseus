# Contributing

Keep the default install local, deterministic, and credential-free. Changes to
memory, persona handling, persistence, or future integrations need tests for
consent, deletion/reversal, and privacy boundaries. Never contribute real
conversation-derived fixtures, credentials, personal identifiers, machine
configuration, or generated runtime state.

Before proposing a change, run:

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests
python scripts/release_guard.py
```

External adapters and capabilities require a separate threat/privacy review;
model instructions alone cannot grant access or enforce isolation.
