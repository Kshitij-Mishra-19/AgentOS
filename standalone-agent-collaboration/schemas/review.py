"""The structured review produced by the Reviewer agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReviewDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class ReviewCriterion:
    """A single evaluation criterion and whether the result satisfied it."""

    name: str
    passed: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "notes": self.notes}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewCriterion":
        return cls(name=data["name"], passed=bool(data["passed"]), notes=data.get("notes", ""))


@dataclass
class Review:
    """The Reviewer's structured output evaluating an ExecutionResult."""

    task_id: str
    decision: ReviewDecision
    score: float
    criteria: list[ReviewCriterion] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    feedback: str = ""
    required_changes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "decision": self.decision.value,
            "score": self.score,
            "criteria": [c.to_dict() for c in self.criteria],
            "issues": list(self.issues),
            "feedback": self.feedback,
            "required_changes": list(self.required_changes),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Review":
        return cls(
            task_id=data["task_id"],
            decision=ReviewDecision(data["decision"]),
            score=float(data.get("score", 0.0)),
            criteria=[ReviewCriterion.from_dict(c) for c in data.get("criteria", [])],
            issues=list(data.get("issues", [])),
            feedback=data.get("feedback", ""),
            required_changes=list(data.get("required_changes", [])),
        )
