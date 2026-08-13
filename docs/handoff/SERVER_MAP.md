# BoursePilot Server Map

## Sender Server (Iran)

Role:
Sync Producer

Server:
srv9702685483

Responsibilities:

- Gateway data access
- Fund snapshot export
- Compression
- Chunk generation
- Sync transport sender

Main paths:

services/sync/
data/sync/live/


---

## Receiver Server (External)

Role:
Sync Consumer

IP:
82.115.8.100

Responsibilities:

- Receive chunks
- Validate checksum
- Store batches
- Reassemble payload
- Prepare database ingestion


Main paths:

services/receiver/
data/receiver/


---

## Data Flow

Iran Sender
    |
    |
    | HTTPS Chunk Transport
    |
    v

External Receiver (82.115.8.100)

    |
    |
    v

Database Persistence Layer (Next Phase)

    |
    |
    v

BoursePilot Analysis Engine

