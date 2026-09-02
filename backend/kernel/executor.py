from abc import ABC, abstractmethod
from datetime import datetime

from backend.kernel.agent import Agent
from backend.kernel.task import Task, TaskStatus


class TaskExecutor(ABC):

    @abstractmethod
    def execute(
        self,
        agent: Agent,
        task: Task
    ) -> Task:
        pass


class SimpleTaskExecutor(TaskExecutor):

    def execute(
        self,
        agent: Agent,
        task: Task
    ) -> Task:

        if agent.id != task.agent_id:
            raise ValueError(
                "Task is assigned to a different agent"
            )

        if agent.status.value not in {"ready", "running"}:
            raise RuntimeError(
                f"Agent cannot execute task from status: {agent.status}"
            )
        
        if task.status != TaskStatus.QUEUED:
            raise RuntimeError(
                f"Task cannot be executed from status: {task.status}"
            )

        try:
            # Task start time
            task.started_at = datetime.now()

            # Task is running
            task.status = TaskStatus.RUNNING

            # Simulated execution
            task.result = "Task completed successfully"

            # Task completed
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()

            return task

        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.completed_at = datetime.now()

            return task