"""
===================================================================
  🎵 CHORUS — Registry Service (Phase 1 Network Alpha)
===================================================================

FastAPI microservice for agent registration and discovery.
Agents register their skills here; orchestrators query to find specialists.

Run: uvicorn services.registry_service:app --port 8001
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from chorus.models import AgentRegistration, AgentInfo, SkillDefinition, _now
from chorus.reputation import ReputationEngine


# =============================================================================
# App & State
# =============================================================================

app = FastAPI(
    title="🎵 Chorus Registry Service",
    description="Agent registration and skill-based discovery for the Chorus network",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state (would be PostgreSQL in production)
_agents: dict[str, AgentInfo] = {}
_skill_index: dict[str, list[str]] = {}
_reputation = ReputationEngine()


# =============================================================================
# Response Models
# =============================================================================

class RegisterResponse(BaseModel):
    status: str
    agent_id: str
    reputation_score: float


class DiscoverResponse(BaseModel):
    agents: list[AgentInfo]
    total: int


class HeartbeatRequest(BaseModel):
    agent_id: str


class HeartbeatResponse(BaseModel):
    status: str
    agent_id: str
    timestamp: str


# =============================================================================
# Endpoints
# =============================================================================

@app.post("/register", response_model=RegisterResponse, status_code=201)
async def register_agent(registration: AgentRegistration):
    """Register a new agent on the Chorus network."""
    initial_rep = _reputation.initialize_agent(registration.agent_id)

    agent_info = AgentInfo(
        agent_id=registration.agent_id,
        agent_name=registration.agent_name,
        owner_id=registration.owner_id,
        api_endpoint=registration.api_endpoint,
        skills=registration.skills,
        reputation_score=initial_rep,
    )

    _agents[registration.agent_id] = agent_info

    for skill in registration.skills:
        if skill.skill_name not in _skill_index:
            _skill_index[skill.skill_name] = []
        _skill_index[skill.skill_name].append(registration.agent_id)

    return RegisterResponse(
        status="registered",
        agent_id=registration.agent_id,
        reputation_score=initial_rep,
    )


@app.get("/discover", response_model=DiscoverResponse)
async def discover_agents(
    skill: str = Query(..., description="Skill name to search for"),
    min_reputation: float = Query(0.0, ge=0.0, le=100.0),
    max_cost: float | None = Query(None, ge=0.0),
):
    """Find agents by skill, filtered and sorted by reputation."""
    agent_ids = _skill_index.get(skill, [])
    results = []

    for agent_id in agent_ids:
        agent = _agents.get(agent_id)
        if not agent or agent.status != "online":
            continue

        agent.reputation_score = _reputation.get_score(agent_id)

        if agent.reputation_score < min_reputation:
            continue

        if max_cost is not None:
            cost = next(
                (s.cost_per_call for s in agent.skills if s.skill_name == skill),
                float("inf"),
            )
            if cost > max_cost:
                continue

        results.append(agent)

    results.sort(key=lambda a: a.reputation_score, reverse=True)

    return DiscoverResponse(agents=results, total=len(results))


@app.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(request: HeartbeatRequest):
    """Update agent's heartbeat to maintain 'online' status."""
    agent = _agents.get(request.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.last_heartbeat = _now()
    agent.status = "online"

    return HeartbeatResponse(
        status="ok",
        agent_id=request.agent_id,
        timestamp=agent.last_heartbeat,
    )


@app.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """Remove an agent from the registry."""
    agent = _agents.pop(agent_id, None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    for skill in agent.skills:
        ids = _skill_index.get(skill.skill_name, [])
        if agent_id in ids:
            ids.remove(agent_id)

    return {"status": "unregistered", "agent_id": agent_id}


@app.get("/agents/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str):
    """Get details for a specific agent."""
    agent = _agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    agent.reputation_score = _reputation.get_score(agent_id)
    return agent


@app.get("/skills")
async def list_skills():
    """List all skills available on the network."""
    return {
        "skills": list(_skill_index.keys()),
        "total_agents": len(_agents),
    }


@app.get("/reputation/{agent_id}")
async def get_reputation(agent_id: str):
    """Get reputation score and stats for an agent."""
    if agent_id not in _agents:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent_id": agent_id,
        "score": _reputation.get_score(agent_id),
        "stats": _reputation.get_stats(agent_id),
    }


@app.post("/reputation/{agent_id}/success")
async def record_success(agent_id: str, job_id: str, contractor_reputation: float = 50.0):
    """Record a successful job completion for reputation update."""
    update = _reputation.record_success(agent_id, job_id, contractor_reputation)
    return update.model_dump()


@app.post("/reputation/{agent_id}/failure")
async def record_failure(agent_id: str, job_id: str, contractor_reputation: float = 50.0):
    """Record a failed job for reputation update."""
    update = _reputation.record_failure(agent_id, job_id, contractor_reputation)
    return update.model_dump()


@app.get("/health")
async def health():
    return {
        "service": "chorus-registry",
        "status": "healthy",
        "agents_online": sum(1 for a in _agents.values() if a.status == "online"),
        "total_skills": len(_skill_index),
    }
