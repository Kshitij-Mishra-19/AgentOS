"""Shared pytest fixtures for the collaboration system test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.executor.agent import ExecutorAgent
from agents.planner.agent import PlannerAgent
from agents.reviewer.agent import ReviewerAgent
from core.llm_provider import MockLLMProvider
from core.message_bus import MessageBus
from core.orchestrator import Orchestrator
from core.state_manager import StateManager
from core.task_manager import TaskManager


@pytest.fixture
def llm_provider() -> MockLLMProvider:
    return MockLLMProvider()


@pytest.fixture
def planner_agent(llm_provider: MockLLMProvider) -> PlannerAgent:
    return PlannerAgent(agent_id="planner", config={"planning": {"max_subtasks": 6}}, llm_provider=llm_provider)


@pytest.fixture
def executor_agent(llm_provider: MockLLMProvider) -> ExecutorAgent:
    return ExecutorAgent(agent_id="executor", config={}, llm_provider=llm_provider)


@pytest.fixture
def reviewer_agent(llm_provider: MockLLMProvider) -> ReviewerAgent:
    return ReviewerAgent(
        agent_id="reviewer",
        config={"review": {"reject_on_any_error": True}},
        llm_provider=llm_provider,
    )


@pytest.fixture
def wired_bus(planner_agent, executor_agent, reviewer_agent) -> MessageBus:
    bus = MessageBus()
    bus.subscribe("planner", planner_agent.handle)
    bus.subscribe("executor", executor_agent.handle)
    bus.subscribe("reviewer", reviewer_agent.handle)
    return bus


@pytest.fixture
def orchestrator(wired_bus: MessageBus) -> Orchestrator:
    return Orchestrator(
        bus=wired_bus,
        task_manager=TaskManager(),
        state_manager=StateManager(),
        max_revision_cycles=3,
        fail_fast=False,
        require_review=True,
    )
