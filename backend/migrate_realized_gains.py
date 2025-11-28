"""
Migration script to calculate and update realized_gain_loss for existing SELL transactions.
Uses FIFO method to calculate cost basis.
"""
import sqlite3
from datetime import datetime

def calculate_realized_gain_loss_fifo(conn, portfolio_id, asset_id, sell_quantity, sell_price, sell_date):
    """
    Calculate realized gain/loss for a SELL transaction using FIFO method.
    """
    cur = conn.cursor()
    
    # Get all BUY transactions for this asset before the sell date, ordered by date (FIFO)
    cur.execute("""
        SELECT id, quantity, price, transaction_date 
        FROM transactions 
        WHERE portfolio_id = ? 
        AND asset_id = ? 
        AND transaction_type = 'BUY'
        AND transaction_date <= ?
        ORDER BY transaction_date
    """, (portfolio_id, asset_id, sell_date))
    
    buy_transactions = cur.fetchall()
    
    if not buy_transactions:
        print(f"  No BUY transactions found for asset_id={asset_id}")
        return None
    
    remaining_to_sell = sell_quantity
    total_cost_basis = 0.0
    
    for buy_id, buy_qty, buy_price, buy_date in buy_transactions:
        if remaining_to_sell <= 0:
            break
        
        # How many shares from this buy are we selling?
        shares_from_this_buy = min(remaining_to_sell, buy_qty)
        
        # Add to cost basis
        total_cost_basis += shares_from_this_buy * buy_price
        
        remaining_to_sell -= shares_from_this_buy
    
    # Calculate realized gain/loss
    total_proceeds = sell_quantity * sell_price
    realized_gain_loss = total_proceeds - total_cost_basis
    
    return realized_gain_loss


def migrate_realized_gains():
    """
    Migrate existing SELL transactions to have proper realized_gain_loss values.
    """
    conn = sqlite3.connect('portfolio.db')
    cur = conn.cursor()
    
    # Get all SELL transactions without realized_gain_loss
    cur.execute("""
        SELECT t.id, t.portfolio_id, t.asset_id, t.quantity, t.price, t.transaction_date, a.ticker
        FROM transactions t
        LEFT JOIN assets a ON t.asset_id = a.id
        WHERE t.transaction_type = 'SELL'
        AND t.realized_gain_loss IS NULL
    """)
    
    sell_transactions = cur.fetchall()
    
    print(f"Found {len(sell_transactions)} SELL transactions to update")
    
    updated_count = 0
    for tx_id, portfolio_id, asset_id, quantity, price, tx_date, ticker in sell_transactions:
        print(f"\nProcessing SELL transaction {tx_id}: {ticker}, qty={quantity}, price=${price}")
        
        realized_gl = calculate_realized_gain_loss_fifo(
            conn, portfolio_id, asset_id, quantity, price, tx_date
        )
        
        if realized_gl is not None:
            cur.execute("""
                UPDATE transactions 
                SET realized_gain_loss = ?
                WHERE id = ?
            """, (realized_gl, tx_id))
            
            print(f"  -> Updated: Realized G/L = ${realized_gl:.2f}")
            updated_count += 1
        else:
            print(f"  -> Skipped: Could not calculate realized G/L")
    
    conn.commit()
    print(f"\n\nMigration complete! Updated {updated_count} transactions.")
    
    # Verify the update
    print("\n\nVerification - Updated SELL transactions:")
    cur.execute("""
        SELECT t.id, t.quantity, t.price, t.realized_gain_loss, a.ticker
        FROM transactions t
        LEFT JOIN assets a ON t.asset_id = a.id
        WHERE t.transaction_type = 'SELL'
    """)
    
    for row in cur.fetchall():
        tx_id, qty, price, realized_gl, ticker = row
        proceeds = qty * price
        cost_basis = proceeds - (realized_gl or 0)
        print(f"  {ticker}: Qty={qty}, Price=${price:.2f}, Proceeds=${proceeds:.2f}, Cost=${cost_basis:.2f}, G/L=${realized_gl or 0:.2f}")
    
    conn.close()


if __name__ == "__main__":
    migrate_realized_gains()
