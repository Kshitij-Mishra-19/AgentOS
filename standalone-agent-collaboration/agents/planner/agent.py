"""The Planner agent implementation."""

from __future__ import annotations

import json

from agents.planner.prompts import PLANNER_SYSTEM_PROMPT, build_planning_prompt
from core.agent import BaseAgent
from core.errors import MalformedAgentOutputError
from schemas.message import AgentMessage, MessageType
from schemas.plan import Plan


class PlannerAgent(BaseAgent):
    """Breaks a high-level task into a structured, dependency-ordered plan."""

    role = "planner"

    async def handle(self, message: AgentMessage) -> AgentMessage:
        if message.message_type not in (MessageType.TASK_CREATED, MessageType.REVISION_REQUESTED):
            raise MalformedAgentOutputError(
                f"PlannerAgent cannot handle message_type={message.message_type.value}",
                details={"message_id": message.message_id},
            )

        self.validate_input(message, ["title", "description"])
        title = message.payload["title"]
        description = message.payload["description"]
        revision_feedback = message.payload.get("feedback", "")

        self.log_event("info", "planning_started", message, title=title)

        prompt = build_planning_prompt(title, description, revision_feedback)
        context = {
            "role": "planner",
            "task_title": title,
            "revision_notes": revision_feedback,
        }

        if self.llm_provider is None:
            raise MalformedAgentOutputError(
                "PlannerAgent has no llm_provider configured", details={"agent_id": self.agent_id}
            )

        response = await self.llm_provider.complete(
            system=PLANNER_SYSTEM_PROMPT, prompt=prompt, context=context
        )

        try:
            plan_data = json.loads(response.text)
            plan = Plan.from_dict(plan_data)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise MalformedAgentOutputError(
                f"Planner produced output that could not be parsed as a Plan: {exc}",
                details={"raw_response": response.text},
            ) from exc

        max_subtasks = self.config.get("planning", {}).get("max_subtasks")
        if max_subtasks and len(plan.subtasks) > max_subtasks:
            plan.subtasks = plan.subtasks[:max_subtasks]
            plan.execution_order = [st.subtask_id for st in plan.subtasks]

        problems = plan.validate()
        if problems:
            raise MalformedAgentOutputError(
                "Planner produced an invalid plan.",
                details={"problems": problems},
            )

        self.log_event(
            "info",
            "plan_generated",
            message,
            subtask_count=len(plan.subtasks),
        )

        return self.build_reply(
            message,
            message_type=MessageType.PLAN_CREATED,
            payload={"plan": plan.to_dict()},
        )
