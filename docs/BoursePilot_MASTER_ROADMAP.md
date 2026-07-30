# BoursePilot Master Development Roadmap

Version: v1.6+
Status: Active Development Guide


# 1. Product Identity

BoursePilot is an intelligent investment assistant specialized in Iranian ETF markets.

The mission:

Transform market data into understandable, actionable and personalized investment insights for Persian-speaking users.

BoursePilot is not a trading bot.
It does not execute orders.
It does not guarantee investment returns.

It is an AI-powered investment intelligence platform.


# 2. Target Users

Primary users:

Persian-speaking Iranian investors.

User interaction language:

- Persian (Farsi) by default.
- Technical terms may remain in English when commonly used.
- Reports must be understandable for non-professional investors.

Communication style:

- Human.
- Educational.
- Clear.
- Avoid unnecessary financial jargon.
- Explain the reason behind every recommendation.


# 3. Product Evolution

## Phase History

v0.x
- Data collection foundation.

v0.6
- Historical engine.
- Smart reports.

v0.7
- Trend engine.
- Relative ranking.
- Portfolio.
- AI advisor.

v0.9
- Stable intelligent reporting.

v1.3
- Advisor engine.

v1.4
- Smart portfolio advisor.

v1.5
- Intelligent platform.
- Bubble analysis.
- Human Telegram reporting.


# 4. Current Architecture


Data Layer:

- BRS API
- TSETMC data providers
- Market history
- SQLite storage
- Cached snapshots


Intelligence Layer:

- Indicators
- Trend engine
- Ranking engine
- Bubble analysis
- Scoring system
- Quality gate


Advisor Layer:

- Portfolio analysis
- Risk profile
- AI recommendations
- Watchlist


Communication Layer:

- Telegram Bot
- Human readable reports
- Interactive conversations


# 5. Infrastructure Architecture


## Production Data Server (Iran)

Purpose:

Market data acquisition.

Responsibilities:

- Connect to Iranian market sources.
- Collect TSETMC/BRS data.
- Store market snapshots.
- Provide reliable internal API if needed.


## Development / AI Server

Purpose:

Development and intelligence operations.

Responsibilities:

- OpenClaw agent.
- Testing.
- Analysis.
- Automation.
- CI/CD tasks.


Development agents must not assume the data server and development server are the same machine.


# 6. Development Principles


Always follow:

1. Understand before coding.
2. Review architecture before changing architecture.
3. Prefer incremental changes.
4. Never break existing stable features.
5. Write tests for important logic.
6. Document significant changes.
7. Use conventional commits.


Before every development task:

Run:

git status
git branch
git log --oneline -5


Before architectural changes:

Review:

ARCHITECTURE.md
ARCHITECTURE_REVIEW.md
ROADMAP.md
BoursePilot_Product_Blueprint_v1.5.md


# 7. v1.6 Roadmap


## Sprint 1 - Reliability Foundation


Goal:

Make the platform production reliable.


Tasks:

- Provider fallback mechanism.
- Better API error handling.
- Data freshness monitoring.
- Structured logging.
- Failure notifications.
- Improve test coverage.


Definition of Done:

- External API failures are handled gracefully.
- System can explain data problems.
- Automated tests pass.


---

## Sprint 2 - Intelligent Alert Engine


Goal:

Move from passive reports to proactive intelligence.


Features:

- NAV deviation alerts.
- Trend reversal alerts.
- Volume anomaly detection.
- Ranking movement alerts.
- Market condition alerts.


Architecture:

core/alerts/


Output:

Persian Telegram notifications with explanation.


Example:

"صندوق X امروز ۳ رتبه در امتیاز BPI رشد کرده است.
دلیل:
- بهبود روند
- افزایش حجم معاملات
- کاهش حباب NAV"


---

## Sprint 3 - Fund Comparison Engine


Goal:

Enable intelligent comparison.


Features:

- Compare multiple funds.
- Performance comparison.
- Risk comparison.
- Ranking comparison.
- Human explanation.


Example:

"مقایسه صندوق‌های طلا، عیار و کهربا"


---

## Sprint 4 - Investor Profile


Goal:

Personalized investment assistant.


Collect:

- Investment amount.
- Risk tolerance.
- Investment horizon.
- Goals.


Generate:

- Personalized portfolio analysis.
- Suitability recommendations.
- Risk warnings.


---

# 8. Future Roadmap


## v1.7

Web dashboard.

Features:

- User accounts.
- Portfolio dashboard.
- Advanced reports.
- AI chat.


## v2.0

Intelligent Wealth Platform.

Features:

- Personal financial intelligence.
- Multi asset analysis.
- Advanced investor assistant.


# 9. Telegram Product Rules


Telegram is the first user interface.

Bot should:

- Speak Persian.
- Explain concepts.
- Ask questions naturally.
- Remember user preferences when implemented.
- Avoid technical raw outputs.


Bad:

"RSI=32 MACD=-0.5"


Good:

"نشانه‌هایی از ضعف کوتاه‌مدت دیده می‌شود، اما روند بلندمدت هنوز مثبت است."


# 10. AI Agent Operating Rules


The development agent role:

Senior Software Architect + Developer.


The agent must:

- Analyze before coding.
- Create implementation plan first.
- Ask approval for major architectural changes.
- Keep commits small and meaningful.
- Avoid unnecessary refactoring.
- Protect stable features.


The agent must not:

- Create new repositories.
- Ignore existing architecture.
- Rewrite working systems without reason.
- Add unnecessary dependencies.


# 11. Quality Standard


Every feature requires:

- Code review.
- Tests.
- Documentation update.
- Git commit.
- Clear changelog entry.


BoursePilot development follows production software engineering standards.


