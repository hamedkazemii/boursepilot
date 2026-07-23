# Sandoghchi Agent Protocol

Before changing code:

1. Run:
git status
bash tools/agent_check.sh

2. Read:
docs/START_HERE.md
docs/MASTER_CONTEXT.md
docs/PROJECT_STATE.md
docs/ARCHITECTURE.md

Rules:

- Do not create duplicate routers
- Do not change API prefixes without audit
- Do not commit secrets
- Do not commit database files
- Update requirements.txt after dependencies

Architecture:

api = FastAPI backend
core = intelligence engines
services = external services
web = user application
admin = management panel
