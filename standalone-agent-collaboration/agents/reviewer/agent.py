"""The Reviewer agent implementation."""

from __future__ import annotations

import json

from agents.reviewer.prompts import REVIEWER_SYSTEM_PROMPT, build_review_prompt
from core.agent import BaseAgent
from core.errors import MalformedAgentOutputError, ReviewerFailureError
from schemas.message import AgentMessage, MessageType
from schemas.result import ExecutionResult
from schemas.review import Review, ReviewDecision


class ReviewerAgent(BaseAgent):
    """Validates Executor output against the original task and renders a decision."""

    role = "reviewer"

    async def handle(self, message: AgentMessage) -> AgentMessage:
        if message.message_type != MessageType.REVIEW_REQUESTED:
            raise MalformedAgentOutputError(
                f"ReviewerAgent cannot handle message_type={message.message_type.value}",
                details={"message_id": message.message_id},
            )

        self.validate_input(
            message, ["original_title", "original_description", "result"]
        )
        original_title = message.payload["original_title"]
        original_description = message.payload["original_description"]

        try:
            result = ExecutionResult.from_dict(message.payload["result"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ReviewerFailureError(
                f"Reviewer could not parse ExecutionResult from payload: {exc}"
            ) from exc

        self.log_event("info", "review_started", message, subtask_id=result.task_id)

        prompt = build_review_prompt(
            original_title,
            original_description,
            result.summary,
            result.output,
            result.errors,
        )
        context = {
            "role": "reviewer",
            "has_errors": bool(result.errors),
            "force_reject": bool(message.payload.get("force_reject", False)),
        }

        if self.llm_provider is None:
            raise MalformedAgentOutputError(
                "ReviewerAgent has no llm_provider configured", details={"agent_id": self.agent_id}
            )

        response = await self.llm_provider.complete(
            system=REVIEWER_SYSTEM_PROMPT, prompt=prompt, context=context
        )

        try:
            review_data = json.loads(response.text)
            review_data.setdefault("task_id", result.task_id)
            review = Review.from_dict(review_data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise MalformedAgentOutputError(
                f"Reviewer produced output that could not be parsed as a Review: {exc}",
                details={"raw_response": response.text},
            ) from exc

        reject_on_any_error = self.config.get("review", {}).get("reject_on_any_error", True)
        if reject_on_any_error and result.errors and review.decision == ReviewDecision.APPROVED:
            # Guard-rail: never let the underlying provider approve a result
            # that self-reported errors, regardless of what it returned.
            review.decision = ReviewDecision.REJECTED
            review.issues.append("Executor reported errors; auto-rejected by policy.")
            review.required_changes.append("Re-run the subtask and resolve the reported errors.")

        message_type = (
            MessageType.REVIEW_APPROVED
            if review.decision == ReviewDecision.APPROVED
            else MessageType.REVIEW_REJECTED
        )

        self.log_event(
            "info",
            "review_decision",
            message,
            subtask_id=result.task_id,
            decision=review.decision.value,
            score=review.score,
        )

        return self.build_reply(
            message,
            message_type=message_type,
            payload={"review": review.to_dict()},
        )
