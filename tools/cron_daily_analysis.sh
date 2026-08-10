#!/bin/bash
# Cron wrapper for daily analysis
cd /root/projects/boursepilot
/root/projects/boursepilot/venv/bin/python tools/run_daily_analysis.py --no-seed >> /var/log/boursepilot/daily_analysis.log 2>&1