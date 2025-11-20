"""
Upload local portfolio.db to production Railway instance.
Run this script locally after adding persistent volume to Railway.
"""
import requests
import os
from pathlib import Path

# Your Railway backend URL
BACKEND_URL = "https://pm.alikone.dev"  # Your custom domain
# Alternative: Use Railway's generated domain if custom domain not set up yet
# BACKEND_URL = "https://[your-service].up.railway.app"

def upload_database():
    """Upload local database to production."""
    db_path = Path(__file__).parent / "portfolio.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return
    
    print(f"📤 Uploading database from: {db_path}")
    print(f"📍 Target: {BACKEND_URL}/admin/upload-db")
    
    with open(db_path, 'rb') as f:
        files = {'file': ('portfolio.db', f, 'application/octet-stream')}
        
        try:
            response = requests.post(
                f"{BACKEND_URL}/admin/upload-db",
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ Database uploaded successfully!")
                print(response.json())
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    upload_database()
