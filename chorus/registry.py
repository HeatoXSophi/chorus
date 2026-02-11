"""
Chorus Registry — Agent discovery and registration.

The Registry is where agents announce their skills and where orchestrators
search for the right specialist. In Phase 0 this is in-memory; in Phase 1
it becomes a FastAPI service.
"""

from __future__ import annotations

from chorus.models import AgentInfo, AgentRegistration, SkillDefinition, _now
from chorus.reputation import ReputationEngine


class Registry:
    """
    In-memory agent registry with skill-based discovery.

    Agents register with their skills and cost. Orchestrators query
    the registry to find the best agent for a given skill, ranked by
    reputation score.
    """

    def __init__(self, reputation_engine: ReputationEngine | None = None):
        self._agents: dict[str, AgentInfo] = {}  # agent_id -> AgentInfo
        self._skill_index: dict[str, list[str]] = {}  # skill_name -> [agent_ids]
        self.reputation = reputation_engine or ReputationEngine()

    def register(self, registration: AgentRegistration) -> AgentInfo:
        """Register a new agent and index its skills."""
        initial_rep = self.reputation.initialize_agent(registration.agent_id)

        agent_info = AgentInfo(
            agent_id=registration.agent_id,
            agent_name=registration.agent_name,
            owner_id=registration.owner_id,
            api_endpoint=registration.api_endpoint,
            skills=registration.skills,
            reputation_score=initial_rep,
        )

        self._agents[registration.agent_id] = agent_info

        # Index by skill for fast discovery
        for skill in registration.skills:
            if skill.skill_name not in self._skill_index:
                self._skill_index[skill.skill_name] = []
            self._skill_index[skill.skill_name].append(registration.agent_id)

        return agent_info

    def discover(
        self,
        skill_name: str,
        min_reputation: float = 0.0,
        max_cost: float | None = None,
    ) -> list[AgentInfo]:
        """
        Find agents by skill, filtered and sorted by reputation (descending).
        
        Args:
            skill_name: The skill to search for
            min_reputation: Minimum reputation score required
            max_cost: Maximum cost per call (None = no limit)
        
        Returns:
            List of matching AgentInfo, sorted by reputation (best first)
        """
        agent_ids = self._skill_index.get(skill_name, [])
        results = []

        for agent_id in agent_ids:
            agent = self._agents.get(agent_id)
            if not agent or agent.status != "online":
                continue

            # Update reputation from engine
            agent.reputation_score = self.reputation.get_score(agent_id)

            if agent.reputation_score < min_reputation:
                continue

            # Check cost filter
            if max_cost is not None:
                skill_cost = next(
                    (s.cost_per_call for s in agent.skills if s.skill_name == skill_name),
                    float("inf"),
                )
                if skill_cost > max_cost:
                    continue

            results.append(agent)

        # Sort by reputation (highest first)
        results.sort(key=lambda a: a.reputation_score, reverse=True)
        return results

    def get_agent(self, agent_id: str) -> AgentInfo | None:
        """Get a specific agent by ID."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.reputation_score = self.reputation.get_score(agent_id)
        return agent

    def heartbeat(self, agent_id: str) -> bool:
        """Update agent's last heartbeat timestamp."""
        agent = self._agents.get(agent_id)
        if agent:
            agent.last_heartbeat = _now()
            agent.status = "online"
            return True
        return False

    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry."""
        agent = self._agents.pop(agent_id, None)
        if agent:
            for skill in agent.skills:
                ids = self._skill_index.get(skill.skill_name, [])
                if agent_id in ids:
                    ids.remove(agent_id)
            return True
        return False

    def list_all_skills(self) -> list[str]:
        """List all skills available in the network."""
        return list(self._skill_index.keys())

    def count_agents(self) -> int:
        """Total number of registered agents."""
        return len(self._agents)
