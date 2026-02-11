"""
Chorus Agent Container — The "Body" for an AI "Brain".

Wraps any callable function into a Chorus-compatible agent that can:
- Declare skills and costs
- Receive and validate job requests
- Execute work and return structured results
- Track its own performance metrics
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable

from chorus.models import (
    AgentRegistration,
    ErrorCode,
    JobRequest,
    JobResult,
    JobStatus,
    SkillDefinition,
    _uuid,
)


class AgentContainer:
    """
    The universal wrapper that gives any AI function a 'Chorus body'.
    
    Usage:
        def my_ai_logic(input_data: dict) -> dict:
            return {"result": input_data["x"] * 2}
        
        agent = AgentContainer(
            name="Doubler-Bot",
            owner_id="acme_corp",
            skill_name="double_number",
            cost=0.05,
            logic=my_ai_logic,
        )
        
        result = agent.handle_job(job_request)
    """

    def __init__(
        self,
        name: str,
        owner_id: str,
        skill_name: str,
        skill_description: str = "",
        cost: float = 0.10,
        logic: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        api_endpoint: str = "local://memory",
    ):
        self.agent_id = _uuid()
        self.name = name
        self.owner_id = owner_id
        self.api_endpoint = api_endpoint

        self.skill = SkillDefinition(
            skill_name=skill_name,
            description=skill_description,
            cost_per_call=cost,
        )

        self._logic = logic or self._default_logic
        self._jobs_completed = 0
        self._jobs_failed = 0
        self._total_earnings = 0.0

    # -------------------------------------------------------------------------
    # Core Operations
    # -------------------------------------------------------------------------

    def handle_job(self, job_request: JobRequest) -> JobResult:
        """
        Process an incoming job request.
        
        1. Validates skill match
        2. Checks budget sufficiency
        3. Executes the internal logic
        4. Returns a structured JobResult
        """
        start_time = time.perf_counter()

        # Validate skill
        if job_request.skill_name != self.skill.skill_name:
            return self._failure(
                job_request,
                f"Skill mismatch: requested '{job_request.skill_name}', "
                f"I have '{self.skill.skill_name}'",
                ErrorCode.SKILL_MISMATCH,
                start_time,
            )

        # Validate budget
        if job_request.budget < self.skill.cost_per_call:
            return self._failure(
                job_request,
                f"Budget {job_request.budget:.2f} < my cost {self.skill.cost_per_call:.2f}",
                ErrorCode.BUDGET_INSUFFICIENT,
                start_time,
            )

        # Execute the AI logic
        try:
            output_data = self._logic(job_request.input_data)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            self._jobs_completed += 1
            self._total_earnings += self.skill.cost_per_call

            return JobResult(
                job_id=job_request.job_id,
                agent_id=self.agent_id,
                status=JobStatus.SUCCESS,
                output_data=output_data,
                execution_cost=self.skill.cost_per_call,
                execution_time_ms=elapsed_ms,
            )

        except Exception as e:
            self._jobs_failed += 1
            return self._failure(
                job_request,
                f"Execution error: {str(e)}",
                ErrorCode.EXECUTION_ERROR,
                start_time,
            )

    def get_registration(self) -> AgentRegistration:
        """Generate the registration message for this agent."""
        return AgentRegistration(
            agent_id=self.agent_id,
            agent_name=self.name,
            owner_id=self.owner_id,
            api_endpoint=self.api_endpoint,
            skills=[self.skill],
        )

    # -------------------------------------------------------------------------
    # Stats
    # -------------------------------------------------------------------------

    @property
    def success_rate(self) -> float:
        total = self._jobs_completed + self._jobs_failed
        if total == 0:
            return 0.0
        return self._jobs_completed / total

    @property
    def total_jobs(self) -> int:
        return self._jobs_completed + self._jobs_failed

    def get_stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "skill": self.skill.skill_name,
            "jobs_completed": self._jobs_completed,
            "jobs_failed": self._jobs_failed,
            "success_rate": f"{self.success_rate:.0%}",
            "total_earnings": self._total_earnings,
        }

    # -------------------------------------------------------------------------
    # Internals
    # -------------------------------------------------------------------------

    def _failure(
        self, job: JobRequest, message: str, code: ErrorCode, start_time: float
    ) -> JobResult:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        self._jobs_failed += 1
        return JobResult(
            job_id=job.job_id,
            agent_id=self.agent_id,
            status=JobStatus.FAILURE,
            error_message=message,
            error_code=code,
            execution_time_ms=elapsed_ms,
        )

    @staticmethod
    def _default_logic(input_data: dict) -> dict:
        """Fallback logic: echoes the input."""
        return {"echo": input_data}

    def __repr__(self) -> str:
        return f"<AgentContainer '{self.name}' skill='{self.skill.skill_name}' cost={self.skill.cost_per_call}>"
