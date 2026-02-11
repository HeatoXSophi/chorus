"""
===================================================================
  🎵 CHORUS — Phase 1: Network Demo Client
===================================================================

Demonstrates the Chorus ecosystem running as real HTTP services.
This client connects to the Registry and Ledger services, discovers
agents, sends job requests over HTTP, and processes payments.

PREREQUISITES (run these in separate terminals):
  Terminal 1: uvicorn services.registry_service:app --port 8001
  Terminal 2: uvicorn services.ledger_service:app --port 8002
  Terminal 3: CHORUS_AGENT_SKILL=analyze_text CHORUS_AGENT_NAME=TextAnalyzer CHORUS_AGENT_PORT=8010 uvicorn services.agent_service:app --port 8010
  Terminal 4: CHORUS_AGENT_SKILL=calculate CHORUS_AGENT_NAME=Calculator CHORUS_AGENT_OWNER=math_corp CHORUS_AGENT_PORT=8011 uvicorn services.agent_service:app --port 8011

Then run this demo:
  python demo/phase1_network.py
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from chorus.models import (
    AgentRegistration,
    JobRequest,
    SkillDefinition,
    _uuid,
)


REGISTRY_URL = "http://localhost:8001"
LEDGER_URL = "http://localhost:8002"


async def main():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  🎵 PROYECTO CHORUS — Phase 1 Network Demo          ║")
    print("║     Real HTTP Communication Between AI Services     ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    async with httpx.AsyncClient(timeout=10.0) as client:

        # -----------------------------------------------------------------
        # 1. Health check all services
        # -----------------------------------------------------------------
        print("🔍 Checking service health...\n")

        services = {
            "Registry": f"{REGISTRY_URL}/health",
            "Ledger": f"{LEDGER_URL}/health",
        }

        for name, url in services.items():
            try:
                r = await client.get(url)
                data = r.json()
                print(f"   ✅ {name}: {data.get('status', 'unknown')}")
            except Exception as e:
                print(f"   ❌ {name}: OFFLINE ({e})")
                print(f"\n⚠️  Please start all services first. See docstring for instructions.")
                return

        # -----------------------------------------------------------------
        # 2. Create accounts on the Ledger
        # -----------------------------------------------------------------
        print("\n💰 Creating accounts on the Ledger...\n")

        accounts = [
            {"owner_id": "demo_user", "initial_balance": 10.0},
            {"owner_id": "demo_owner", "initial_balance": 0.0},
            {"owner_id": "math_corp", "initial_balance": 0.0},
        ]

        for acc in accounts:
            r = await client.post(f"{LEDGER_URL}/accounts", json=acc)
            data = r.json()
            print(f"   📦 Account '{data['owner_id']}': {data['balance']:.2f} credits")

        # -----------------------------------------------------------------
        # 3. Discover available agents
        # -----------------------------------------------------------------
        print("\n🔍 Discovering agents on the network...\n")

        r = await client.get(f"{REGISTRY_URL}/skills")
        skills_data = r.json()
        print(f"   Available skills: {skills_data.get('skills', [])}")
        print(f"   Total agents: {skills_data.get('total_agents', 0)}")

        # Try discovering text analyzers
        r = await client.get(f"{REGISTRY_URL}/discover", params={"skill": "analyze_text"})
        discover_data = r.json()

        if discover_data["total"] == 0:
            print("\n   ⚠️ No text analyzer agents found.")
            print("   Start an agent with: CHORUS_AGENT_SKILL=analyze_text uvicorn services.agent_service:app --port 8010")

            # Show what agents ARE available
            for skill in skills_data.get("skills", []):
                r2 = await client.get(f"{REGISTRY_URL}/discover", params={"skill": skill})
                d2 = r2.json()
                for a in d2.get("agents", []):
                    print(f"   Found: '{a['agent_name']}' with skill '{skill}' at {a['api_endpoint']}")
        else:
            for agent in discover_data["agents"]:
                print(f"   🤖 '{agent['agent_name']}' — rep: {agent['reputation_score']:.1f} — "
                      f"endpoint: {agent['api_endpoint']}")

        # -----------------------------------------------------------------
        # 4. Send a job to an agent
        # -----------------------------------------------------------------
        print("\n📋 Sending job requests...\n")

        # Find any available agent
        all_skills = skills_data.get("skills", [])
        if not all_skills:
            print("   ⚠️ No agents registered. Start agent services first.")
            return

        for skill in all_skills:
            r = await client.get(f"{REGISTRY_URL}/discover", params={"skill": skill})
            agents = r.json().get("agents", [])

            if not agents:
                continue

            agent = agents[0]
            print(f"   📩 Sending job to '{agent['agent_name']}' (skill: {skill})...")

            # Build job request based on skill
            if skill == "analyze_text":
                input_data = {"text": "Los ingresos netos fueron 42000 dólares en Q3"}
            elif skill == "calculate":
                input_data = {"primary_number": 42000, "operation": "projection", "growth_rate": 0.15, "periods": 4}
            else:
                input_data = {"message": "Hello from Chorus Network!"}

            job = JobRequest(
                orchestrator_id="demo_orchestrator",
                skill_name=skill,
                input_data=input_data,
                budget=1.0,
            )

            try:
                r = await client.post(
                    f"{agent['api_endpoint']}/jobs",
                    json=job.model_dump(),
                )
                result = r.json()

                if result.get("status") == "SUCCESS":
                    print(f"   ✅ Success! Output: {result.get('output_data', {})}")
                    print(f"      Cost: {result.get('execution_cost', 0):.2f} | "
                          f"Time: {result.get('execution_time_ms', 0)}ms")

                    # Process payment via Ledger
                    transfer = {
                        "from_owner": "demo_user",
                        "to_owner": agent.get("owner_id", "demo_owner"),
                        "amount": result.get("execution_cost", 0.05),
                        "job_id": result.get("job_id", _uuid()),
                    }
                    tr = await client.post(f"{LEDGER_URL}/transfer", json=transfer)
                    tr_data = tr.json()
                    if tr.status_code == 200:
                        print(f"   💰 Payment settled! Sender balance: {tr_data.get('sender_balance', 0):.2f}")
                    else:
                        print(f"   ⚠️ Payment failed: {tr_data}")

                    # Update reputation
                    await client.post(
                        f"{REGISTRY_URL}/reputation/{agent['agent_id']}/success",
                        params={"job_id": result.get("job_id", ""), "contractor_reputation": 50.0},
                    )
                    print(f"   ⭐ Reputation updated for '{agent['agent_name']}'")

                else:
                    print(f"   ❌ Failed: {result.get('error_message', 'Unknown error')}")

            except httpx.ConnectError:
                print(f"   ❌ Could not connect to agent at {agent['api_endpoint']}")

        # -----------------------------------------------------------------
        # 5. Final economy report
        # -----------------------------------------------------------------
        print(f"\n{'='*60}")
        print("💰 NETWORK ECONOMY REPORT")
        print(f"{'='*60}\n")

        r = await client.get(f"{LEDGER_URL}/economy")
        economy = r.json()

        for owner, balance in economy.get("all_balances", {}).items():
            print(f"   {owner:.<35s} {balance:>8.2f} credits")

        print(f"\n   Total transactions: {economy.get('total_transactions', 0)}")
        print(f"   Total volume: {economy.get('total_volume', 0):.2f} credits")

        # -----------------------------------------------------------------
        # 6. Audit log
        # -----------------------------------------------------------------
        r = await client.get(f"{LEDGER_URL}/audit")
        audit = r.json()

        if audit.get("transactions"):
            print(f"\n📜 Audit Log:")
            for tx in audit["transactions"]:
                print(f"   {tx['from_owner']} → {tx['to_owner']}: "
                      f"{tx['amount']:.2f} credits (job: {tx['job_id'][:8]}...)")

    print(f"\n✨ Phase 1 Network Demo Complete!")
    print(f"   Real HTTP-based AI agent collaboration demonstrated.\n")


if __name__ == "__main__":
    asyncio.run(main())
