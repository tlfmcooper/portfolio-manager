"""
Upload local portfolio.db to production Railway instance.
Run this script locally after adding persistent volume to Railway.
Requires superuser authentication.
"""

import requests
import getpass
from pathlib import Path

# Your Railway backend URL
BACKEND_URL = "https://pm.alikone.dev"  # Your custom domain
# Alternative: Use Railway's generated domain if custom domain not set up yet
# BACKEND_URL = "https://[your-service].up.railway.app"


def login(username: str, password: str) -> str:
    """Login and get JWT token."""
    print(f"🔐 Logging in as: {username}")

    response = requests.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        data={"username": username, "password": password},
        timeout=10,
    )

    if response.status_code == 200:
        data = response.json()
        print("✅ Login successful!")
        return data["access_token"]
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None


def upload_database(token: str):
    """Upload local database to production."""
    db_path = Path(__file__).parent / "portfolio.db"

    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"\n📤 Uploading database from: {db_path}")
    print(f"📍 Target: {BACKEND_URL}/admin/upload-db")

    with open(db_path, "rb") as f:
        files = {"file": ("portfolio.db", f, "application/octet-stream")}
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = requests.post(
                f"{BACKEND_URL}/admin/upload-db",
                files=files,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                print("✅ Database uploaded successfully!")
                print(response.json())
            elif response.status_code == 401:
                print("❌ Authentication failed - check your credentials")
                print(response.text)
            elif response.status_code == 403:
                print("❌ Permission denied - user must be a superuser")
                print(response.text)
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 Portfolio Database Uploader")
    print("=" * 50)

    # Get credentials
    username = input("Username: ")
    password = getpass.getpass("Password: ")

    # Login
    token = login(username, password)

    if token:
        # Upload database
        upload_database(token)
    else:
        print("\n❌ Upload cancelled - authentication required")
