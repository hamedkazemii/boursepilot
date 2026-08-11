from services.analysis.portfolio_analyzer import get_portfolio_analysis

# Find first user + portfolio
import sqlite3
conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row
user = conn.execute("SELECT id, telegram_id FROM users LIMIT 1").fetchone()
if not user:
    print("No users found")
    exit()

portfolio = conn.execute("SELECT id, name FROM portfolios WHERE user_id = ? LIMIT 1", (user["id"],)).fetchone()
if not portfolio:
    print(f"User {user['id']} has no portfolio")
    exit()

print(f"User: {user['id']} ({user['telegram_id']}) | Portfolio: {portfolio['id']} ({portfolio['name']})")

result = get_portfolio_analysis(user["id"], portfolio["id"])
print(result)