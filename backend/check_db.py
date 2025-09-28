#!/usr/bin/env python3
"""
Check database contents to see existing portfolio data.
"""

import sqlite3
import sys

def check_database():
    try:
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        
        print("=== DATABASE CONTENTS ===\n")
        
        # Check assets
        print("ASSETS:")
        cursor.execute("SELECT id, ticker, name, asset_type, sector, current_price FROM assets")
        assets = cursor.fetchall()
        if assets:
            print("ID | Ticker | Name | Type | Sector | Price")
            print("-" * 60)
            for asset in assets:
                print(f"{asset[0]} | {asset[1]} | {asset[2]} | {asset[3]} | {asset[4]} | {asset[5]}")
        else:
            print("No assets found")
        
        print("\n" + "="*60 + "\n")
        
        # Check portfolios
        print("PORTFOLIOS:")
        cursor.execute("SELECT id, user_id, name, total_value FROM portfolios")
        portfolios = cursor.fetchall()
        if portfolios:
            print("ID | User ID | Name | Total Value")
            print("-" * 40)
            for portfolio in portfolios:
                print(f"{portfolio[0]} | {portfolio[1]} | {portfolio[2]} | {portfolio[3]}")
        else:
            print("No portfolios found")
        
        print("\n" + "="*60 + "\n")
        
        # Check holdings
        print("HOLDINGS:")
        cursor.execute("""
            SELECT h.id, h.portfolio_id, h.ticker, h.quantity, h.current_price, 
                   h.average_cost, a.name 
            FROM holdings h 
            LEFT JOIN assets a ON h.asset_id = a.id
        """)
        holdings = cursor.fetchall()
        if holdings:
            print("ID | Portfolio | Ticker | Quantity | Current Price | Avg Cost | Asset Name")
            print("-" * 80)
            for holding in holdings:
                print(f"{holding[0]} | {holding[1]} | {holding[2]} | {holding[3]} | {holding[4]} | {holding[5]} | {holding[6]}")
        else:
            print("No holdings found")
        
        print("\n" + "="*60 + "\n")
        
        # Check users
        print("USERS:")
        cursor.execute("SELECT id, username, email, display_name FROM users")
        users = cursor.fetchall()
        if users:
            print("ID | Username | Email | Display Name")
            print("-" * 50)
            for user in users:
                print(f"{user[0]} | {user[1]} | {user[2]} | {user[3]}")
        else:
            print("No users found")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_database()
