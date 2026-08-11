import sqlite3
conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row

# Check kodal_disclosures schema
print("=== kodal_disclosures schema ===")
for r in conn.execute("PRAGMA table_info(kodal_disclosures)").fetchall():
    print(dict(r))

# Check if FK is still there
print("\n=== Foreign keys ===")
for r in conn.execute("PRAGMA foreign_key_list(kodal_disclosures)").fetchall():
    print(dict(r))

# Check if funds table has the symbols
print("\n=== funds with آتیه ===")
for r in conn.execute("SELECT symbol FROM funds WHERE symbol LIKE '%آتیه%' LIMIT 5").fetchall():
    print(dict(r))