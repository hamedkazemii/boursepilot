from services.portfolio.service import PortfolioService
from core.database.connection import get_database

db = get_database()
ps = PortfolioService(db)

# Get first user
user = db.fetchone("SELECT * FROM users LIMIT 1")
print(f"User: {user['id']} - {user['telegram_id']}")

# Add some test holdings
pf = ps.upsert_holding(user['id'], "عیار", quantity=100, avg_cost=1500000)
pf = ps.upsert_holding(user['id'], "سرو", quantity=200, avg_cost=800000)
pf = ps.upsert_holding(user['id'], "توان", quantity=150, avg_cost=1200000)

pf = ps.get_portfolio(user['id'])
print(f"Portfolio: {pf['portfolio']['name']} (id={pf['portfolio']['id']})")
print(f"Items: {len(pf['items'])}")
for item in pf['items']:
    print(f"  {item['symbol']}: qty={item['quantity']}, avg_cost={item['avg_cost']}")