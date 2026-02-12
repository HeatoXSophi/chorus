"""
Register ALL Chorus Cloud Agents in Supabase.
Run this once to add TranslatorBot, WeatherBot, and NewsScanner.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chorus_sdk as chorus
from chorus_sdk import client
import httpx

SUPABASE_URL = "https://yjhwxelvgwaqszletlkk.supabase.co"
SUPABASE_KEY = "sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu"
BASE_ENDPOINT = "https://chorus-ruddy.vercel.app"

AGENTS = [
    {
        "name": "TranslatorBot 🌐",
        "skill": "translate",
        "description": "Traduzco textos automáticamente entre español e inglés. ¡Escribe cualquier frase y la traduzco al instante!",
        "endpoint": f"{BASE_ENDPOINT}/api/translate",
        "cost_per_call": 10.0,
        "reputation_score": 90.0,
        "is_serverless": True
    },
    {
        "name": "WeatherBot ⛅",
        "skill": "weather",
        "description": "Te digo el clima actual de cualquier ciudad del mundo. ¡Pregúntame por 'Madrid', 'Tokyo' o tu ciudad!",
        "endpoint": f"{BASE_ENDPOINT}/api/weather",
        "cost_per_call": 10.0,
        "reputation_score": 88.0,
        "is_serverless": True
    },
    {
        "name": "NewsScanner 📰",
        "skill": "news",
        "description": "Busco las últimas noticias sobre cualquier tema. ¡Escribe 'Bitcoin', 'deportes' o lo que quieras saber!",
        "endpoint": f"{BASE_ENDPOINT}/api/news",
        "cost_per_call": 10.0,
        "reputation_score": 85.0,
        "is_serverless": True
    }
]

def main():
    print("🚀 Registering ALL Cloud Agents in Supabase...")
    
    email = input("Enter your email: ")
    password = input("Enter your password: ")
    
    try:
        chorus.connect(SUPABASE_URL, SUPABASE_KEY, email, password)
    except Exception as e:
        print(f"⚠️ Login failed: {e}")
        print("Attempting signup...")
        try:
            auth_url = f"{SUPABASE_URL}/auth/v1/signup"
            headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
            r = httpx.post(auth_url, json={"email": email, "password": password}, headers=headers)
            if r.status_code in [200, 201]:
                print("✅ Account created! Check your email for confirmation.")
                chorus.connect(SUPABASE_URL, SUPABASE_KEY, email, password)
            else:
                print(f"❌ Signup failed: {r.text}")
                return
        except Exception as e2:
            print(f"❌ Error: {e2}")
            return

    headers = client._get_headers()
    headers["Prefer"] = "return=representation"
    
    owner_id = None
    try:
        auth_headers = {"apikey": SUPABASE_KEY, "Authorization": headers.get("Authorization", "")}
        r = httpx.get(f"{SUPABASE_URL}/auth/v1/user", headers=auth_headers)
        if r.status_code == 200:
            owner_id = r.json().get("id")
    except:
        pass
    
    if not owner_id:
        owner_id = email
    
    print(f"👤 Owner ID: {owner_id}")
    
    for agent_def in AGENTS:
        print(f"\n🔧 Registering: {agent_def['name']}...")
        
        # Check if agent already exists
        check_url = f"{SUPABASE_URL}/rest/v1/agents?name=eq.{urllib.parse.quote(agent_def['name'])}&owner_id=eq.{owner_id}&select=id"
        r = httpx.get(check_url, headers=headers)
        if r.status_code == 200 and r.json():
            print(f"   ⏭️ Already exists, skipping.")
            continue
        
        payload = {
            "name": agent_def["name"],
            "owner_id": owner_id,
            "skill": agent_def["skill"],
            "description": agent_def["description"],
            "endpoint": agent_def["endpoint"],
            "cost_per_call": agent_def["cost_per_call"],
            "reputation_score": agent_def["reputation_score"],
            "is_serverless": agent_def["is_serverless"]
        }
        
        url = f"{SUPABASE_URL}/rest/v1/agents"
        r = httpx.post(url, json=payload, headers=headers)
        
        if r.status_code in [200, 201]:
            print(f"   ✅ Registered successfully!")
        else:
            print(f"   ❌ Error: {r.text}")

    print("\n🎉 All agents registered! Visit the Marketplace to see them.")

if __name__ == "__main__":
    import urllib.parse
    main()
