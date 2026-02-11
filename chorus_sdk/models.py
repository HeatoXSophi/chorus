"""
Chorus SDK — Data Models

Clean, developer-friendly classes returned by the SDK.
These are the objects developers interact with — designed for
readability and ease of use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentProfile:
    """
    A discovered agent on the Chorus network.
    
    Attributes:
        agent_id: Unique identifier
        name: Human-readable name
        owner_id: Who operates this agent
        skill: What this agent can do
        cost: Credits per job
        reputation: Trust score (0-100)
        endpoint: Where the agent lives
        status: "online" or "offline"
    """
    agent_id: str
    name: str
    owner_id: str
    skill: str
    cost: float
    reputation: float
    endpoint: str
    status: str = "online"

    def __repr__(self) -> str:
        return (
            f"AgentProfile('{self.name}' | skill='{self.skill}' | "
            f"cost={self.cost:.2f} | rep={self.reputation:.1f})"
        )

    @property
    def is_online(self) -> bool:
        return self.status == "online"


@dataclass
class HireResult:
    """
    The result of hiring an agent to perform a job.
    
    Attributes:
        success: Whether the job completed successfully
        job_id: Unique job identifier
        agent_name: Who did the work
        output: The result data (dict)
        cost: How much was charged
        time_ms: How long it took
        error: Error message if failed
    """
    success: bool
    job_id: str
    agent_name: str
    output: dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0
    time_ms: int = 0
    error: str | None = None

    def __repr__(self) -> str:
        if self.success:
            return (
                f"HireResult(✅ agent='{self.agent_name}' | "
                f"cost={self.cost:.2f} | {self.time_ms}ms)"
            )
        return f"HireResult(❌ agent='{self.agent_name}' | error='{self.error}')"

    def __getitem__(self, key: str) -> Any:
        """Allow result['key'] access to output data."""
        return self.output[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Safe access to output data."""
        return self.output.get(key, default)


@dataclass
class EconomyStats:
    """Network economy snapshot."""
    total_accounts: int
    total_transactions: int
    total_volume: float
    balances: dict[str, float] = field(default_factory=dict)


@dataclass
class NetworkStatus:
    """Health status of the Chorus network."""
    registry_online: bool
    ledger_online: bool
    agents_online: int
    total_skills: int
    available_skills: list[str] = field(default_factory=list)
