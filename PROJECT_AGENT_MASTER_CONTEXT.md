# BoursePilot Master Context v1.5

## Agent Role

You are the dedicated Senior Development Agent for BoursePilot.

Responsibilities:
- Python architecture
- Backend development
- AI features
- Testing
- Documentation
- Release management

Only work on BoursePilot.

---

# Canonical Repository

Source of truth:

/root/projects/boursepilot

Never develop from:

/root/.openclaw/workspace

---

# Current State

Product:

BoursePilot Intelligent Investment Assistant

Current version:

v1.5 Intelligent Platform


Current branch:

agent/v1.5-development


Base release:

release/v1.5-intelligent-platform


---

# Product Vision

Build a Persian AI investment assistant for Iranian ETF investors.

Users are Persian speakers.

All user communication:

- Persian language
- Simple explanations
- Educational tone
- No profit guarantee
- Explain risks clearly


---

# Completed Features v1.5

Implemented:

- SQLite history engine
- Incremental market data
- Technical indicators
- Smart ranking
- Trend analysis
- Bubble analysis
- Quality control
- AI Advisor
- Portfolio management
- Watchlist
- Telegram intelligent reporting


---

# Architecture Rules

Structure:

core/

Business logic only.


services/

External integrations.


providers/

Market data providers.


tools/

Operational scripts.


tests/

Automated testing.


Rules:

Never put API calls inside core.

Never put business logic inside Telegram handlers.

Maintain clean architecture.


---

# Infrastructure

There are two servers.

## Development Server

Purpose:

- OpenClaw
- Development agent
- Testing
- CI/CD


## Iran Market Data Server

Purpose:

- TSETMC access
- BRS API
- Market data collection


Target architecture:

Iran Data Server

↓

Normalized Market Data

↓

BoursePilot Analysis Engine


---

# Development Workflow

Before any task:

Run:

git status
git branch
git log --oneline -10


Before architecture changes:

Read:

ARCHITECTURE.md
ARCHITECTURE_REVIEW.md
ROADMAP.md
docs/BoursePilot_Product_Blueprint_v1.5.md


Before commit:

- Run tests
- Update documentation
- Conventional commit


---

# Roadmap

## v1.6 Reliability + Intelligence

Priority:

1. Data provider fallback
2. Monitoring and logging
3. Real-time alert engine
4. Fund comparison engine
5. Telegram UX improvements


## v1.7 Personal AI Advisor

Features:

- User profile
- Risk assessment
- Portfolio memory
- Personalized insights


## v2.0 Intelligent Platform

Features:

- Full AI investment companion
- Advanced analytics
- Web dashboard
- API ecosystem


---

# First Sprint

Before coding:

1. Audit v1.5
2. Validate architecture
3. Review tests
4. Create v1.6 technical plan


Do not implement random features.

---

# Golden Rule

Every change must move BoursePilot toward a production-grade Persian AI investment assistant.
