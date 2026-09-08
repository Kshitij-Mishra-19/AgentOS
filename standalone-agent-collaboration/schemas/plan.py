"""The structured plan produced by the Planner agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Subtask:
    """A single unit of planned work, assigned to one agent role."""

    subtask_id: str
    title: str
    description: str
    assigned_role: str = "executor"
    depends_on: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subtask_id": self.subtask_id,
            "title": self.title,
            "description": self.description,
            "assigned_role": self.assigned_role,
            "depends_on": list(self.depends_on),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Subtask":
        return cls(
            subtask_id=data["subtask_id"],
            title=data["title"],
            description=data["description"],
            assigned_role=data.get("assigned_role", "executor"),
            depends_on=list(data.get("depends_on", [])),
        )


@dataclass
class Plan:
    """The Planner's structured output: how a task should be broken down."""

    goal: str
    subtasks: list[Subtask] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    execution_order: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    revision_notes: str = ""

    def validate(self) -> list[str]:
        """Return a list of validation problems (empty means the plan is valid)."""
        problems: list[str] = []
        if not self.goal.strip():
            problems.append("Plan is missing a goal.")
        if not self.subtasks:
            problems.append("Plan has no subtasks.")

        subtask_ids = {st.subtask_id for st in self.subtasks}
        for st in self.subtasks:
            for dep in st.depends_on:
                if dep not in subtask_ids:
                    problems.append(
                        f"Subtask {st.subtask_id} depends on unknown subtask {dep}."
                    )

        if self.execution_order:
            missing_from_order = subtask_ids - set(self.execution_order)
            if missing_from_order:
                problems.append(
                    f"execution_order is missing subtasks: {sorted(missing_from_order)}"
                )
        return problems

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "dependencies": {k: list(v) for k, v in self.dependencies.items()},
            "execution_order": list(self.execution_order),
            "success_criteria": list(self.success_criteria),
            "risks": list(self.risks),
            "revision_notes": self.revision_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        return cls(
            goal=data["goal"],
            subtasks=[Subtask.from_dict(st) for st in data.get("subtasks", [])],
            dependencies={k: list(v) for k, v in data.get("dependencies", {}).items()},
            execution_order=list(data.get("execution_order", [])),
            success_criteria=list(data.get("success_criteria", [])),
            risks=list(data.get("risks", [])),
            revision_notes=data.get("revision_notes", ""),
        )
