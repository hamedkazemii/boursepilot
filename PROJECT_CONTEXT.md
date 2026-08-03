# Sandoghchi Project Context

Project:
BoursePilot / صندوقچی

Repository:
hamedkazemii/boursepilot

Branch:
feature/architecture-v2-sync

Environment:
Ubuntu VPS

Stable Components:

Sync V1:
- Sender transport
- Receiver storage
- Snapshot transfer
- Chunk validation
- Reassembly

Status:
STABLE


Rules:

Never:
- Break Sync V1
- Create duplicate providers
- Delete production data
- Apply uncontrolled migrations


Workflow:

REQUEST
AUDIT
PLAN
IMPLEMENT
REVIEW
TEST
CHECKPOINT
