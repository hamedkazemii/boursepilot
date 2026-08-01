# BoursePilot Agent Continuation Context

## Project

Name:
BoursePilot

Product:
صندوقچی

Repository:
hamedkazemii/boursepilot


## Current Branch

feature/architecture-v2-sync


## Current Stable Milestone

Architecture V2 Sync Baseline


Latest commits:

0babc19 docs: create complete project handoff baseline

cbbf206 docs(sync): fix sender receiver server mapping

934af4d feat(sync): finalize sender transport v1 with real snapshot flow


## Server Architecture


### Sender Server (Iran)

Role:

Sync Producer


Server:

srv9702685483


Responsibilities:

- Market data collection
- BRS provider access
- Snapshot generation
- Compression
- Chunk generation
- HTTPS transport


Main modules:

services/providers/

services/sync/


Data:

data/sync/

data/snapshots/


---


### Receiver Server (External)

Role:

Sync Consumer


IP:

82.115.8.100


Responsibilities:

- Receive manifests
- Receive chunks
- Validate checksum
- Reassemble payload
- Prepare persistence layer


Main modules:

services/receiver/


Data:

data/receiver/


## Sync V1 Status

Status:

STABLE


Validated:

[x] Real sender to receiver transfer

[x] Manifest delivery

[x] Chunk transfer

[x] Checksum validation

[x] Reassembly


Production batch:

funds-production-sync-001


Payload:

funds_latest.json.gz


Chunks:

26


Important:

Do NOT rewrite Sync V1 transport unless required.

Current transport is considered baseline.


## Current Architecture


Flow:


BRS Provider

    |

    v

Snapshot Collector

    |

    v

Sync Exporter

    |

    v

Chunk Transport

    |

    v

External Receiver

    |

    v

Persistence Layer (Next Phase)

    |

    v

Analysis Engine


## Database Status


Current:

SQLite exists.


Path:

data/database.db


Database layer:

core/database/


Receiver does NOT persist into DB yet.


Next major task:

Receiver Persistence Layer.


## Agent Rules


Before coding:

1. Read this file.

2. Read:

docs/handoff/PROJECT_HANDOFF.md

docs/architecture/CURRENT_ARCHITECTURE.md

docs/operations/SERVER_STATUS.md


3. Check git branch.

4. Do not create duplicate architecture.

5. Do not create parallel providers.

6. Preserve Sync V1.


## Next Recommended Development Tasks


Phase 1:

Receiver Persistence Layer

Goal:

Move received batches from file storage into database safely.


Phase 2:

History Engine integration


Phase 3:

Smart Ranking pipeline using synced data


Phase 4:

Telegram and Web API expansion


## Important Decisions


Provider architecture:

BRS is primary market provider.


Legacy TSETMC code should not become another data path.


Sync architecture:

Push model:

Iran Sender

-->

External Receiver


## Repository Standard


One repository.

One architecture.

One source of truth.


