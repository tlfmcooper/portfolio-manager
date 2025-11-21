"""
Setup superuser on Railway using the admin endpoint.
Run this script locally after deploying the backend to Railway.
"""
import requests
import os
import sys

# Your Railway backend URL
BACKEND_URL = "https://protective-playfulness-production.up.railway.app"

# Admin token (you need to set this in Railway environment variables)
ADMIN_TOKEN = input("Enter your ADMIN_UPLOAD_TOKEN (set this in Railway env vars first): ").strip()

if not ADMIN_TOKEN:
    print("❌ Error: ADMIN_UPLOAD_TOKEN is required")
    print("\n📝 Steps:")
    print("1. Go to your Railway backend service")
    print("2. Click 'Variables' tab")
    print("3. Add: ADMIN_UPLOAD_TOKEN = <your-secret-token>")
    print("4. Deploy the changes")
    print("5. Run this script again")
    sys.exit(1)

print(f"\n🚀 Creating superuser on Railway...")
print(f"📍 Target: {BACKEND_URL}")
print("=" * 60)

try:
    response = requests.post(
        f"{BACKEND_URL}/admin/create-first-superuser",
        headers={"x-admin-token": ADMIN_TOKEN},
        timeout=30,
    )

    if response.status_code == 200:
        data = response.json()
        print("✅ Success!")
        print(f"✨ {data['message']}")
        print(f"\n👤 Username: {data['username']}")
        print(f"📧 Email: {data['email']}")
        print(f"🔑 Password: userpass")
        print(f"\n🎉 You can now login at: https://pm.alikone.dev")
        print(f"🔗 Or directly to backend: {BACKEND_URL}/docs")
    elif response.status_code == 401:
        print("❌ Authentication failed!")
        print("Make sure ADMIN_UPLOAD_TOKEN is set in Railway environment variables")
        print(response.text)
    elif response.status_code == 403:
        print("❌ Invalid admin token!")
        print("The ADMIN_UPLOAD_TOKEN you provided doesn't match the one in Railway")
        print(response.text)
    else:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("❌ Connection error!")
    print("Make sure your backend is deployed and running on Railway")
except Exception as e:
    print(f"❌ Error: {e}")
