"""
Chorus SDK — Pipeline Module

Chain multiple agents together with a fluent API.
Data flows from one step to the next automatically.

Example:
    result = (
        chorus.Pipeline("Sales Analysis")
        .step("analyze_text", lambda ctx: {"text": ctx["report"]})
        .step("calculate", lambda ctx: {"primary_number": ctx["primary_number"]})
        .step("translate", lambda ctx: {"text": ctx["result"]})
        .run(context={"report": "Revenue was $42,000"}, budget=1.0)
    )
"""

from __future__ import annotations

from typing import Any, Callable

from chorus_sdk.client import discover, hire, _ensure_connected, _owner_id
from chorus_sdk.errors import AgentNotFoundError, ChorusError
from chorus_sdk.models import AgentProfile, HireResult


class PipelineStep:
    """A single step in a pipeline."""

    def __init__(
        self,
        skill: str,
        input_builder: Callable[[dict], dict],
        budget_fraction: float = 0.25,
        min_reputation: float = 0.0,
        label: str = "",
    ):
        self.skill = skill
        self.input_builder = input_builder
        self.budget_fraction = budget_fraction
        self.min_reputation = min_reputation
        self.label = label or skill


class PipelineResult:
    """The final result of a pipeline execution."""

    def __init__(self):
        self.success: bool = False
        self.context: dict[str, Any] = {}
        self.steps_completed: int = 0
        self.steps_total: int = 0
        self.total_cost: float = 0.0
        self.step_results: list[HireResult] = []
        self.error: str | None = None

    def __repr__(self) -> str:
        status = "✅" if self.success else "❌"
        return (
            f"PipelineResult({status} {self.steps_completed}/{self.steps_total} steps | "
            f"cost={self.total_cost:.2f})"
        )

    def __getitem__(self, key: str) -> Any:
        return self.context[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)


class Pipeline:
    """
    Chain multiple agents into a workflow.

    Each step's output is merged into a shared context that
    subsequent steps can read from.

    Example:
        >>> result = (
        ...     chorus.Pipeline("Data Processing")
        ...     .step("analyze_text", lambda ctx: {"text": ctx["raw"]})
        ...     .step("calculate", lambda ctx: {"number": ctx["primary_number"]})
        ...     .run({"raw": "Revenue: $42,000"}, budget=1.0)
        ... )
        >>> print(result["projected_value"])
    """

    def __init__(self, name: str = "Pipeline"):
        self.name = name
        self._steps: list[PipelineStep] = []
        self._on_step: Callable[[int, str, str], None] | None = None

    def step(
        self,
        skill: str,
        input_builder: Callable[[dict], dict],
        budget_fraction: float = 0.25,
        min_reputation: float = 0.0,
        label: str = "",
    ) -> "Pipeline":
        """
        Add a step to the pipeline.

        Args:
            skill: Which skill to hire for this step
            input_builder: Function that takes the accumulated context
                          and returns input_data for this step
            budget_fraction: What fraction of total budget to allocate
            min_reputation: Minimum agent reputation required
            label: Human-readable step name

        Returns:
            self (for chaining)
        """
        self._steps.append(PipelineStep(
            skill=skill,
            input_builder=input_builder,
            budget_fraction=budget_fraction,
            min_reputation=min_reputation,
            label=label,
        ))
        return self

    def on_step(self, callback: Callable[[int, str, str], None]) -> "Pipeline":
        """
        Register a callback for step progress updates.

        Callback receives: (step_number, skill, status_message)
        """
        self._on_step = callback
        return self

    def run(
        self,
        context: dict[str, Any] | None = None,
        budget: float = 1.0,
        verbose: bool = True,
    ) -> PipelineResult:
        """
        Execute the pipeline.

        Args:
            context: Initial data (available to all steps)
            budget: Total budget for all steps combined
            verbose: Print progress to console

        Returns:
            PipelineResult with accumulated context and step details
        """
        _ensure_connected()

        result = PipelineResult()
        result.steps_total = len(self._steps)
        ctx = dict(context or {})
        remaining = budget

        if verbose:
            print(f"\n🎵 Pipeline '{self.name}' — {len(self._steps)} steps, budget: {budget:.2f}")
            print("─" * 50)

        for i, step in enumerate(self._steps, 1):
            step_budget = budget * step.budget_fraction
            step_budget = min(step_budget, remaining)

            if verbose:
                print(f"  [{i}/{result.steps_total}] {step.label}...", end=" ", flush=True)

            if self._on_step:
                self._on_step(i, step.skill, "discovering")

            # Discover agents
            agents = discover(
                step.skill,
                min_reputation=step.min_reputation,
                max_cost=step_budget,
            )

            if not agents:
                msg = f"No agent for '{step.skill}'"
                if verbose:
                    print(f"❌ {msg}")
                result.error = msg
                result.context = ctx
                return result

            # Build input
            try:
                input_data = step.input_builder(ctx)
            except Exception as e:
                msg = f"Input builder failed: {e}"
                if verbose:
                    print(f"❌ {msg}")
                result.error = msg
                result.context = ctx
                return result

            if self._on_step:
                self._on_step(i, step.skill, f"hiring {agents[0].name}")

            # Hire
            try:
                hire_result = hire(agents[0], input_data, budget=step_budget)
            except ChorusError as e:
                if verbose:
                    print(f"❌ {e.message}")
                result.error = e.message
                result.context = ctx
                return result

            # Update context
            ctx.update(hire_result.output)
            remaining -= hire_result.cost
            result.total_cost += hire_result.cost
            result.steps_completed += 1
            result.step_results.append(hire_result)

            if verbose:
                print(f"✅ {agents[0].name} (cost: {hire_result.cost:.2f})")

        result.success = True
        result.context = ctx

        if verbose:
            print("─" * 50)
            print(f"  ✨ Complete! Cost: {result.total_cost:.2f} / {budget:.2f}")

        return result
