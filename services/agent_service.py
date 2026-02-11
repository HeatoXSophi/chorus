"""
===================================================================
  🎵 CHORUS — Agent Container Service (Phase 1 Network Alpha)
===================================================================

Generic FastAPI service that wraps an AI function into a network-accessible
Chorus agent. Configurable via environment variables or constructor params.

Run: uvicorn services.agent_service:app --port 8010
     (set AGENT_SKILL, AGENT_NAME, AGENT_COST, etc.)
"""

from __future__ import annotations

import sys
import os
import httpx
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from typing import Any, Callable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from chorus.models import (
    AgentRegistration,
    JobRequest,
    JobResult,
    JobStatus,
    SkillDefinition,
    ErrorCode,
    _uuid,
    _now,
)
from chorus.agent import AgentContainer


# =============================================================================
# Configuration
# =============================================================================

REGISTRY_URL = os.getenv("CHORUS_REGISTRY_URL", "http://localhost:8001")
LEDGER_URL = os.getenv("CHORUS_LEDGER_URL", "http://localhost:8002")
AGENT_NAME = os.getenv("CHORUS_AGENT_NAME", "Demo-Agent")
AGENT_OWNER = os.getenv("CHORUS_AGENT_OWNER", "demo_owner")
AGENT_SKILL = os.getenv("CHORUS_AGENT_SKILL", "echo")
AGENT_COST = float(os.getenv("CHORUS_AGENT_COST", "0.05"))
AGENT_PORT = int(os.getenv("CHORUS_AGENT_PORT", "8010"))


# =============================================================================
# Built-in Skill Functions (for demo purposes)
# =============================================================================

def skill_echo(input_data: dict) -> dict:
    """Default: echoes input."""
    return {"echo": input_data}


def skill_text_analyzer(input_data: dict) -> dict:
    """Extracts numbers from text."""
    text = input_data.get("text", "")
    numbers = []
    for word in text.replace(",", "").split():
        cleaned = word.strip("$€£.;:")
        if cleaned.isdigit():
            numbers.append(int(cleaned))
    return {
        "primary_number": numbers[0] if numbers else 0,
        "all_numbers": numbers,
        "source_text": text[:100],
    }


def skill_calculator(input_data: dict) -> dict:
    """Performs basic calculations."""
    number = input_data.get("primary_number", input_data.get("number", 0))
    operation = input_data.get("operation", "double")
    if operation == "double":
        return {"result": number * 2}
    elif operation == "square":
        return {"result": number ** 2}
    elif operation == "projection":
        rate = input_data.get("growth_rate", 0.15)
        periods = input_data.get("periods", 4)
        projected = number * (1 + rate) ** periods
        return {"original": number, "projected": round(projected, 2), "rate": rate}
    return {"result": number}


# Map of available skills
SKILL_REGISTRY: dict[str, Callable] = {
    "echo": skill_echo,
    "analyze_text": skill_text_analyzer,
    "calculate": skill_calculator,
}


# =============================================================================
# Agent Instance
# =============================================================================

_skill_func = SKILL_REGISTRY.get(AGENT_SKILL, skill_echo)

_agent = AgentContainer(
    name=AGENT_NAME,
    owner_id=AGENT_OWNER,
    skill_name=AGENT_SKILL,
    skill_description=f"Skill: {AGENT_SKILL}",
    cost=AGENT_COST,
    logic=_skill_func,
    api_endpoint=f"http://localhost:{AGENT_PORT}",
)


# =============================================================================
# App with Lifespan (auto-registration)
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """On startup, register with the Registry service."""
    print(f"\n🎵 Chorus Agent '{AGENT_NAME}' starting...")
    print(f"   Skill: {AGENT_SKILL} | Cost: {AGENT_COST} | Owner: {AGENT_OWNER}")

    try:
        async with httpx.AsyncClient() as client:
            reg = _agent.get_registration()
            reg.api_endpoint = f"http://localhost:{AGENT_PORT}"
            response = await client.post(
                f"{REGISTRY_URL}/register",
                json=reg.model_dump(),
                timeout=5.0,
            )
            if response.status_code == 201:
                print(f"   ✅ Registered with Registry at {REGISTRY_URL}")
            else:
                print(f"   ⚠️ Registration failed: {response.text}")
    except Exception as e:
        print(f"   ⚠️ Could not reach Registry: {e}")
        print(f"   Running in standalone mode.")

    yield

    print(f"\n🎵 Agent '{AGENT_NAME}' shutting down.")


app = FastAPI(
    title=f"🎵 Chorus Agent: {AGENT_NAME}",
    description=f"Agent container for skill '{AGENT_SKILL}'",
    version="0.1.0",
    lifespan=lifespan,
)


# =============================================================================
# Endpoints
# =============================================================================

@app.post("/jobs", response_model=dict)
async def handle_job(job_request: JobRequest):
    """Receive and execute a job request."""
    print(f"\n📩 Job received: {job_request.job_id[:8]}... (skill: {job_request.skill_name})")

    result = _agent.handle_job(job_request)

    status_icon = "✅" if result.status == JobStatus.SUCCESS else "❌"
    print(f"   {status_icon} Result: {result.status.value} | Cost: {result.execution_cost}")

    return result.model_dump()


@app.get("/info")
async def agent_info():
    """Get agent information and stats."""
    return {
        "agent_id": _agent.agent_id,
        "name": _agent.name,
        "owner_id": _agent.owner_id,
        "skill": _agent.skill.model_dump(),
        "stats": _agent.get_stats(),
    }


@app.get("/health")
async def health():
    return {
        "service": "chorus-agent",
        "agent_id": _agent.agent_id,
        "name": _agent.name,
        "skill": _agent.skill.skill_name,
        "status": "healthy",
        "jobs_completed": _agent._jobs_completed,
    }
