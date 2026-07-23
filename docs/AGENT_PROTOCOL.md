# Sandoghchi Agent Protocol

## Purpose

This document defines how AI agents work on Sandoghchi.

## Before Any Code Change

Agent must read:

- AGENT.md
- docs/START_HERE.md
- docs/MASTER_CONTEXT.md
- docs/PROJECT_STATE.md

Then run:

git status

bash tools/agent_verify_full.sh


## After Any Change

Agent must:

1. Run verification.
2. Add or update tests.
3. Update documentation.
4. Update CHANGELOG.md.
5. Commit changes.


## Development Rules

- No feature without test.
- No API change without route verification.
- No architecture change without documentation.
- Never commit broken code.

