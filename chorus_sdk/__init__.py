"""
🎵 Chorus SDK — The Developer's Gateway to the AI Skills Marketplace

The simplest way to discover, hire, and publish AI agents on the Chorus network.

Usage:
    import chorus_sdk as chorus

    chorus.connect("http://localhost:8001", "http://localhost:8002")

    # Discover agents
    agents = chorus.discover("analyze_text", min_reputation=40.0)

    # Hire one
    result = chorus.hire(agents[0], input_data={"text": "Hello"}, budget=0.50)
    print(result.output)

    # Publish your own agent
    chorus.publish(
        name="My-Agent",
        skill="summarize",
        cost=0.10,
        handler=lambda data: {"summary": data["text"][:100]},
    )
"""

    connect,
    discover,
    discover_all,
    hire,
    hire_best,
    get_balance,
    get_economy,
    get_agent,
from chorus_sdk.publisher import publish, serve
from chorus_sdk.models import AgentProfile, HireResult, EconomyStats
from chorus_sdk.errors import (
    ChorusError,
    ConnectionError,
    AgentNotFoundError,
    BudgetTooLowError,
    JobFailedError,
    InsufficientCreditsError,
    SkillNotFoundError,
)
from chorus_sdk.pipeline import Pipeline

__version__ = "0.1.0"
__all__ = [
    "connect",
    "discover",
    "hire",
    "hire_best",
    "publish",
    "serve",
    "get_balance",
    "get_economy",
    "get_agent",
    "Pipeline",
    "AgentProfile",
    "HireResult",
    "EconomyStats",
    "ChorusError",
    "ConnectionError",
    "AgentNotFoundError",
    "BudgetTooLowError",
    "JobFailedError",
    "InsufficientCreditsError",
    "SkillNotFoundError",
]
