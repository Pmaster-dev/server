# Pmaster-dev / server

[![Pyre](https://github.com/Pmaster-dev/server/actions/workflows/pyre.yml/badge.svg)](https://github.com/Pmaster-dev/server/actions/workflows/pyre.yml)
[![CI](https://github.com/Pmaster-dev/server/actions/workflows/ci.yml/badge.svg)](https://github.com/Pmaster-dev/server/actions/workflows/ci.yml)
[![Pages](https://github.com/Pmaster-dev/server/actions/workflows/pages.yml/badge.svg)](https://github.com/Pmaster-dev/server/actions/workflows/pages.yml)

Infrastructure and automation layer for the **Pmaster-dev** core ecosystem. Provides a serverless Python automation engine, shared OpenAPI contracts, and auth utilities consumed by downstream services built on `magician-core`, `a2a`, and the AI SDK.

📖 **Documentation →** [pmaster-dev.github.io/server](https://pmaster-dev.github.io/server)

---

## Repository layout

```
server/
├── src/
│   ├── automation/       # Core automation engine (Python package)
│   └── handoff/          # Handoff coordination module
├── auth/
│   └── utils.py          # JWT, bcrypt, session helpers
├── docs/                 # GitHub Pages documentation source
│   ├── openapi/          # Machine-readable OpenAPI contracts
│   ├── api/              # Human-readable API reference
│   └── guides/           # Getting-started guides
└── .github/
    └── workflows/        # CI, Pyre type-check, Pages deploy
```

## Quick start

```bash
# Install Python dependencies
pip install -r requirements.txt

# Use the automation engine
PYTHONPATH=src python - <<'EOF'
from automation import AutomationEngine, AutomationDefinition

engine = AutomationEngine()
engine.register_fn("greet", lambda inp: f"Hello, {inp.payload}!")
engine.define(AutomationDefinition(name="hello", triggers=["user.request"], steps=["greet"]))
results = engine.trigger_type("user.request", payload="world")
print(results[0].status)  # RunStatus.SUCCESS
EOF
```

## Documentation

Full API reference and guides are published on [GitHub Pages](https://pmaster-dev.github.io/server).  
OpenAPI contract: [`docs/openapi/automation.yaml`](docs/openapi/automation.yaml)

## Ecosystem

See [`docs/ecosystem-inventory.md`](docs/ecosystem-inventory.md) for the full cross-org architecture map.

## License

MIT
