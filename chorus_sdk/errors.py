"""
Chorus SDK — Custom Error Hierarchy

Clean, developer-friendly errors that tell you exactly what went wrong
and how to fix it.
"""


class ChorusError(Exception):
    """Base error for all Chorus SDK operations."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConnectionError(ChorusError):
    """Cannot reach the Chorus network services."""

    def __init__(self, service: str, url: str, cause: str = ""):
        self.service = service
        self.url = url
        super().__init__(
            f"Cannot connect to Chorus {service} at {url}. "
            f"Is the service running? ({cause})",
            {"service": service, "url": url},
        )


class AgentNotFoundError(ChorusError):
    """No agent found matching the criteria."""

    def __init__(self, skill: str, filters: dict | None = None):
        self.skill = skill
        super().__init__(
            f"No agent found with skill '{skill}'. "
            f"Try lowering min_reputation or increasing max_cost.",
            {"skill": skill, "filters": filters or {}},
        )


class SkillNotFoundError(ChorusError):
    """The requested skill doesn't exist on the network."""

    def __init__(self, skill: str, available: list[str] | None = None):
        self.skill = skill
        self.available = available or []
        hint = f" Available skills: {', '.join(self.available)}" if self.available else ""
        super().__init__(
            f"Skill '{skill}' not found on the network.{hint}",
            {"skill": skill, "available": self.available},
        )


class BudgetTooLowError(ChorusError):
    """Offered budget is below the agent's minimum cost."""

    def __init__(self, budget: float, agent_cost: float, agent_name: str = ""):
        self.budget = budget
        self.agent_cost = agent_cost
        super().__init__(
            f"Budget {budget:.2f} is below {agent_name or 'agent'}'s "
            f"minimum cost of {agent_cost:.2f} credits.",
            {"budget": budget, "agent_cost": agent_cost},
        )


class InsufficientCreditsError(ChorusError):
    """Account doesn't have enough credits for this operation."""

    def __init__(self, owner_id: str, balance: float, required: float):
        self.owner_id = owner_id
        self.balance = balance
        self.required = required
        super().__init__(
            f"Account '{owner_id}' has {balance:.2f} credits, "
            f"needs {required:.2f}. Top up your account first.",
            {"owner_id": owner_id, "balance": balance, "required": required},
        )


class JobFailedError(ChorusError):
    """The hired agent failed to complete the job."""

    def __init__(self, agent_name: str, job_id: str, reason: str = ""):
        self.agent_name = agent_name
        self.job_id = job_id
        self.reason = reason
        super().__init__(
            f"Agent '{agent_name}' failed job {job_id[:8]}... — {reason}",
            {"agent_name": agent_name, "job_id": job_id, "reason": reason},
        )
