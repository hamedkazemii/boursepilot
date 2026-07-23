# صندوقچی Data Pipeline


## مسیر داده


BRS API

↓

Normalize

↓

DTO

↓

History Storage

↓

Indicator Engine

↓

SmartRanker

↓

Explain Engine

↓

Delivery


## داده‌های ذخیره‌شده

- قیمت
- حجم
- ارزش معاملات
- NAV
- orderbook
- جریان پول


## Indicators

Trend:

- EMA
- Returns


Momentum:

- RSI
- MACD


Risk:

- Sharpe
- Sortino
- Max Drawdown


## SmartRanker

روش:

Relative Ranking


عوامل:

- Trend
- Momentum
- Liquidity
- Risk
- Money Flow
- NAV


## Quality Gate

شرط:

top5_avg - worst5_avg > 8


در صورت sane=false انتشار باید هشدار دهد.
