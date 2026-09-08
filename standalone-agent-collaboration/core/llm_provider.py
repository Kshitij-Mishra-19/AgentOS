"""LLM provider abstraction.

Agents never call a specific LLM vendor's SDK directly. They depend on
the small ``LLMProvider`` interface below, which the orchestrator wires
up at startup based on configuration. This means:

- The whole system runs locally, offline, and deterministically using
  ``MockLLMProvider`` -- no paid API required for development or tests.
- A real provider can be plugged in later by implementing the same
  interface (see ``RealLLMProvider`` for the adapter shape) without
  touching any agent code.
"""

from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMResponse:
    """A normalized response from any provider."""

    text: str
    raw: dict[str, Any]


class LLMProvider(ABC):
    """Common interface every provider (mock or real) must implement."""

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> LLMResponse:
        """Return a completion for ``prompt`` given a ``system`` instruction and context."""


class MockLLMProvider(LLMProvider):
    """A deterministic, offline stand-in for a real LLM.

    Instead of calling out to a network service, this provider applies
    small rule-based generators keyed by content in the prompt/context,
    so behavior is reproducible across runs -- which is what makes the
    test suite and the example script runnable without any external
    service or API key.
    """

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> LLMResponse:
        context = context or {}
        role = context.get("role", "generic")
        seed = self._seed(system, prompt, context)

        if role == "planner":
            text = self._plan_response(prompt, context, seed)
        elif role == "executor":
            text = self._execution_response(prompt, context, seed)
        elif role == "reviewer":
            text = self._review_response(prompt, context, seed)
        else:
            text = json.dumps({"message": "mock response", "seed": seed})

        return LLMResponse(text=text, raw={"system": system, "prompt": prompt, "seed": seed})

    @staticmethod
    def _seed(system: str, prompt: str, context: dict[str, Any]) -> str:
        digest = hashlib.sha256((system + prompt + json.dumps(context, sort_keys=True, default=str)).encode())
        return digest.hexdigest()[:12]

    @staticmethod
    def _plan_response(prompt: str, context: dict[str, Any], seed: str) -> str:
        task_title = context.get("task_title", "the task")
        revision_notes = context.get("revision_notes", "")
        subtasks = [
            {
                "subtask_id": "subtask-1",
                "title": f"Research and scope: {task_title}",
                "description": f"Gather requirements and constraints for '{task_title}'.",
                "assigned_role": "executor",
                "depends_on": [],
            },
            {
                "subtask_id": "subtask-2",
                "title": f"Produce core deliverable for: {task_title}",
                "description": f"Create the main output needed to satisfy '{task_title}'.",
                "assigned_role": "executor",
                "depends_on": ["subtask-1"],
            },
            {
                "subtask_id": "subtask-3",
                "title": "Summarize and finalize",
                "description": "Compile results into a final structured summary.",
                "assigned_role": "executor",
                "depends_on": ["subtask-2"],
            },
        ]
        plan = {
            "goal": task_title,
            "subtasks": subtasks,
            "dependencies": {st["subtask_id"]: st["depends_on"] for st in subtasks},
            "execution_order": [st["subtask_id"] for st in subtasks],
            "success_criteria": [
                f"All subtasks for '{task_title}' are completed",
                "Output directly addresses the original task description",
            ],
            "risks": ["Ambiguous requirements may require clarification from the Executor."],
            "revision_notes": revision_notes,
        }
        return json.dumps(plan)

    @staticmethod
    def _execution_response(prompt: str, context: dict[str, Any], seed: str) -> str:
        subtask_title = context.get("subtask_title", "subtask")
        force_failure = bool(context.get("force_failure", False))
        if force_failure:
            result = {
                "status": "FAILED",
                "summary": f"Could not complete '{subtask_title}'.",
                "output": {},
                "artifacts": [],
                "errors": ["Simulated executor failure for testing."],
                "metadata": {"seed": seed},
            }
        else:
            result = {
                "status": "SUCCESS",
                "summary": f"Completed '{subtask_title}'.",
                "output": {
                    "content": f"Result for {subtask_title} (ref {seed})",
                    "steps_taken": [
                        f"Analyzed requirements for {subtask_title}",
                        "Produced structured output",
                    ],
                },
                "artifacts": [f"{subtask_title.lower().replace(' ', '_')}.md"],
                "errors": [],
                "metadata": {"seed": seed},
            }
        return json.dumps(result)

    @staticmethod
    def _review_response(prompt: str, context: dict[str, Any], seed: str) -> str:
        force_reject = bool(context.get("force_reject", False))
        has_errors = bool(context.get("has_errors", False))
        should_reject = force_reject or has_errors

        criteria = [
            {"name": "addresses_original_task", "passed": not should_reject, "notes": ""},
            {"name": "no_reported_errors", "passed": not has_errors, "notes": ""},
            {"name": "structured_output_present", "passed": True, "notes": ""},
        ]
        review = {
            "decision": "REJECTED" if should_reject else "APPROVED",
            "score": 0.4 if should_reject else 0.95,
            "criteria": criteria,
            "issues": ["Output did not fully satisfy requirements."] if should_reject else [],
            "feedback": (
                "Please address the missing requirements and resubmit."
                if should_reject
                else "Meets all requirements."
            ),
            "required_changes": (
                ["Re-run the failed subtask and include a complete output."]
                if should_reject
                else []
            ),
        }
        return json.dumps(review)


class RealLLMProvider(LLMProvider):
    """Adapter skeleton for a real LLM vendor.

    Not wired up by default -- no network calls happen unless a
    concrete subclass fills in ``complete``. This class exists so
    swapping the mock for a live provider is a one-line change in
    configuration rather than a rewrite of agent code.

    Example of how a concrete subclass might look (left unimplemented
    to avoid any hard dependency on a specific vendor SDK):

        class AnthropicLLMProvider(RealLLMProvider):
            def __init__(self, model: str = "claude-sonnet-4-6"):
                self.model = model
                self.api_key = os.environ["LLM_API_KEY"]

            async def complete(self, *, system, prompt, context=None):
                ...  # call the vendor SDK/HTTP API here
    """

    def __init__(self, api_key_env_var: str = "LLM_API_KEY") -> None:
        self.api_key_env_var = api_key_env_var

    async def complete(
        self,
        *,
        system: str,
        prompt: str,
        context: Optional[dict[str, Any]] = None,
    ) -> LLMResponse:
        api_key = os.environ.get(self.api_key_env_var)
        if not api_key:
            raise RuntimeError(
                f"RealLLMProvider requires the {self.api_key_env_var} environment variable "
                "to be set, and a concrete subclass implementing `complete`."
            )
        raise NotImplementedError(
            "RealLLMProvider is an adapter skeleton. Implement `complete` in a subclass "
            "that calls your chosen LLM vendor's API."
        )
