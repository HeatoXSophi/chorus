"""
Chorus Protocol Data Models — Pydantic v2

Defines all structured messages for the Chorus protocol:
agent registration, job requests, job results, transfers, and reputation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class JobStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PENDING = "PENDING"


class ErrorCode(str, Enum):
    SKILL_MISMATCH = "SKILL_MISMATCH"
    BUDGET_INSUFFICIENT = "BUDGET_INSUFFICIENT"
    AGENT_OFFLINE = "AGENT_OFFLINE"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    TRANSFER_FAILED = "TRANSFER_FAILED"


# =============================================================================
# Core Models
# =============================================================================

def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SkillDefinition(BaseModel):
    """A single capability that an agent can perform."""
    skill_name: str = Field(..., description="Unique skill identifier")
    description: str = Field("", description="What this skill does")
    cost_per_call: float = Field(..., ge=0, description="Cost in chorus credits")
    input_schema: dict[str, str] = Field(default_factory=dict, description="Expected input keys and types")
    output_schema: dict[str, str] = Field(default_factory=dict, description="Expected output keys and types")


class AgentRegistration(BaseModel):
    """Message sent by an agent to register itself with the Registry."""
    agent_id: str = Field(default_factory=_uuid)
    agent_name: str = Field(..., description="Human-readable agent name")
    owner_id: str = Field(..., description="Owner/operator identifier")
    api_endpoint: str = Field("local://memory", description="URL where agent listens for jobs")
    skills: list[SkillDefinition] = Field(default_factory=list)
    version: str = Field("0.1")
    timestamp_utc: str = Field(default_factory=_now)


class AgentInfo(BaseModel):
    """Agent record as stored in the Registry (includes reputation)."""
    agent_id: str
    agent_name: str
    owner_id: str
    api_endpoint: str
    skills: list[SkillDefinition]
    reputation_score: float = Field(default=50.0, ge=0.0, le=100.0)
    status: str = Field(default="online")
    registered_at: str = Field(default_factory=_now)
    last_heartbeat: str = Field(default_factory=_now)


class JobRequest(BaseModel):
    """A work offer sent from an orchestrator to a specialist agent."""
    job_id: str = Field(default_factory=_uuid)
    orchestrator_id: str = Field(..., description="ID of the requesting agent")
    skill_name: str = Field(..., description="Which skill is being requested")
    input_data: dict[str, Any] = Field(default_factory=dict)
    budget: float = Field(..., ge=0, description="Max credits willing to pay")
    currency: str = Field(default="chorus_credits_v1")
    callback_url: str = Field(default="", description="Where to send results")
    timestamp_utc: str = Field(default_factory=_now)


class JobResult(BaseModel):
    """Result returned by a specialist agent after processing a job."""
    job_id: str
    agent_id: str
    status: JobStatus
    output_data: Optional[dict[str, Any]] = None
    execution_cost: float = Field(default=0.0, ge=0)
    execution_time_ms: int = Field(default=0, ge=0)
    error_message: Optional[str] = None
    error_code: Optional[ErrorCode] = None
    timestamp_utc: str = Field(default_factory=_now)


class TransferRecord(BaseModel):
    """Record of a credit transfer between two owners."""
    transfer_id: str = Field(default_factory=_uuid)
    from_owner: str
    to_owner: str
    amount: float = Field(..., gt=0)
    job_id: str = Field(..., description="Associated job")
    timestamp_utc: str = Field(default_factory=_now)


class ReputationUpdate(BaseModel):
    """A reputation change event."""
    agent_id: str
    old_score: float
    new_score: float
    job_id: str
    success: bool
    contractor_reputation: float = Field(default=50.0, description="Reputation of the hiring agent")
    timestamp_utc: str = Field(default_factory=_now)
