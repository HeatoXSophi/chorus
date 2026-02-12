import sys
import os

# Add parent directory to path to import chorus_sdk
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chorus_sdk as chorus
from chorus_sdk import client
import httpx

def main():
    print("🚀 Updating Agent Description in Supabase...")
    
    SUPABASE_URL = "https://yjhwxelvgwaqszletlkk.supabase.co"
    SUPABASE_KEY = "sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu" 
    
    # Login
    print("🔑 Login required to update your agent.")
    email = input("Enter your email: ")
    password = input("Enter your password: ")
    
    try:
        chorus.connect(SUPABASE_URL, SUPABASE_KEY, email, password)
    except Exception as e:
        print(f"❌ Login Error: {e}")
        return

    # 1. Find the Agent ID
    print("🔍 Looking for 'WikiCloud' agent...")
    headers = client._get_headers()
    
    # Use direct query because SDK discovery might return limited fields
    url = f"{SUPABASE_URL}/rest/v1/agents?name=eq.WikiCloud%20☁️&select=id"
    
    try:
        r = httpx.get(url, headers=headers)
        data = r.json()
        
        if not data:
            # Try without emoji if failed
            url = f"{SUPABASE_URL}/rest/v1/agents?name=eq.WikiCloud&select=id"
            r = httpx.get(url, headers=headers)
            data = r.json()
            
        if not data:
            print("❌ Agent 'WikiCloud' not found. Did you register it?")
            return
            
        agent_id = data[0]['id']
        print(f"✅ Found Agent ID: {agent_id}")
        
    except Exception as e:
        print(f"❌ Error searching agent: {e}")
        return

    # 2. Update Description
    new_description = "Investigo cualquier tema en Wikipedia y te entrego un resumen completo. ¡Pruébame consultando sobre 'Inteligencia Artificial'!"
    
    update_url = f"{SUPABASE_URL}/rest/v1/agents?id=eq.{agent_id}"
    payload = {
        "description": new_description
    }
    
    try:
        r = httpx.patch(update_url, json=payload, headers=headers)
        if r.status_code in [200, 204]:
            print("✅ Description updated successfully!")
            print(f"   New Text: {new_description}")
        else:
            print(f"❌ Update failed: {r.text}")
    except Exception as e:
        print(f"❌ Error updating: {e}")

if __name__ == "__main__":
    main()
