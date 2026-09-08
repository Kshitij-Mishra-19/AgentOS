"""Wires configuration, agents, the message bus, and the orchestrator together.

Both the CLI (``app/__main__.py``) and the example scripts
(``examples/*.py``) use this module so there is exactly one place that
knows how to assemble a runnable system from ``config/collaboration.yaml``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from agents.executor.agent import ExecutorAgent
from agents.planner.agent import PlannerAgent
from agents.reviewer.agent import ReviewerAgent
from core.errors import ConfigurationError
from core.llm_provider import LLMProvider, MockLLMProvider
from core.logging import configure_logging
from core.message_bus import MessageBus
from core.orchestrator import Orchestrator
from core.state_manager import StateManager
from core.task_manager import TaskManager

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "collaboration.yaml"


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def build_llm_provider(config: dict[str, Any]) -> LLMProvider:
    llm_config = config.get("llm", {})
    provider_name = llm_config.get("provider", "mock")

    if provider_name == "mock":
        return MockLLMProvider()

    # "real" is intentionally left unwired: it requires a concrete vendor
    # adapter subclassing RealLLMProvider. This keeps zero hard dependency
    # on any specific LLM vendor in the default codebase.
    raise ConfigurationError(
        f"llm.provider={provider_name!r} is not wired up by default. "
        "Implement a RealLLMProvider subclass (see core/llm_provider.py) "
        "and update build_llm_provider() to construct it."
    )


class Application:
    """A fully assembled, runnable instance of the collaboration system."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        configure_logging(config.get("logging", {}).get("level", "INFO"))

        self.llm_provider = build_llm_provider(config)
        self.bus = MessageBus()
        self.task_manager = TaskManager()
        self.state_manager = StateManager()

        agents_config = config.get("agents", {})
        self.planner = PlannerAgent(
            agent_id="planner",
            config=load_yaml(REPO_ROOT / agents_config.get("planner", {}).get(
                "config_path", "agents/planner/config.yaml"
            )),
            llm_provider=self.llm_provider,
        )
        self.executor = ExecutorAgent(
            agent_id="executor",
            config=load_yaml(REPO_ROOT / agents_config.get("executor", {}).get(
                "config_path", "agents/executor/config.yaml"
            )),
            llm_provider=self.llm_provider,
        )
        self.reviewer = ReviewerAgent(
            agent_id="reviewer",
            config=load_yaml(REPO_ROOT / agents_config.get("reviewer", {}).get(
                "config_path", "agents/reviewer/config.yaml"
            )),
            llm_provider=self.llm_provider,
        )

        self.bus.subscribe("planner", self.planner.handle)
        self.bus.subscribe("executor", self.executor.handle)
        self.bus.subscribe("reviewer", self.reviewer.handle)

        workflow_config = config.get("workflow", {})
        system_config = config.get("system", {})
        self.orchestrator = Orchestrator(
            bus=self.bus,
            task_manager=self.task_manager,
            state_manager=self.state_manager,
            max_revision_cycles=system_config.get("max_revision_cycles", 3),
            fail_fast=workflow_config.get("fail_fast", False),
            require_review=workflow_config.get("require_review", True),
        )

    @classmethod
    def from_config_path(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Application":
        return cls(load_yaml(path))

    async def run_task(self, title: str, description: str):
        return await self.orchestrator.run(title, description)
