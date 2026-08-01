# BoursePilot Project Handoff

## Current Branch

feature/architecture-v2-sync


## Current Milestone

Sync V1 Production Transport Completed


## Server Architecture


### Sender Server (Iran)

Hostname:
srv9702685483

Role:
SYNC PRODUCER


Responsibilities:

- Market data collection
- BRS/Gateway provider
- Fund snapshot generation
- Compression
- Chunk creation
- HTTPS transport sender


Main Modules:

services/providers/

services/sync/

data/sync/live/


---

### Receiver Server (External)

IP:

82.115.8.100


Role:

SYNC CONSUMER


Responsibilities:

- Receive manifest
- Receive chunks
- Validate checksum
- Reassemble batches
- Prepare persistence layer


Main Modules:

services/receiver/


Storage:

data/receiver/


---

# Current Sync V1 Status


Status:

STABLE


Validated Flow:

Iran Sender

        |

        |

 HTTPS Transport

        |

        v


External Receiver


Validated Batch:

funds-production-sync-001


Payload:

funds_latest.json.gz


Chunks:

26


Validation:

[x] Manifest received

[x] Chunk transfer

[x] Checksum validation

[x] Reassembly


---

# Architecture Rules


DO NOT BREAK:

1. Sync transport protocol

2. Receiver API contract

3. Sender chunk format

4. Existing provider abstraction


---

# Next Development Phase


## Receiver Persistence Layer


Goal:

Move received batches from file storage into production database.


Current:

data/receiver/

Temporary storage


Target:

SQLite/PostgreSQL persistence


Expected modules:

services/receiver/

core/database/


---

# Agent Instructions


Before any task:

1. Read this document.

2. Inspect current branch.

3. Do not redesign architecture without approval.

4. Continue from current milestone.

5. Keep sender and receiver separation.


