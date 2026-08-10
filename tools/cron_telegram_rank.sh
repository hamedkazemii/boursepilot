#!/bin/bash
# Cron wrapper for telegram rank
cd /root/projects/boursepilot
/root/projects/boursepilot/venv/bin/python tools/run_telegram_rank.py --smart >> /var/log/boursepilot/telegram_rank.log 2>&1