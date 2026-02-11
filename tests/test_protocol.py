"""
===================================================================
  🎵 CHORUS — Unit Tests
===================================================================

Tests for the core Chorus protocol components:
  - Data models
  - AgentContainer
  - Registry
  - Ledger
  - ReputationEngine
  - Orchestrator
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from chorus.models import (
    SkillDefinition,
    AgentRegistration,
    JobRequest,
    JobResult,
    JobStatus,
    ErrorCode,
    TransferRecord,
)
from chorus.agent import AgentContainer
from chorus.registry import Registry
from chorus.ledger import Ledger, InsufficientCreditsError
from chorus.reputation import ReputationEngine
from chorus.orchestrator import Orchestrator, TaskPipeline, SubTask


# =============================================================================
# Model Tests
# =============================================================================

class TestModels:
    def test_skill_definition(self):
        skill = SkillDefinition(skill_name="test", cost_per_call=0.1)
        assert skill.skill_name == "test"
        assert skill.cost_per_call == 0.1

    def test_agent_registration_generates_uuid(self):
        reg = AgentRegistration(agent_name="TestBot", owner_id="owner1")
        assert reg.agent_id is not None
        assert len(reg.agent_id) == 36  # UUID format

    def test_job_request_defaults(self):
        job = JobRequest(orchestrator_id="orch1", skill_name="test", budget=1.0)
        assert job.currency == "chorus_credits_v1"
        assert job.job_id is not None

    def test_job_result_success(self):
        result = JobResult(
            job_id="j1", agent_id="a1",
            status=JobStatus.SUCCESS,
            output_data={"x": 42},
            execution_cost=0.1,
        )
        assert result.status == JobStatus.SUCCESS
        assert result.error_message is None


# =============================================================================
# AgentContainer Tests
# =============================================================================

class TestAgentContainer:
    def setup_method(self):
        self.agent = AgentContainer(
            name="TestAgent",
            owner_id="owner_test",
            skill_name="double",
            cost=0.10,
            logic=lambda data: {"result": data.get("n", 0) * 2},
        )

    def test_handle_success(self):
        job = JobRequest(orchestrator_id="orch", skill_name="double", budget=0.50, input_data={"n": 21})
        result = self.agent.handle_job(job)
        assert result.status == JobStatus.SUCCESS
        assert result.output_data["result"] == 42
        assert result.execution_cost == 0.10

    def test_handle_skill_mismatch(self):
        job = JobRequest(orchestrator_id="orch", skill_name="wrong_skill", budget=1.0)
        result = self.agent.handle_job(job)
        assert result.status == JobStatus.FAILURE
        assert result.error_code == ErrorCode.SKILL_MISMATCH

    def test_handle_budget_insufficient(self):
        job = JobRequest(orchestrator_id="orch", skill_name="double", budget=0.01)
        result = self.agent.handle_job(job)
        assert result.status == JobStatus.FAILURE
        assert result.error_code == ErrorCode.BUDGET_INSUFFICIENT

    def test_handle_execution_error(self):
        agent = AgentContainer(
            name="Faulty",
            owner_id="owner",
            skill_name="crash",
            cost=0.01,
            logic=lambda data: 1 / 0,  # Will raise ZeroDivisionError
        )
        job = JobRequest(orchestrator_id="orch", skill_name="crash", budget=1.0)
        result = agent.handle_job(job)
        assert result.status == JobStatus.FAILURE
        assert result.error_code == ErrorCode.EXECUTION_ERROR

    def test_stats_tracking(self):
        job = JobRequest(orchestrator_id="orch", skill_name="double", budget=1.0, input_data={"n": 5})
        self.agent.handle_job(job)
        self.agent.handle_job(job)
        assert self.agent.total_jobs == 2
        assert self.agent._jobs_completed == 2
        assert self.agent.success_rate == 1.0

    def test_registration_message(self):
        reg = self.agent.get_registration()
        assert reg.agent_name == "TestAgent"
        assert reg.owner_id == "owner_test"
        assert len(reg.skills) == 1
        assert reg.skills[0].skill_name == "double"


# =============================================================================
# Registry Tests
# =============================================================================

class TestRegistry:
    def setup_method(self):
        self.registry = Registry()
        self.reg1 = AgentRegistration(
            agent_name="Agent1",
            owner_id="owner1",
            skills=[SkillDefinition(skill_name="analyze", cost_per_call=0.10)],
        )
        self.reg2 = AgentRegistration(
            agent_name="Agent2",
            owner_id="owner2",
            skills=[SkillDefinition(skill_name="analyze", cost_per_call=0.20)],
        )

    def test_register_and_discover(self):
        self.registry.register(self.reg1)
        found = self.registry.discover("analyze")
        assert len(found) == 1
        assert found[0].agent_name == "Agent1"

    def test_discover_multiple_agents(self):
        self.registry.register(self.reg1)
        self.registry.register(self.reg2)
        found = self.registry.discover("analyze")
        assert len(found) == 2

    def test_discover_with_cost_filter(self):
        self.registry.register(self.reg1)
        self.registry.register(self.reg2)
        found = self.registry.discover("analyze", max_cost=0.15)
        assert len(found) == 1
        assert found[0].agent_name == "Agent1"

    def test_discover_nonexistent_skill(self):
        self.registry.register(self.reg1)
        found = self.registry.discover("nonexistent")
        assert len(found) == 0

    def test_unregister(self):
        self.registry.register(self.reg1)
        assert self.registry.count_agents() == 1
        self.registry.unregister(self.reg1.agent_id)
        assert self.registry.count_agents() == 0

    def test_list_skills(self):
        self.registry.register(self.reg1)
        skills = self.registry.list_all_skills()
        assert "analyze" in skills


# =============================================================================
# Ledger Tests
# =============================================================================

class TestLedger:
    def setup_method(self):
        self.ledger = Ledger()
        self.ledger.create_account("alice", 100.0)
        self.ledger.create_account("bob", 50.0)

    def test_create_account(self):
        assert self.ledger.get_balance("alice") == 100.0

    def test_transfer_success(self):
        record = self.ledger.transfer("alice", "bob", 25.0, "job1")
        assert self.ledger.get_balance("alice") == 75.0
        assert self.ledger.get_balance("bob") == 75.0
        assert record.amount == 25.0

    def test_transfer_insufficient_funds(self):
        with pytest.raises(InsufficientCreditsError):
            self.ledger.transfer("alice", "bob", 200.0, "job2")

    def test_transfer_nonexistent_account(self):
        with pytest.raises(InsufficientCreditsError):
            self.ledger.transfer("ghost", "bob", 10.0, "job3")

    def test_transfer_invalid_amount(self):
        with pytest.raises(ValueError):
            self.ledger.transfer("alice", "bob", -5.0, "job4")

    def test_audit_log(self):
        self.ledger.transfer("alice", "bob", 10.0, "job_a")
        self.ledger.transfer("bob", "alice", 5.0, "job_b")
        log = self.ledger.get_audit_log()
        assert len(log) == 2

    def test_audit_filter_by_job(self):
        self.ledger.transfer("alice", "bob", 10.0, "job_x")
        self.ledger.transfer("alice", "bob", 20.0, "job_y")
        log = self.ledger.get_audit_log(job_id="job_x")
        assert len(log) == 1

    def test_total_volume(self):
        self.ledger.transfer("alice", "bob", 10.0, "j1")
        self.ledger.transfer("alice", "bob", 15.0, "j2")
        assert self.ledger.get_total_volume() == 25.0


# =============================================================================
# Reputation Engine Tests
# =============================================================================

class TestReputation:
    def setup_method(self):
        self.engine = ReputationEngine()
        self.engine.initialize_agent("agent1")

    def test_initial_score(self):
        assert self.engine.get_score("agent1") == 50.0

    def test_success_increases_score(self):
        update = self.engine.record_success("agent1", "job1", contractor_reputation=80.0)
        assert update.new_score > update.old_score

    def test_failure_decreases_score(self):
        update = self.engine.record_failure("agent1", "job1")
        assert update.new_score < update.old_score

    def test_failure_penalty_exceeds_success_reward(self):
        self.engine.initialize_agent("a")
        self.engine.initialize_agent("b")
        s = self.engine.record_success("a", "j1", contractor_reputation=50.0)
        f = self.engine.record_failure("b", "j2", contractor_reputation=50.0)
        reward = s.new_score - s.old_score
        penalty = f.old_score - f.new_score
        assert penalty > reward  # Failures hurt more

    def test_high_rep_contractor_gives_more_boost(self):
        self.engine.initialize_agent("x")
        self.engine.initialize_agent("y")
        low = self.engine.record_success("x", "j1", contractor_reputation=20.0)
        high = self.engine.record_success("y", "j2", contractor_reputation=90.0)
        boost_low = low.new_score - low.old_score
        boost_high = high.new_score - high.old_score
        assert boost_high > boost_low

    def test_score_clamped_to_bounds(self):
        self.engine._scores["agent1"] = 99.0
        self.engine.record_success("agent1", "j1", contractor_reputation=100.0)
        assert self.engine.get_score("agent1") <= 100.0

        self.engine._scores["agent1"] = 1.0
        self.engine.record_failure("agent1", "j2")
        assert self.engine.get_score("agent1") >= 0.0

    def test_leaderboard(self):
        self.engine.initialize_agent("top")
        self.engine._scores["top"] = 95.0
        board = self.engine.get_leaderboard(top_n=2)
        assert board[0][0] == "top"

    def test_stats(self):
        self.engine.record_success("agent1", "j1")
        self.engine.record_failure("agent1", "j2")
        stats = self.engine.get_stats("agent1")
        assert stats["total"] == 2
        assert stats["successes"] == 1
        assert stats["failures"] == 1


# =============================================================================
# Orchestrator Tests
# =============================================================================

class TestOrchestrator:
    def setup_method(self):
        self.registry = Registry()
        self.ledger = Ledger()
        self.ledger.create_account("test_user", 10.0)
        self.orchestrator = Orchestrator(
            registry=self.registry,
            ledger=self.ledger,
            owner_id="test_user",
            print_logs=False,
        )

        # Register a simple doubler agent
        self.doubler = AgentContainer(
            name="Doubler",
            owner_id="agent_owner",
            skill_name="double",
            cost=0.10,
            logic=lambda data: {"result": data.get("n", 0) * 2},
        )
        self.orchestrator.register_local_agent(self.doubler)

    def test_simple_pipeline(self):
        pipeline = TaskPipeline("Test", [
            SubTask(
                skill_name="double",
                build_input=lambda ctx: {"n": ctx["value"]},
                budget_fraction=1.0,
            ),
        ])
        result = self.orchestrator.execute(pipeline, {"value": 21}, budget=1.0)
        assert result.success
        assert result.final_output.get("result") == 42
        assert result.total_cost == 0.10

    def test_pipeline_budget_tracking(self):
        pipeline = TaskPipeline("Budget Test", [
            SubTask(
                skill_name="double",
                build_input=lambda ctx: {"n": 5},
                budget_fraction=1.0,
            ),
        ])
        result = self.orchestrator.execute(pipeline, {}, budget=1.0)
        assert result.success
        assert self.ledger.get_balance("test_user") < 10.0
        assert self.ledger.get_balance("agent_owner") > 0.0

    def test_pipeline_missing_skill(self):
        pipeline = TaskPipeline("Missing Skill", [
            SubTask(
                skill_name="nonexistent",
                build_input=lambda ctx: {},
                budget_fraction=1.0,
            ),
        ])
        result = self.orchestrator.execute(pipeline, {}, budget=1.0)
        assert not result.success
        assert "No agent found" in result.error

    def test_multi_step_pipeline(self):
        # Add a second agent
        adder = AgentContainer(
            name="Adder",
            owner_id="adder_owner",
            skill_name="add_ten",
            cost=0.05,
            logic=lambda data: {"result": data.get("n", 0) + 10},
        )
        self.orchestrator.register_local_agent(adder)

        pipeline = TaskPipeline("Multi-Step", [
            SubTask(
                skill_name="double",
                build_input=lambda ctx: {"n": ctx["value"]},
                budget_fraction=0.5,
            ),
            SubTask(
                skill_name="add_ten",
                build_input=lambda ctx: {"n": ctx.get("result", 0)},
                budget_fraction=0.5,
            ),
        ])
        result = self.orchestrator.execute(pipeline, {"value": 5}, budget=1.0)
        assert result.success
        assert result.final_output.get("result") == 20  # (5*2) + 10
        assert result.steps_completed == 2
        assert result.total_cost == pytest.approx(0.15)  # 0.10 + 0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
