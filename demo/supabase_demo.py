
import os
import time
import chorus
from chorus_sdk import client

# ── Configuration ──────────────────────────────────────────

SUPABASE_URL = "https://yjhwxelvgwaqszletlkk.supabase.co"
# Using the key provided by user (publishable/anon)
SUPABASE_KEY = "sb_publishable_b-PO7Mk5IusgL9ymbAaShw_p5ByupTu" # Correct key provided by user

# ── Agent Logic ────────────────────────────────────────────

def echo_handler(data):
    return {"message": f"Echo: {data.get('text', '')}"}

def calc_handler(data):
    a = data.get("a", 0)
    b = data.get("b", 0)
    op = data.get("op", "add")
    if op == "add": res = a + b
    elif op == "sub": res = a - b
    elif op == "mul": res = a * b
    else: res = 0
    return {"result": res}

def main():
    print("🚀 Connecting to Chorus Network (Supabase)...")
    
    # 1. Credentials
    print("\n--- Login ---")
    email = input("Enter your email (used in Portal): ")
    password = input("Enter your password: ")
    
    # 2. Connect
    try:
        status = chorus.connect(
            supabase_url=SUPABASE_URL,
            supabase_key=SUPABASE_KEY,
            email=email,
            password=password
        )
        print(f"✅ Connected! Agents online: {status.agents_online}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    print("\n📦 Publishing Agents...")
    
    agent1 = chorus.publish(
        name="EchoBot 3000",
        skill="echo",
        cost=0.1,
        handler=echo_handler,
        description="I repeat everything you say.",
        serverless=False # Local Hybrid
    )
    
    agent2 = chorus.publish(
        name="SuperCalc",
        skill="calculator",
        cost=0.5,
        handler=calc_handler,
        description="Math is easy.",
        serverless=False
    )
    
    print(f"\n✨ Agents are live on the network!")
    print(f"   - EchoBot: {agent1['endpoint']}")
    print(f"   - SuperCalc: {agent2['endpoint']}")
    
    # Discover via Supabase
    print("\n🔍 Discovering agents via Supabase API...")
    agents = chorus.discover("calculator")
    if agents:
        print(f"   Found {len(agents)} calculators. Hiring the best one...")
        target = agents[0]
        
        # Hire
        print(f"   Hiring {target.name} for 2 + 5...")
        result = chorus.hire(target, {"a": 2, "b": 5, "op": "add"})
        print(f"   Result: {result.output}")
        print(f"   Cost: Ƈ {result.cost}")
    else:
        print("   No calculators found (maybe replication lag or filter issue).")

    print("\n✅ Demo Complete. Keep this script running to serve requests.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agents...")

if __name__ == "__main__":
    main()
