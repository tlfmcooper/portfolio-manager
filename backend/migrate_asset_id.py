"""
Migration script to make asset_id nullable in transactions table.

This allows cash transactions (DEPOSIT/WITHDRAWAL) to have NULL asset_id.
"""
import sqlite3
import shutil
from pathlib import Path

def migrate_database():
    """Migrate the database to make asset_id nullable."""

    # Database path
    db_path = Path(__file__).parent / "portfolio.db"

    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    # Create backup
    backup_path = db_path.parent / f"{db_path.name}.backup_{Path(__file__).stem}"
    shutil.copy2(db_path, backup_path)
    print(f"Created backup at {backup_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check current schema
        cursor.execute("PRAGMA table_info(transactions)")
        columns = cursor.fetchall()
        print("\nCurrent schema:")
        for col in columns:
            print(f"  {col[1]}: {col[2]} (nullable={col[3] == 0})")

        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        print("\nRecreating transactions table with nullable asset_id...")

        # Get existing data
        cursor.execute("SELECT * FROM transactions")
        existing_data = cursor.fetchall()
        print(f"Found {len(existing_data)} existing transactions")

        # Drop old table and recreate with correct schema
        cursor.execute("DROP TABLE IF EXISTS transactions_old")
        cursor.execute("ALTER TABLE transactions RENAME TO transactions_old")

        # Create new table with nullable asset_id
        cursor.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER NOT NULL,
                asset_id INTEGER,
                transaction_type VARCHAR NOT NULL,
                quantity FLOAT,
                price FLOAT NOT NULL,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                notes TEXT,
                realized_gain_loss FLOAT,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
                FOREIGN KEY (asset_id) REFERENCES assets(id)
            )
        """)

        # Copy data back
        if existing_data:
            cursor.execute("""
                INSERT INTO transactions
                SELECT * FROM transactions_old
            """)
            print(f"Migrated {len(existing_data)} transactions")

        # Drop old table
        cursor.execute("DROP TABLE transactions_old")

        # Verify new schema
        cursor.execute("PRAGMA table_info(transactions)")
        columns = cursor.fetchall()
        print("\nNew schema:")
        for col in columns:
            print(f"  {col[1]}: {col[2]} (nullable={col[3] == 0})")

        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        conn.rollback()
        print(f"Database was not modified. Backup is at {backup_path}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
