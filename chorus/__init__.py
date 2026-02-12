"""
Proyecto Chorus — The AI Skills Marketplace Protocol
"""

__version__ = "0.1.0"
__protocol_version__ = "0.1"

# Expose the SDK interface directly from 'chorus'
from chorus_sdk import (
    connect,
    discover,
    discover_all,
    hire,
    hire_best,
    publish,
    serve,
    get_balance,
    get_economy,
    get_agent,
    Pipeline,
    AgentProfile,
    HireResult,
    EconomyStats,
    ChorusError,
    ConnectionError,
    AgentNotFoundError,
    BudgetTooLowError,
    JobFailedError,
    InsufficientCreditsError,
    SkillNotFoundError,
)
