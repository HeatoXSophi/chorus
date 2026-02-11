"""
Chorus SDK — Agent Publisher Module (Supabase Edition)

Makes it trivial for developers to publish their own AI agents on the Chorus network.
Just define a function and call publish().
"""

from __future__ import annotations

import uuid
import threading
import uvicorn
from typing import Any, Callable
from fastapi import FastAPI, Header, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chorus_sdk import client

# =============================================================================
# State
# =============================================================================

_published_agents: list[dict] = []

# =============================================================================
# Quick Publish
# =============================================================================

def publish(
    name: str,
    skill: str,
    cost: float,
    handler: Callable[[dict[str, Any]], dict[str, Any]],
    description: str = "",
    port: int = 0,
    serverless: bool = False, # Kept for compatibility but works differently
) -> dict:
    """
    Publish an AI agent on the Chorus network.
    
    Requires chorus.connect() to be called first.
    """
    
    # 1. Ensure connected
    if not client._connected:
         # Try to auto-connect if env vars present? 
         # Or just raise error.
         raise ConnectionError("SDK", "N/A", "Call chorus.connect() before publishing.")

    agent_id = str(uuid.uuid4())
    endpoint = ""
    
    if serverless:
        # TODO: Implement Vercel deployment logic
        print("⚠️ Serverless deployment not yet fully implemented for Vercel. Falling back to local.")
        # We fall back to local serving for now
        
    # 2. Start Local Server
    if port == 0:
        import socket
        with socket.socket() as s:
            s.bind(('', 0))
            port = s.getsockname()[1]
            
    host = "localhost" # or 0.0.0.0
    endpoint = f"http://{host}:{port}"
    
    # Start the server in a thread
    t = threading.Thread(
        target=serve,
        args=(name, handler, port, host),
        daemon=True
    )
    t.start()
    
    # 3. Register in Supabase
    # We need to insert into 'agents' table
    # Schema: id, owner_id, name, skill, description, endpoint, cost_per_call, ...
    
    # We need the authenticated user's ID.
    if not client._owner_id:
        print("⚠️ Warning: Publishing as anonymous? Registry might reject if RLS enforced.")
    
    import httpx
    payload = {
        "id": agent_id,
        "owner_id": client._owner_id, 
        "name": name,
        "skill": skill,
        "description": description,
        "endpoint": endpoint,
        "cost_per_call": cost,
        "status": "online",
        "reputation_score": 50.0 # Default
    }
    
    url = f"{client._supabase_url}/rest/v1/agents"
    headers = client._get_headers()
    headers["Prefer"] = "return=representation"
    
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        r.raise_for_status()
        print(f"✅ Agent '{name}' registered on Chorus Network (Supabase).")
    except Exception as e:
        print(f"❌ Failed to register agent: {e}")
        # Note: If server is running, we might still return, but it won't be discoverable.
        
    info = {
        "agent_id": agent_id,
        "endpoint": endpoint,
        "port": port,
        "mode": "local_hybrid",
    }
    _published_agents.append(info)
    return info


def serve(
    name: str,
    handler: Callable[[dict], dict],
    port: int,
    host: str = "0.0.0.0",
):
    """
    Starts a FastAPI server for the agent.
    """
    app = FastAPI(title=name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class JobRequest(BaseModel):
        job_id: str
        skill_name: str
        input_data: dict[str, Any]
        budget: float
        orchestrator_id: str | None = None

    @app.get("/")
    def root():
        return {"agent": name, "status": "online"}

    @app.post("/jobs")
    def run_job(job: JobRequest, authorization: str | None = Header(default=None)):
        # Verify Auth if needed? 
        # For now, public.
        
        try:
            # Run the handler
            output = handler(job.input_data)
            return {
                "job_id": job.job_id,
                "status": "SUCCESS",
                "output_data": output,
                "execution_cost": 0, # Agent logic determines cost, passed in publish? 
                # We should return the cost so the caller knows how much to pay.
                # Ideally this is retrieved from Registry, but good to confirm.
            }
        except Exception as e:
            return {
                "job_id": job.job_id,
                "status": "FAILURE",
                "error_message": str(e)
            }

    uvicorn.run(app, host=host, port=port, log_level="error")
