# Changelog

## 2026-07-23 — v0.7.0 (Trend engine + relative rank + user/AI platform)

### Added
- **Indicator Engine** (`core/indicators/engine.py`)
  - returns, EMA, RSI, MACD, ATR, Bollinger, Sharpe/Sortino, MaxDD, volume ratio
- **SmartRanker** (`core/ranking/smart_ranker.py`)
  - percentile ranking across full fund universe
  - trend-aware recommendations: strong_buy/buy/hold/reduce/sell
- **DailyAnalysisPipeline** (`core/pipeline/daily_analysis.py`)
  - live → history → indicators → smart rank → quality gate
  - history seeding when series too short
  - CLI: `tools/run_daily_analysis.py`
- **Schema v2**
  - `fund_indicators`, `users`, `portfolios`, `portfolio_items`, `watchlist`
  - `ai_memory`, `ai_lessons`, `chat_messages`
- **PortfolioService** — profile/portfolio/watchlist
- **AIAdvisor** — daily learning + Q&A (+ optional free OpenAI-compatible LLM)
- Bot commands: `/profile /risk /capital /portfolio /pf_add /pf_del /watch /ask`
- Tests: `test_smart_ranker`, `test_daily_analysis`, `test_portfolio_ai`

### Fixed
- Worst funds no longer outscore top funds
- Explanations for weak funds are weakness/risk oriented
- Ranking quality gate (`top5_avg - worst5_avg > 8`)

### Notes
- BRS may be SSL-blocked in some sandboxes; pipeline falls back to offline/demo with seeded history.
- On VPS/Iran network, live BRS path is preferred automatically.

---

## 2026-07-23 — v0.6.1 (Explain fix + bot buttons)
- Role-aware top/worst explanations
- Inline keyboards + snapshot fallback

## 2026-07-23 — v0.6.0 (History Engine + Smart Telegram Report)
- SQLite history engine
- Multi-message smart telegram reports
- GitHub workflows daily/preopen/morning

## 2026-07-22 — v0.5.0 / 0.4.0 / 0.3.0
- Telegram V1, discovery/scoring, BRS layer
