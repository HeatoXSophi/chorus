"""
Chorus SDK — Client Module (Supabase Edition)

The main interface for developers to interact with the Chorus network via Supabase.
Provides simple functions: connect(), discover(), hire(), hire_best().
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from pydantic import BaseModel

from chorus_sdk.errors import (
    AgentNotFoundError,
    BudgetTooLowError,
    ConnectionError,
    InsufficientCreditsError,
    JobFailedError,
    SkillNotFoundError,
)
from chorus_sdk.models import AgentProfile, HireResult, NetworkStatus, EconomyStats


# =============================================================================
# Global Connection State
# =============================================================================

_supabase_url: str = ""
_supabase_key: str = ""
_access_token: str = ""
_owner_id: str = ""  # UUID
_connected: bool = False
_timeout: float = 10.0


# =============================================================================
# Connection
# =============================================================================

def connect(
    supabase_url: str,
    supabase_key: str,
    email: str = None,
    password: str = None,
    timeout: float = 10.0,
) -> NetworkStatus:
    """
    Connect to the Chorus network (Supabase).
    
    Args:
        supabase_url: Your Supabase Project URL
        supabase_key: Your Supabase Anon Key
        email: (Optional) Your account email
        password: (Optional) Your account password
        timeout: HTTP timeout in seconds
    """
    global _supabase_url, _supabase_key, _access_token, _owner_id, _connected, _timeout

    _supabase_url = supabase_url.rstrip("/")
    _supabase_key = supabase_key
    _timeout = timeout

    # Authenticate if credentials provided
    if email and password:
        auth_url = f"{_supabase_url}/auth/v1/token?grant_type=password"
        headers = {"apikey": _supabase_key, "Content-Type": "application/json"}
        try:
            r = httpx.post(auth_url, json={"email": email, "password": password}, headers=headers, timeout=_timeout)
            r.raise_for_status()
            data = r.json()
            _access_token = data["access_token"]
            _owner_id = data["user"]["id"]
        except Exception as e:
            raise ConnectionError("Auth", auth_url, f"Failed to login: {str(e)}")
    else:
        # Anonymous / Public access only
        pass

    _connected = True

    # Check network health (count agents)
    headers = _get_headers()
    try:
        r = httpx.get(f"{_supabase_url}/rest/v1/agents?select=count", headers=headers, timeout=_timeout)
        # Content-Range: 0-25/50 -> count is total
        # Or Just SELECT count(*)... PostgREST interaction
        agents_count = 0 
        # Simple query to check connectivity
        r = httpx.head(f"{_supabase_url}/rest/v1/agents", headers=headers, timeout=_timeout)
        if r.is_error:
             raise Exception(f"HTTP {r.status_code}")
             
        # Try to parse content-range for count if available, or just assume online
        cr = r.headers.get("Content-Range")
        if cr:
             agents_count = int(cr.split("/")[-1])
        
    except Exception as e:
        raise ConnectionError("Supabase", _supabase_url, str(e))

    return NetworkStatus(
        registry_online=True,
        ledger_online=True,
        agents_online=agents_count,
        total_skills=0,
        available_skills=[],
    )


def _ensure_connected():
    if not _connected:
        raise ConnectionError("SDK", "N/A", "Call chorus.connect() first.")

def _get_headers() -> dict:
    headers = {
        "apikey": _supabase_key,
        "Content-Type": "application/json",
        "Prefer": "return=representation", # return json
    }
    if _access_token:
        headers["Authorization"] = f"Bearer {_access_token}"
    return headers


# =============================================================================
# Discovery
# =============================================================================

def discover(
    skill: str | None = None,
    min_reputation: float = 0.0,
) -> list[AgentProfile]:
    _ensure_connected()

    url = f"{_supabase_url}/rest/v1/agents?select=*"
    params = {}
    
    if skill:
        url += f"&skill=eq.{skill}"
    
    if min_reputation > 0:
        url += f"&reputation_score=gte.{min_reputation}"
        
    # Sort by reputation desc
    url += "&order=reputation_score.desc"

    with httpx.Client(timeout=_timeout) as client:
        try:
            r = client.get(url, headers=_get_headers())
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            raise ConnectionError("Registry", url, str(e))

    agents = []
    for a in data:
        agents.append(AgentProfile(
            agent_id=str(a["id"]),
            name=a["name"],
            owner_id=str(a["owner_id"]),
            skill=a["skill"],
            cost=float(a["cost_per_call"]),
            reputation=float(a["reputation_score"]),
            endpoint=a["endpoint"],
            status="online",
        ))

    return agents


def discover_all() -> list[AgentProfile]:
    return discover(None)


# =============================================================================
# Hiring
# =============================================================================

def hire(
    agent: AgentProfile,
    input_data: dict[str, Any],
    budget: float | None = None,
    auto_pay: bool = True,
) -> HireResult:
    _ensure_connected()

    if budget is None:
        budget = agent.cost * 2

    if budget < agent.cost:
        raise BudgetTooLowError(budget, agent.cost)

    # 1. Check Balance (if authenticated)
    if _owner_id:
        balance = get_balance()
        if balance < budget:
            raise InsufficientCreditsError(balance, budget)

    # 2. Call Agent
    # Agent endpoint expects /jobs POST
    job_id = _generate_uuid()
    payload = {
        "job_id": job_id,
        "skill_name": agent.skill,
        "input_data": input_data,
        "budget": budget,
        "orchestrator_id": _owner_id or "anon",
    }
    
    # We call the agent directly. 
    # NOTE: If the agent is protected, we might need to pass our token?
    # For now, agents are public or check 'Authorization' header if provided.
    
    try:
        # We pass our bearer token to the agent so it can verify us if needed
        agent_headers = {}
        if _access_token:
            agent_headers["Authorization"] = f"Bearer {_access_token}"
            
        r = httpx.post(f"{agent.endpoint}/jobs", json=payload, headers=agent_headers, timeout=_timeout * 2)
        r.raise_for_status()
        result = r.json()
    except Exception as e:
        raise JobFailedError(agent.name, str(e))

    if result.get("status") != "SUCCESS":
        raise JobFailedError(agent.name, result.get("error_message", "Unknown error"))

    # 3. Pay (if auto_pay and cost > 0)
    cost = result.get("execution_cost", 0.0)
    if _owner_id and auto_pay and cost > 0:
        _transfer_credits(_owner_id, agent.owner_id, cost, job_id)

    return HireResult(
        job_id=job_id,
        status="SUCCESS",
        output=result.get("output_data"),
        cost=cost,
        time_ms=result.get("execution_time_ms", 0),
        agent_name=agent.name
    )


def hire_best(
    skill: str,
    input_data: dict[str, Any],
    budget: float | None = None,
) -> HireResult:
    """Convenience function to find the best agent and hire it immediately."""
    agents = discover(skill)
    if not agents:
        raise SkillNotFoundError(skill)
    
    # Best is first (sorted by reputation)
    best_agent = agents[0]
    return hire(best_agent, input_data, budget)


def get_balance() -> float:
    _ensure_connected()
    if not _owner_id:
        return 0.0
        
    url = f"{_supabase_url}/rest/v1/ledger_accounts?owner_id=eq.{_owner_id}&select=balance"
    
    try:
        r = httpx.get(url, headers=_get_headers())
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["balance"])
        return 0.0
    except Exception:
        return 0.0

    except Exception:
        return 0.0


def get_agent(agent_id: str) -> AgentProfile:
    _ensure_connected()
    url = f"{_supabase_url}/rest/v1/agents?id=eq.{agent_id}&select=*"
    
    try:
        with httpx.Client(timeout=_timeout) as client:
            r = client.get(url, headers=_get_headers())
            r.raise_for_status()
            data = r.json()
            
        if not data:
            raise AgentNotFoundError(agent_id)
            
        a = data[0]
        return AgentProfile(
            agent_id=str(a["id"]),
            name=a["name"],
            owner_id=str(a["owner_id"]),
            skill=a["skill"],
            cost=float(a["cost_per_call"]),
            reputation=float(a["reputation_score"]),
            endpoint=a["endpoint"],
            status="online",
        )
    except Exception as e:
        if isinstance(e, AgentNotFoundError): raise e
        raise ConnectionError("Registry", url, str(e))


def get_economy() -> EconomyStats:
    _ensure_connected()
    # Simple stats from DB
    try:
        # This would ideally be a dedicated RPC or view
        return EconomyStats(
            total_volume=0.0,
            active_agents=0,
            total_transactions=0,
            avg_network_cost=0.0
        )
    except:
        return EconomyStats(0,0,0,0)


def _transfer_credits(sender: str, receiver: str, amount: float, job_id: str):
    # Call RPC function
    url = f"{_supabase_url}/rest/v1/rpc/transfer_credits"
    payload = {
        "sender_id": sender,
        "receiver_id": receiver,
        "amount": amount,
        "description": f"Payment for job {job_id}",
        "job_id": job_id
    }
    
    try:
        r = httpx.post(url, json=payload, headers=_get_headers())
        r.raise_for_status()
    except Exception as e:
        # Log error but don't crash execution? 
        print(f"PAYMENT FAILED: {e}")
        # In production this should queue a retry
        pass

def _generate_uuid() -> str:
    import uuid
    return str(uuid.uuid4())
