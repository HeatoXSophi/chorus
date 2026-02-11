"""
Chorus Reputation Engine — PageRank-inspired scoring system.

Agents earn reputation through successful work. The score is influenced by
the reputation of the contracting agent (high-rep clients give more boost).
Failures are penalized more heavily than successes are rewarded.
"""

from __future__ import annotations

from chorus.models import ReputationUpdate, _now


# Tuning constants
BASE_REWARD = 2.0       # Points gained on success (before weighting)
BASE_PENALTY = 3.0      # Points lost on failure (before multiplier)
FAILURE_MULTIPLIER = 1.5  # Failures hurt 1.5× more
INITIAL_REPUTATION = 50.0
MIN_REPUTATION = 0.0
MAX_REPUTATION = 100.0


class ReputationEngine:
    """
    Manages reputation scores for all agents in the network.

    Score formula:
        SUCCESS: new = old + (BASE_REWARD × contractor_rep / 100)
        FAILURE: new = old - (BASE_PENALTY × FAILURE_MULTIPLIER)

    Score is clamped to [0.0, 100.0].
    """

    def __init__(self):
        self._scores: dict[str, float] = {}
        self._history: list[ReputationUpdate] = []
        self._stats: dict[str, dict] = {}  # agent_id -> {total, successes, failures}

    def initialize_agent(self, agent_id: str, initial_score: float = INITIAL_REPUTATION) -> float:
        """Register a new agent with an initial reputation score."""
        self._scores[agent_id] = initial_score
        self._stats[agent_id] = {"total": 0, "successes": 0, "failures": 0}
        return initial_score

    def get_score(self, agent_id: str) -> float:
        """Get the current reputation score for an agent."""
        return self._scores.get(agent_id, INITIAL_REPUTATION)

    def get_stats(self, agent_id: str) -> dict:
        """Get execution statistics for an agent."""
        return self._stats.get(agent_id, {"total": 0, "successes": 0, "failures": 0})

    def record_success(self, agent_id: str, job_id: str, contractor_reputation: float = 50.0) -> ReputationUpdate:
        """
        Record a successful job completion.
        
        The reputation boost is weighted by the contractor's own reputation:
        being hired by a high-reputation agent gives more credibility.
        """
        old_score = self._scores.get(agent_id, INITIAL_REPUTATION)

        # Weighted reward: high-rep contractors boost you more
        reward = BASE_REWARD * (contractor_reputation / 100.0)
        new_score = min(old_score + reward, MAX_REPUTATION)

        self._scores[agent_id] = new_score
        stats = self._stats.setdefault(agent_id, {"total": 0, "successes": 0, "failures": 0})
        stats["total"] += 1
        stats["successes"] += 1

        update = ReputationUpdate(
            agent_id=agent_id,
            old_score=round(old_score, 2),
            new_score=round(new_score, 2),
            job_id=job_id,
            success=True,
            contractor_reputation=contractor_reputation,
        )
        self._history.append(update)
        return update

    def record_failure(self, agent_id: str, job_id: str, contractor_reputation: float = 50.0) -> ReputationUpdate:
        """
        Record a failed job. Failures are penalized more heavily than successes.
        """
        old_score = self._scores.get(agent_id, INITIAL_REPUTATION)

        penalty = BASE_PENALTY * FAILURE_MULTIPLIER
        new_score = max(old_score - penalty, MIN_REPUTATION)

        self._scores[agent_id] = new_score
        stats = self._stats.setdefault(agent_id, {"total": 0, "successes": 0, "failures": 0})
        stats["total"] += 1
        stats["failures"] += 1

        update = ReputationUpdate(
            agent_id=agent_id,
            old_score=round(old_score, 2),
            new_score=round(new_score, 2),
            job_id=job_id,
            success=False,
            contractor_reputation=contractor_reputation,
        )
        self._history.append(update)
        return update

    def get_history(self, agent_id: str | None = None) -> list[ReputationUpdate]:
        """Get reputation change history, optionally filtered by agent."""
        if agent_id:
            return [u for u in self._history if u.agent_id == agent_id]
        return list(self._history)

    def get_leaderboard(self, top_n: int = 10) -> list[tuple[str, float]]:
        """Get the top N agents by reputation score."""
        sorted_agents = sorted(self._scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_agents[:top_n]
