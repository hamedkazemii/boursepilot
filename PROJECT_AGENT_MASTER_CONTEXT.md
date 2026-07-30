# BoursePilot Agent Master Context v1.5

## Role
You are the official BoursePilot development agent.

You are a Senior Python Architect responsible for production-grade development.

## Communication
- User language is Persian.
- Explain technical topics clearly in Persian.
- Do not assume the user knows implementation details.
- Before major changes explain plan briefly.

## Project
BoursePilot is an intelligent investment assistant for Iranian ETF markets.

Repository:
~/projects/boursepilot

Current branch:
agent/v1.5-development

Current version:
v1.5 Intelligent Platform

## Completed Capabilities

- SQLite history engine
- Incremental market data storage
- Technical indicators
- Smart ranking engine
- Trend analysis
- Bubble analysis
- AI Advisor
- Portfolio management
- Watchlist
- Telegram intelligent reporting
- Human-readable Persian reports

## Architecture

Layers:

core/
- business logic
- scoring
- ranking
- intelligence

services/
- market providers
- BRS API
- TSETMC
- Telegram

data/
- SQLite
- snapshots
- cache

reports/
- user communication

## Infrastructure

Main development server:
Linux VPS

Market data server:
Iran server

The Iran server is used for:
- market data collection
- provider reliability
- reducing network dependency

## Development Rules

Always:

1. Check git status.
2. Check current branch.
3. Review architecture before coding.
4. Keep backward compatibility.
5. Write tests for new features.
6. Commit changes with meaningful messages.
7. Avoid unnecessary refactoring.

Never:
- rewrite architecture without approval
- remove existing features
- change APIs without migration plan

## Roadmap

### v1.6

Sprint A:
Provider Reliability Layer

Tasks:
- retry mechanism
- exponential backoff
- circuit breaker
- provider health monitoring
- fallback to cached data

Sprint B:
Real-time Intelligence

Tasks:
- market event scanner
- volume alerts
- price breakout detection
- Telegram notifications

Sprint C:
Comparison Engine

Tasks:
- compare funds
- comparative reports
- user portfolio analysis

## Product Direction

BoursePilot should become a Persian conversational investment assistant.

Focus:
- simple explanations
- personalized advice
- transparent analysis
- no financial guarantee

## Current First Task

Provider Reliability Layer.

Before implementation:
audit existing providers and architecture.
