"""
Upload local portfolio.db to production Railway instance.
Run this script locally after adding persistent volume to Railway.
Requires superuser authentication.
"""

import os
import requests
import getpass
from pathlib import Path

# Your Railway backend URL (use env var if set so we always hit the API service)
BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://protective-playfulness-production.up.railway.app",
)
ADMIN_UPLOAD_TOKEN = os.getenv("ADMIN_UPLOAD_TOKEN")


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


def upload_database(token: str | None, admin_token: str | None = None):
    """Upload local database to production."""
    db_path = Path(__file__).parent / "portfolio.db"

    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return

    print(f"\n📤 Uploading database from: {db_path}")
    print(f"📍 Target: {BACKEND_URL}/admin/upload-db")

    with open(db_path, "rb") as f:
        files = {"file": ("portfolio.db", f, "application/octet-stream")}
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if admin_token:
            headers["x-admin-token"] = admin_token

        if not headers:
            print(
                "❌ Missing authentication headers - provide credentials or ADMIN_UPLOAD_TOKEN"
            )
            return

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

    token = None

    if ADMIN_UPLOAD_TOKEN:
        print("🔑 Using ADMIN_UPLOAD_TOKEN for authentication")
    else:
        # Get credentials
        username = input("Username: ")
        password = getpass.getpass("Password: ")

        # Login
        token = login(username, password)

        if not token:
            print("\n❌ Upload cancelled - authentication required")
            raise SystemExit(1)

    # Upload database
    upload_database(token, ADMIN_UPLOAD_TOKEN)
