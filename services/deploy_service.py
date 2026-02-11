"""
===================================================================
  🎵 CHORUS — Deploy Service (Operación Éxodo)
===================================================================

FastAPI microservice that receives Python handler functions packaged
as ZIP archives, deploys them as managed worker processes, and auto-
registers them in the Chorus Registry.

This is the "Chorus Cloud" — a local FaaS (Function-as-a-Service)
that lets developers publish agents with `serverless=True` and walk
away. The agents run 24/7 without the developer's machine.

Architecture:
  SDK → uploads .zip → Deploy Service → spawns worker → registers in Registry
  
  When a job arrives at the worker's endpoint, the Deploy Service
  loads the handler from the .zip and executes it in-process.

Run: uvicorn services.deploy_service:app --port 8003
"""

from __future__ import annotations

import sys
import os
import uuid
import zipfile
import importlib.util
import io
import time
import threading
import shutil
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import uvicorn


# =============================================================================
# Configuration
# =============================================================================

REGISTRY_URL = os.getenv("CHORUS_REGISTRY_URL", "http://localhost:8001")
LEDGER_URL = os.getenv("CHORUS_LEDGER_URL", "http://localhost:8002")
DEPLOY_DIR = os.getenv("CHORUS_DEPLOY_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".chorus_cloud"
))
HOST = os.getenv("CHORUS_CLOUD_HOST", "0.0.0.0")
BASE_PORT = int(os.getenv("CHORUS_CLOUD_BASE_PORT", "9000"))


# =============================================================================
# App
# =============================================================================

app = FastAPI(
    title="🎵 Chorus Deploy Service — Chorus Cloud FaaS",
    description="Serverless function deployment for the Chorus AI marketplace",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# State — Deployed Functions
# =============================================================================

class DeployedAgent:
    """Represents a serverless agent running in the Chorus Cloud."""
    def __init__(
        self,
        deploy_id: str,
        agent_id: str,
        name: str,
        skill: str,
        cost: float,
        owner_id: str,
        handler: Callable,
        port: int,
        deploy_dir: str,
    ):
        self.deploy_id = deploy_id
        self.agent_id = agent_id
        self.name = name
        self.skill = skill
        self.cost = cost
        self.owner_id = owner_id
        self.handler = handler
        self.port = port
        self.deploy_dir = deploy_dir
        self.endpoint = f"http://localhost:{port}"
        self.created_at = time.time()
        self.jobs_completed = 0
        self.total_earned = 0.0
        self.status = "deploying"
        self.server = None
        self.thread = None

    def to_dict(self):
        return {
            "deploy_id": self.deploy_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "skill": self.skill,
            "cost": self.cost,
            "owner_id": self.owner_id,
            "endpoint": self.endpoint,
            "port": self.port,
            "status": self.status,
            "jobs_completed": self.jobs_completed,
            "total_earned": round(self.total_earned, 4),
            "uptime_seconds": int(time.time() - self.created_at),
        }


# Active deployments
_deployments: dict[str, DeployedAgent] = {}
_next_port = BASE_PORT


# =============================================================================
# Response Models
# =============================================================================

class DeployResponse(BaseModel):
    status: str
    deploy_id: str
    agent_id: str
    endpoint: str
    name: str
    skill: str
    message: str


# =============================================================================
# Core: Load handler from ZIP
# =============================================================================

def _load_handler_from_zip(zip_path: str, handler_name: str = "handler") -> Callable:
    """
    Extract a ZIP, find the handler module, and return the handler function.
    
    Expected ZIP structure:
        handler.py          — must contain a function called `handler(data) -> dict`
        requirements.txt    — (optional) dependencies
    """
    extract_dir = zip_path.replace(".zip", "")
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)
    
    # Look for handler.py
    handler_file = os.path.join(extract_dir, "handler.py")
    if not os.path.exists(handler_file):
        # Try looking in a subdirectory
        for root, dirs, files in os.walk(extract_dir):
            if "handler.py" in files:
                handler_file = os.path.join(root, "handler.py")
                break
    
    if not os.path.exists(handler_file):
        raise ValueError("No handler.py found in the uploaded package")
    
    # Load the module dynamically
    spec = importlib.util.spec_from_file_location("agent_handler", handler_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Get the handler function
    if not hasattr(module, handler_name):
        # Try 'main' as fallback
        if hasattr(module, "main"):
            handler_name = "main"
        else:
            raise ValueError(
                f"handler.py must contain a function called '{handler_name}' or 'main'"
            )
    
    return getattr(module, handler_name)


# =============================================================================
# Core: Create and start a worker server for a deployed agent
# =============================================================================

class _JobPayload(BaseModel):
    job_id: str = ""
    orchestrator_id: str = ""
    skill_name: str = ""
    input_data: dict = {}
    budget: float = 1.0
    currency: str = "chorus_credits_v1"


def _create_worker_app(agent: DeployedAgent) -> FastAPI:
    """Create a FastAPI app for a serverless agent worker."""
    
    worker_app = FastAPI(
        title=f"☁️ Chorus Cloud: {agent.name}",
        version="0.1.0",
    )
    
    worker_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @worker_app.post("/jobs")
    async def handle_job(payload: _JobPayload):
        start = time.perf_counter()
        
        # Skill mismatch check
        if payload.skill_name and payload.skill_name != agent.skill:
            return {
                "job_id": payload.job_id,
                "agent_id": agent.agent_id,
                "status": "FAILURE",
                "error_message": f"Skill mismatch: '{payload.skill_name}' != '{agent.skill}'",
                "error_code": "SKILL_MISMATCH",
                "execution_cost": 0,
                "execution_time_ms": 0,
            }
        
        # Budget check
        if payload.budget < agent.cost:
            return {
                "job_id": payload.job_id,
                "agent_id": agent.agent_id,
                "status": "FAILURE",
                "error_message": f"Budget {payload.budget:.2f} < cost {agent.cost:.2f}",
                "error_code": "BUDGET_INSUFFICIENT",
                "execution_cost": 0,
                "execution_time_ms": 0,
            }
        
        # Execute the handler
        try:
            output = agent.handler(payload.input_data)
            elapsed = int((time.perf_counter() - start) * 1000)
            agent.jobs_completed += 1
            agent.total_earned += agent.cost
            return {
                "job_id": payload.job_id,
                "agent_id": agent.agent_id,
                "status": "SUCCESS",
                "output_data": output,
                "execution_cost": agent.cost,
                "execution_time_ms": elapsed,
                "error_message": None,
                "deployment_mode": "serverless",
            }
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            return {
                "job_id": payload.job_id,
                "agent_id": agent.agent_id,
                "status": "FAILURE",
                "error_message": str(e),
                "error_code": "EXECUTION_ERROR",
                "execution_cost": 0,
                "execution_time_ms": elapsed,
            }
    
    @worker_app.get("/health")
    async def health():
        return {
            "service": "chorus-cloud-worker",
            "name": agent.name,
            "skill": agent.skill,
            "status": "healthy",
            "deployment_mode": "serverless",
            "jobs_completed": agent.jobs_completed,
            "uptime_seconds": int(time.time() - agent.created_at),
        }
    
    @worker_app.get("/info")
    async def info():
        return agent.to_dict()
    
    return worker_app


def _start_worker(agent: DeployedAgent):
    """Start a worker server in a background thread."""
    worker_app = _create_worker_app(agent)
    config = uvicorn.Config(
        worker_app,
        host=HOST,
        port=agent.port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    agent.server = server
    
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    agent.thread = thread
    
    # Wait for server to be ready
    time.sleep(1.5)
    agent.status = "online"


def _register_with_registry(agent: DeployedAgent) -> bool:
    """Register the deployed agent with the Chorus Registry."""
    reg_payload = {
        "agent_id": agent.agent_id,
        "agent_name": f"☁️ {agent.name}",
        "owner_id": agent.owner_id,
        "api_endpoint": agent.endpoint,
        "skills": [{
            "skill_name": agent.skill,
            "description": f"Serverless agent: {agent.skill}",
            "cost_per_call": agent.cost,
            "input_schema": {},
            "output_schema": {},
        }],
        "version": "0.1-serverless",
    }
    
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.post(f"{REGISTRY_URL}/register", json=reg_payload)
            return r.status_code == 201
    except Exception:
        return False


def _find_free_port() -> int:
    """Find a free TCP port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


# =============================================================================
# API Endpoints
# =============================================================================

@app.post("/deploy", response_model=DeployResponse)
async def deploy_agent(
    package: UploadFile = File(...),
    name: str = Form(...),
    skill: str = Form(...),
    cost: float = Form(...),
    owner_id: str = Form(...),
    handler_name: str = Form("handler"),
):
    """
    Deploy a serverless agent to the Chorus Cloud.
    
    Receives a ZIP containing handler.py, extracts it, loads the handler
    function, starts a managed worker server, and registers with the Registry.
    """
    global _next_port
    
    deploy_id = str(uuid.uuid4())[:12]
    agent_id = str(uuid.uuid4())
    
    # Create deployment directory
    deploy_dir = os.path.join(DEPLOY_DIR, deploy_id)
    os.makedirs(deploy_dir, exist_ok=True)
    
    # Save the uploaded package
    zip_path = os.path.join(deploy_dir, "package.zip")
    content = await package.read()
    with open(zip_path, "wb") as f:
        f.write(content)
    
    # Load the handler
    try:
        handler = _load_handler_from_zip(zip_path, handler_name)
    except Exception as e:
        shutil.rmtree(deploy_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Failed to load handler: {e}")
    
    # Assign port
    port = _find_free_port()
    
    # Create deployed agent
    agent = DeployedAgent(
        deploy_id=deploy_id,
        agent_id=agent_id,
        name=name,
        skill=skill,
        cost=cost,
        owner_id=owner_id,
        handler=handler,
        port=port,
        deploy_dir=deploy_dir,
    )
    
    # Start the worker
    try:
        _start_worker(agent)
    except Exception as e:
        shutil.rmtree(deploy_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Worker startup failed: {e}")
    
    # Register with Registry
    registered = _register_with_registry(agent)
    if not registered:
        agent.status = "online (unregistered)"
    
    # Create Ledger account for owner
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(f"{LEDGER_URL}/accounts", json={
                "owner_id": owner_id,
                "initial_balance": 0.0,
            })
    except Exception:
        pass
    
    _deployments[deploy_id] = agent
    
    reg_msg = "registered in network" if registered else "running (registry offline)"
    
    return DeployResponse(
        status="deployed",
        deploy_id=deploy_id,
        agent_id=agent_id,
        endpoint=agent.endpoint,
        name=name,
        skill=skill,
        message=f"☁️ Agent '{name}' deployed to Chorus Cloud at {agent.endpoint}, {reg_msg}",
    )


@app.post("/deploy/inline")
async def deploy_inline(
    name: str,
    skill: str,
    cost: float,
    owner_id: str,
    handler_code: str,
    handler_name: str = "handler",
):
    """
    Deploy a serverless agent from inline Python code (no ZIP needed).
    
    The handler_code should be valid Python that defines a function
    matching handler_name.
    """
    global _next_port
    
    deploy_id = str(uuid.uuid4())[:12]
    agent_id = str(uuid.uuid4())
    
    # Create deployment directory
    deploy_dir = os.path.join(DEPLOY_DIR, deploy_id)
    os.makedirs(deploy_dir, exist_ok=True)
    
    # Write the code to handler.py
    handler_file = os.path.join(deploy_dir, "handler.py")
    with open(handler_file, "w", encoding="utf-8") as f:
        f.write(handler_code)
    
    # Load it
    try:
        spec = importlib.util.spec_from_file_location("agent_handler", handler_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        handler = getattr(module, handler_name)
    except Exception as e:
        shutil.rmtree(deploy_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Failed to load handler: {e}")
    
    # Assign port
    port = _find_free_port()
    
    # Create deployed agent
    agent = DeployedAgent(
        deploy_id=deploy_id,
        agent_id=agent_id,
        name=name,
        skill=skill,
        cost=cost,
        owner_id=owner_id,
        handler=handler,
        port=port,
        deploy_dir=deploy_dir,
    )
    
    # Start worker and register
    _start_worker(agent)
    registered = _register_with_registry(agent)
    
    try:
        with httpx.Client(timeout=5.0) as client:
            client.post(f"{LEDGER_URL}/accounts", json={
                "owner_id": owner_id,
                "initial_balance": 0.0,
            })
    except Exception:
        pass
    
    _deployments[deploy_id] = agent
    
    return {
        "status": "deployed",
        "deploy_id": deploy_id,
        "agent_id": agent_id,
        "endpoint": agent.endpoint,
        "name": name,
        "skill": skill,
        "registered": registered,
        "message": f"☁️ Agent '{name}' live at {agent.endpoint}",
    }


@app.get("/deployments")
async def list_deployments():
    """List all deployed serverless agents."""
    return {
        "deployments": [a.to_dict() for a in _deployments.values()],
        "total": len(_deployments),
        "cloud_status": "operational",
    }


@app.get("/deployments/{deploy_id}")
async def get_deployment(deploy_id: str):
    """Get status of a specific deployment."""
    agent = _deployments.get(deploy_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Deployment '{deploy_id}' not found")
    return agent.to_dict()


@app.delete("/deployments/{deploy_id}")
async def undeploy(deploy_id: str):
    """Stop and remove a deployed agent."""
    agent = _deployments.pop(deploy_id, None)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Deployment '{deploy_id}' not found")
    
    # Shutdown the server
    if agent.server:
        agent.server.should_exit = True
    
    # Remove files
    shutil.rmtree(agent.deploy_dir, ignore_errors=True)
    
    # Unregister from Registry
    try:
        with httpx.Client(timeout=5.0) as client:
            client.delete(f"{REGISTRY_URL}/agents/{agent.agent_id}")
    except Exception:
        pass
    
    return {
        "status": "undeployed",
        "deploy_id": deploy_id,
        "name": agent.name,
        "jobs_completed": agent.jobs_completed,
        "total_earned": round(agent.total_earned, 4),
    }


@app.get("/health")
async def health():
    online = sum(1 for a in _deployments.values() if a.status == "online")
    return {
        "service": "chorus-cloud",
        "status": "operational",
        "deployments": len(_deployments),
        "agents_online": online,
        "cloud_mode": "local-faas",
    }
