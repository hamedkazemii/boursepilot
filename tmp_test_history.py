import sys
sys.path.insert(0, ".")
from services.sync.history_backfill import run_history_backfill
result = run_history_backfill()
print("Result:", result)