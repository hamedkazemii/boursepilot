# BoursePilot Product Blueprint v1.5

## 1. Product Vision
BoursePilot is an autonomous, intelligent investment assistant for Iranian ETFs. The mission is to transform raw market data into actionable, explainable, and personalized financial insights through a conversational Telegram interface, empowering users with data-driven portfolio management and market intelligence.

## 2. Current Capabilities
- **Robust Data Pipeline:** SQLite-based incremental history engine and market snapshots.
- **Bubble Analysis:** NAV and market price analysis to identify premium/discount and valuation bubbles.
- **Analysis Quality Control:** Automated sanity checks (e.g., top/worst fund average performance gap) to validate ranking quality.
- **Analytical Engine:** Advanced indicator library (technical, risk-adjusted, momentum, NAV-based).
- **Intelligent Ranking:** Smart, trend-aware relative ranking with quality gating.
- **AI-Driven Personalization:** AI Advisor with daily learning capabilities, portfolio tracking, and watchlist management.
- **Conversational UX:** Multi-message, role-aware Telegram reports with inline interaction buttons.

## 3. User Journeys
- **Daily Market Briefing:** User receives automated morning/daily report -> Reviews top/worst performers -> Understands the "why" via AI-generated explanations.
- **Portfolio Management:** User checks portfolio health -> Adds/removes funds -> Asks AI for adjustments based on risk profile and horizon.
- **Intelligent Alerts:** User receives real-time notification on volume spikes or technical level breaks -> Reviews immediate signal context.
- **Market Research:** User searches for funds (`/search`) -> Compares specific metrics -> Adds promising funds to a personal watchlist.

## 4. Feature Matrix

| Feature | Status | Priority |
| :--- | :--- | :--- |
| Market Data Integration (BRS) | ✅ | High |
| History Engine | ✅ | High |
| Indicator Engine | ✅ | High |
| Smart Ranking | ✅ | High |
| AI Advisor (Learning + Q&A) | ✅ | High |
| Portfolio Management | ✅ | High |
| Real-time Alerts | ❌ | High (v1.6) |
| Fund Comparison | ❌ | Medium (v1.6) |

## 5. v1.6 Goals
- **Real-time Vigilance:** Introduce event-driven scanning for immediate market signals (e.g., volume spikes, price level breaks).
- **Comparative Intelligence:** Enable side-by-side fund performance comparison.
- **Robustness:** Enhance resilience against external API failures (BRS/TSETMC) and network instability.

## 6. Technical Priorities
- **Refining Pipeline:** Decouple market analysis from daily ranking to enable independent high-frequency scanning.
- **Scalability:** Optimize historical data access patterns to maintain performance as indicator series grow.
- **Reliability:** Enhance data provider fallback strategies and logging.

## 7. Out of Scope (Explicitly Deferred)
- **Direct Execution:** No brokerage integration or automated order placement.
- **Complex Financial Instruments:** Strictly focused on Iranian ETFs (no single-stock or derivative analysis).
- **Multi-platform UI:** Telegram remains the sole conversational interface.
- **Financial Guarantee Disclaimer:** BoursePilot provides analytical insights only; it is not a financial advisor. All investment decisions are the sole responsibility of the user.
