# صندوقچی Deployment Specification

## هدف

استقرار پایدار صندوقچی برای استفاده واقعی.


# Environment


## Development

محیط توسعه:

- Python 3.11+
- Virtual Environment
- SQLite


## Production

پیشنهاد:

- VPS
- Linux
- PostgreSQL
- Nginx
- HTTPS


---

# Services


## API Server

FastAPI + Uvicorn


Run:

uvicorn api.main:app --host 0.0.0.0 --port 8080


---

## Telegram Bot

Process دائم:


tools/run_telegram_bot.py


پیشنهاد:

systemd service


---

## Scheduler


وظایف:


صبح:

- history sync
- analysis
- telegram publish


روز:

- refresh data


شب:

- backup


---

# Environment Variables


نمونه:


BRS_API_KEY

TELEGRAM_BOT_TOKEN

DATABASE_PATH

AI_API_KEY

JWT_SECRET


هیچ secret داخل Git ذخیره نشود.


---

# Monitoring


مانیتور شود:


- API health
- Database
- Pipeline status
- Telegram status
- Data freshness


---

# Backup


بکاپ:

- Database
- Reports
- Configuration

به صورت روزانه.
