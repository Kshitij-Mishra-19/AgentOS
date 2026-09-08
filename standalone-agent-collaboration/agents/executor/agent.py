"""The Executor agent implementation."""

from __future__ import annotations

import json

from agents.executor.prompts import EXECUTOR_SYSTEM_PROMPT, build_execution_prompt
from core.agent import BaseAgent
from core.errors import MalformedAgentOutputError
from schemas.message import AgentMessage, MessageType
from schemas.result import ExecutionResult, ExecutionStatus


class ExecutorAgent(BaseAgent):
    """Executes an assigned subtask and returns a structured result.

    Never silently fails: any inability to complete the work is
    reported explicitly through ``ExecutionResult.status`` and
    ``errors``, and reflected in the reply message type
    (``EXECUTION_COMPLETED`` vs ``EXECUTION_FAILED``).
    """

    role = "executor"

    async def handle(self, message: AgentMessage) -> AgentMessage:
        if message.message_type != MessageType.TASK_ASSIGNED:
            raise MalformedAgentOutputError(
                f"ExecutorAgent cannot handle message_type={message.message_type.value}",
                details={"message_id": message.message_id},
            )

        self.validate_input(message, ["subtask_id", "title", "description"])
        subtask_id = message.payload["subtask_id"]
        title = message.payload["title"]
        description = message.payload["description"]

        self.log_event("info", "execution_started", message, subtask_id=subtask_id)

        prompt = build_execution_prompt(title, description)
        context = {
            "role": "executor",
            "subtask_title": title,
            "force_failure": bool(message.payload.get("force_failure", False)),
        }

        if self.llm_provider is None:
            raise MalformedAgentOutputError(
                "ExecutorAgent has no llm_provider configured", details={"agent_id": self.agent_id}
            )

        response = await self.llm_provider.complete(
            system=EXECUTOR_SYSTEM_PROMPT, prompt=prompt, context=context
        )

        try:
            result_data = json.loads(response.text)
            result_data.setdefault("task_id", subtask_id)
            result = ExecutionResult.from_dict(result_data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise MalformedAgentOutputError(
                f"Executor produced output that could not be parsed as an ExecutionResult: {exc}",
                details={"raw_response": response.text},
            ) from exc

        if result.status == ExecutionStatus.NEEDS_CLARIFICATION:
            self.log_event("warning", "clarification_requested", message, subtask_id=subtask_id)
            return self.build_reply(
                message,
                message_type=MessageType.CLARIFICATION_REQUESTED,
                payload={"result": result.to_dict()},
            )

        if result.status == ExecutionStatus.FAILED:
            self.log_event(
                "error", "execution_failed", message, subtask_id=subtask_id, errors=result.errors
            )
            return self.build_reply(
                message,
                message_type=MessageType.EXECUTION_FAILED,
                payload={"result": result.to_dict()},
            )

        self.log_event("info", "execution_completed", message, subtask_id=subtask_id)
        return self.build_reply(
            message,
            message_type=MessageType.EXECUTION_COMPLETED,
            payload={"result": result.to_dict()},
        )
