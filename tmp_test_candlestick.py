import sys
sys.path.insert(0, ".")
from services.sync.candlestick_backfill import run_candlestick_backfill
result = run_candlestick_backfill()
print("Result:", result)