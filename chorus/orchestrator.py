"""
Chorus Orchestrator — Task decomposition and multi-agent coordination.

The Orchestrator is the 'brain' that breaks complex tasks into sub-tasks,
discovers the best agents for each, manages budget allocation, processes
payments through the ledger, and synthesizes final results.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from chorus.agent import AgentContainer
from chorus.ledger import Ledger, InsufficientCreditsError
from chorus.models import (
    AgentInfo,
    JobRequest,
    JobResult,
    JobStatus,
    _uuid,
)
from chorus.registry import Registry


class SubTask:
    """Defines a single step in a complex task pipeline."""

    def __init__(
        self,
        skill_name: str,
        build_input: Callable[[dict[str, Any]], dict[str, Any]],
        extract_output_key: str | None = None,
        budget_fraction: float = 0.2,
        description: str = "",
    ):
        """
        Args:
            skill_name: Which skill to look for
            build_input: Function that takes accumulated context → input_data for this step
            extract_output_key: Key to pull from output_data into the context
            budget_fraction: What fraction of total budget to allocate
            description: Human-readable description
        """
        self.skill_name = skill_name
        self.build_input = build_input
        self.extract_output_key = extract_output_key
        self.budget_fraction = budget_fraction
        self.description = description


class TaskPipeline:
    """A sequence of SubTasks that form a complex workflow."""

    def __init__(self, name: str, subtasks: list[SubTask] | None = None):
        self.name = name
        self.subtasks = subtasks or []

    def add(self, subtask: SubTask) -> "TaskPipeline":
        self.subtasks.append(subtask)
        return self


class OrchestratorResult:
    """The final result of a complex orchestrated task."""

    def __init__(self):
        self.success = False
        self.final_output: dict[str, Any] = {}
        self.context: dict[str, Any] = {}
        self.total_cost: float = 0.0
        self.steps_completed: int = 0
        self.steps_total: int = 0
        self.step_results: list[dict] = []
        self.error: str | None = None


class Orchestrator:
    """
    Coordinates multi-agent workflows using the Registry and Ledger.
    
    Usage:
        orchestrator = Orchestrator(registry, ledger, owner_id="my_company")
        
        pipeline = TaskPipeline("Analyze Sales", [
            SubTask("extract_numbers", lambda ctx: {"text": ctx["raw_text"]}),
            SubTask("calculate_projection", lambda ctx: {"number": ctx["extracted"]}),
        ])
        
        result = orchestrator.execute(pipeline, initial_context, budget=1.0)
    """

    def __init__(
        self,
        registry: Registry,
        ledger: Ledger,
        owner_id: str = "orchestrator_default",
        agent_id: str | None = None,
        print_logs: bool = True,
    ):
        self.agent_id = agent_id or _uuid()
        self.owner_id = owner_id
        self.registry = registry
        self.ledger = ledger
        self._print = print_logs

        # Ensure orchestrator has an account
        self.ledger.create_account(owner_id)

        # For local mode: direct agent references
        self._local_agents: dict[str, AgentContainer] = {}

    def register_local_agent(self, agent: AgentContainer) -> None:
        """Register an agent for local (in-memory) execution."""
        reg = agent.get_registration()
        self.registry.register(reg)
        self._local_agents[agent.agent_id] = agent
        self.ledger.create_account(agent.owner_id)
        self._log(f"✅ Registered agent '{agent.name}' (skill: {agent.skill.skill_name})")

    def execute(
        self,
        pipeline: TaskPipeline,
        initial_context: dict[str, Any],
        budget: float,
    ) -> OrchestratorResult:
        """
        Execute a multi-step task pipeline.
        
        Args:
            pipeline: The workflow definition
            initial_context: Starting data
            budget: Total budget for the entire pipeline
        """
        result = OrchestratorResult()
        result.steps_total = len(pipeline.subtasks)
        context = dict(initial_context)
        remaining_budget = budget

        self._log(f"\n{'='*60}")
        self._log(f"🎵 CHORUS ORCHESTRATOR — Starting: '{pipeline.name}'")
        self._log(f"   Budget: {budget:.2f} credits | Steps: {len(pipeline.subtasks)}")
        self._log(f"{'='*60}")

        for i, subtask in enumerate(pipeline.subtasks, 1):
            step_budget = budget * subtask.budget_fraction
            step_budget = min(step_budget, remaining_budget)

            self._log(f"\n📋 Step {i}/{result.steps_total}: {subtask.description or subtask.skill_name}")
            self._log(f"   Skill needed: '{subtask.skill_name}' | Budget: {step_budget:.2f}")

            # 1. Discover agents
            agents = self.registry.discover(subtask.skill_name, max_cost=step_budget)
            if not agents:
                error_msg = f"No agent found for skill '{subtask.skill_name}'"
                self._log(f"   ❌ {error_msg}")
                result.error = error_msg
                result.context = context
                return result

            best_agent_info = agents[0]
            self._log(
                f"   🔍 Found: '{best_agent_info.agent_name}' "
                f"(rep: {best_agent_info.reputation_score:.1f})"
            )

            # 2. Build input
            try:
                input_data = subtask.build_input(context)
            except Exception as e:
                error_msg = f"Input builder failed: {e}"
                self._log(f"   ❌ {error_msg}")
                result.error = error_msg
                result.context = context
                return result

            # 3. Create and send job request
            job_request = JobRequest(
                orchestrator_id=self.agent_id,
                skill_name=subtask.skill_name,
                input_data=input_data,
                budget=step_budget,
            )

            # 4. Execute (local mode: direct call)
            local_agent = self._local_agents.get(best_agent_info.agent_id)
            if local_agent:
                job_result = local_agent.handle_job(job_request)
            else:
                # Phase 1: HTTP call would go here
                error_msg = f"Agent '{best_agent_info.agent_id}' not available locally"
                self._log(f"   ❌ {error_msg}")
                result.error = error_msg
                result.context = context
                return result

            # 5. Process result
            step_record = {
                "step": i,
                "skill": subtask.skill_name,
                "agent": best_agent_info.agent_name,
                "status": job_result.status.value,
                "cost": job_result.execution_cost,
                "time_ms": job_result.execution_time_ms,
            }

            if job_result.status == JobStatus.SUCCESS:
                self._log(f"   ✅ Success! Cost: {job_result.execution_cost:.2f} | Time: {job_result.execution_time_ms}ms")

                # Update context with output
                if job_result.output_data:
                    if subtask.extract_output_key and subtask.extract_output_key in job_result.output_data:
                        context[subtask.extract_output_key] = job_result.output_data[subtask.extract_output_key]
                    context.update(job_result.output_data)

                # Process payment
                try:
                    agent_owner = best_agent_info.owner_id
                    transfer = self.ledger.transfer(
                        from_owner=self.owner_id,
                        to_owner=agent_owner,
                        amount=job_result.execution_cost,
                        job_id=job_request.job_id,
                    )
                    self._log(f"   💰 Payment: {transfer.amount:.2f} → '{agent_owner}'")
                except InsufficientCreditsError as e:
                    self._log(f"   ⚠️ Payment failed: {e}")

                # Update reputation
                self.registry.reputation.record_success(
                    best_agent_info.agent_id,
                    job_request.job_id,
                    contractor_reputation=self.registry.reputation.get_score(self.agent_id)
                        if self.agent_id in self.registry.reputation._scores
                        else 50.0,
                )

                remaining_budget -= job_result.execution_cost
                result.steps_completed += 1
                result.total_cost += job_result.execution_cost
                step_record["output"] = job_result.output_data

            else:
                self._log(f"   ❌ Failed: {job_result.error_message}")
                self.registry.reputation.record_failure(
                    best_agent_info.agent_id,
                    job_request.job_id,
                )
                result.error = job_result.error_message
                step_record["error"] = job_result.error_message
                result.step_results.append(step_record)
                result.context = context
                return result

            result.step_results.append(step_record)

        # All steps completed
        result.success = True
        result.final_output = context
        result.context = context

        self._log(f"\n{'='*60}")
        self._log(f"🎵 TASK COMPLETE: '{pipeline.name}'")
        self._log(f"   Total cost: {result.total_cost:.2f} / {budget:.2f}")
        self._log(f"   Steps: {result.steps_completed}/{result.steps_total}")
        self._log(f"   Budget remaining: {remaining_budget:.2f}")
        self._log(f"{'='*60}")

        return result

    def _log(self, message: str) -> None:
        if self._print:
            print(message)
