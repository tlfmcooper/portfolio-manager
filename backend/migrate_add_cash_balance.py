#!/usr/bin/env python3
"""
Database migration script to add cash management fields.

This script adds the following fields:
- portfolios.cash_balance (default 0.0)
- transactions.realized_gain_loss (nullable)

Also updates the transaction model to allow nullable asset_id and quantity for cash transactions.
"""

import sqlite3
import sys
from pathlib import Path

def migrate_database(db_path: str = "portfolio.db"):
    """Run the migration to add cash management fields."""

    db_file = Path(db_path)
    if not db_file.exists():
        print(f"[ERROR] Database file not found: {db_path}")
        sys.exit(1)

    print(f"[INFO] Migrating database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if cash_balance column already exists
        cursor.execute("PRAGMA table_info(portfolios)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'cash_balance' not in columns:
            print("[+] Adding cash_balance column to portfolios table...")
            cursor.execute("""
                ALTER TABLE portfolios
                ADD COLUMN cash_balance REAL NOT NULL DEFAULT 0.0
            """)
            print("    [OK] cash_balance column added")
        else:
            print("    [INFO] cash_balance column already exists")

        # Check if realized_gain_loss column exists in transactions
        cursor.execute("PRAGMA table_info(transactions)")
        trans_columns = [col[1] for col in cursor.fetchall()]

        if 'realized_gain_loss' not in trans_columns:
            print("[+] Adding realized_gain_loss column to transactions table...")
            cursor.execute("""
                ALTER TABLE transactions
                ADD COLUMN realized_gain_loss REAL
            """)
            print("    [OK] realized_gain_loss column added")
        else:
            print("    [INFO] realized_gain_loss column already exists")

        # Commit changes
        conn.commit()
        print("\n[SUCCESS] Migration completed successfully!")
        print("\n[INFO] Note: The following changes were made:")
        print("   - portfolios.cash_balance: Default value set to 0.0 for all existing portfolios")
        print("   - transactions.realized_gain_loss: Set to NULL for all existing transactions")
        print("\n[IMPORTANT] You'll need to:")
        print("   1. Restart the backend server")
        print("   2. Refresh the frontend")
        print("   3. Users can now deposit cash using the 'Add Cash' button")

    except sqlite3.Error as e:
        print(f"\n[ERROR] Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    # Run migration
    migrate_database("portfolio.db")
