from services.portfolio.service import PortfolioService
from core.database.connection import get_database

db = get_database()
ps = PortfolioService(db)

# Get first user
user = db.fetchone("SELECT * FROM users LIMIT 1")
print(f"User: {user['id']} - {user['telegram_id']}")

pf = ps.get_portfolio(user['id'])
print(f"Portfolio: {pf['portfolio']['name']} (id={pf['portfolio']['id']})")
print(f"Items: {len(pf['items'])}")
for item in pf['items']:
    print(f"  {item['symbol']}: qty={item['quantity']}, avg_cost={item['avg_cost']}")