
import chorus
import httpx

def main():
    print("🚀 Registering Cloud Agent in Supabase...")
    
    SUPABASE_URL = "https://yjhwxelvgwaqszletlkk.supabase.co"
    SUPABASE_KEY = "sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu" 
    
    # Login
    chorus.connect(SUPABASE_URL, SUPABASE_KEY, "pablo@chorus.dev", "demo123")
    
    # Register the Vercel URL directly
    # Note: We can't use 'publish' easily for external URLs in the current SDK without modification,
    # OR we just insert it via API manually.
    # Actually, let's use the SDK 'client._register_agent' internal method or just do a raw post.
    
    payload = {
        "owner_id": chorus.client._owner_id, 
        "name": "WikiCloud ☁️",
        "skill": "research",
        "description": "I run on Vercel Serverless (Production). No localhost needed.",
        "endpoint": "https://chorus-ruddy.vercel.app/api/wiki", # The REAL production URL
        "cost_per_call": 20.0,
        "status": "online",
        "reputation_score": 100.0,
        "is_serverless": True
    }
    
    url = f"{SUPABASE_URL}/rest/v1/agents"
    headers = chorus.client._get_headers()
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
