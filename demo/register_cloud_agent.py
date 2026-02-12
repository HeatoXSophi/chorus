import sys
import os

# Add parent directory to path so we can import chorus
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import chorus
import httpx

def main():
    print("🚀 Registering Cloud Agent in Supabase...")
    
    SUPABASE_URL = "https://yjhwxelvgwaqszletlkk.supabase.co"
    SUPABASE_KEY = "sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu" 
    
    print("🔑 Login required to register your agent.")
    email = input("Enter your email: ")
    password = input("Enter your password: ")
    
    try:
        chorus.connect(SUPABASE_URL, SUPABASE_KEY, email, password)
    except Exception:
        print("⚠️ Login failed. Attempting to CREATE NEW ACCOUNT...")
        try:
            # Manual Signup Request
            auth_url = f"{SUPABASE_URL}/auth/v1/signup"
            headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
            r = httpx.post(auth_url, json={"email": email, "password": password}, headers=headers)
            if r.status_code in [200, 201]:
                print("✅ Account created! Logging in...")
                chorus.connect(SUPABASE_URL, SUPABASE_KEY, email, password)
            else:
                print(f"❌ Signup failed: {r.text}")
                return
        except Exception as e:
            print(f"❌ Error: {e}")
            return
    

    # Register the Vercel URL directly
    # Note: We can't use 'publish' easily for external URLs in the current SDK without modification,
    # OR we just insert it via API manually.
    # Actually, let's use the SDK 'client._register_agent' internal method or just do a raw post.
    from chorus_sdk import client

    payload = {
        "owner_id": client._owner_id, 
        "name": "WikiCloud ☁️",
        "skill": "research",
        "description": "I run on Vercel Serverless (Production). No localhost needed.",
        "endpoint": "https://chorus-ruddy.vercel.app/api/wiki", # The REAL production URL
        "cost_per_call": 20.0,
        "reputation_score": 100.0,
        "is_serverless": True
    }
    
    url = f"{SUPABASE_URL}/rest/v1/agents"
    headers = client._get_headers()
    headers["Prefer"] = "return=representation"
    
    try:
        r = httpx.post(url, json=payload, headers=headers)
        if r.status_code == 201:
            print(f"✅ Agent '{payload['name']}' registered successfully!")
            print(f"   URL: {payload['endpoint']}")
        else:
            print(f"❌ Failed: {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
