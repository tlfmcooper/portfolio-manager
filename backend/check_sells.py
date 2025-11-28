import sqlite3

conn = sqlite3.connect('portfolio.db')
cur = conn.cursor()

# Check SELL transactions
cur.execute("""
SELECT t.id, t.transaction_type, t.quantity, t.price, t.realized_gain_loss, a.ticker 
FROM transactions t 
LEFT JOIN assets a ON t.asset_id = a.id 
WHERE t.transaction_type = 'SELL'
""")
rows = cur.fetchall()
print('ALL SELL Transactions:')
for row in rows:
    print(row)
print(f'Total: {len(rows)} rows')

# Also check all transactions
print('\n\nFirst 20 Transactions:')
cur.execute("""
SELECT t.id, t.transaction_type, t.quantity, t.price, t.realized_gain_loss, a.ticker 
FROM transactions t 
LEFT JOIN assets a ON t.asset_id = a.id 
LIMIT 20
""")
rows = cur.fetchall()
for row in rows:
    print(row)

conn.close()
