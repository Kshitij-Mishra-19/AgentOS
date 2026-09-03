from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class AgentStatus(str, Enum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class Agent:
    name: str
    agent_type: str

    id: str = field(default_factory=lambda: str(uuid4()))

    status: AgentStatus = AgentStatus.CREATED

    capabilities: list[str] = field(default_factory=list)

    def mark_ready(self):
        self.status = AgentStatus.READY

    def start(self):
        if self.status != AgentStatus.READY:
            raise RuntimeError(
                f"Agent cannot start from status: {self.status}"
            )

        self.status = AgentStatus.RUNNING

    def pause(self):
        if self.status != AgentStatus.RUNNING:
            raise RuntimeError(
                f"Agent cannot pause from status: {self.status}"
            )

        self.status = AgentStatus.PAUSED

    def resume(self):
        if self.status != AgentStatus.PAUSED:
            raise RuntimeError(
                f"Agent cannot resume from status: {self.status}"
            )

        self.status = AgentStatus.RUNNING

    def stop(self):
        if self.status not in {
            AgentStatus.RUNNING,
            AgentStatus.PAUSED,
            AgentStatus.READY,
        }:
            raise RuntimeError(
                f"Agent cannot stop from status: {self.status}"
            )

        self.status = AgentStatus.STOPPED

    def __post_init__(self):

        if not isinstance(self.name, str):
            raise TypeError("Agent name must be a string")

        if not self.name.strip():
            raise ValueError("Agent name cannot be empty")

        if not isinstance(self.agent_type, str):
            raise TypeError("Agent type must be a string")

        if not self.agent_type.strip():
            raise ValueError("Agent type cannot be empty")

        if not isinstance(self.capabilities, list):
            raise TypeError("Agent capabilities must be a list")

        if not all(isinstance(capability, str) for capability in self.capabilities):
            raise TypeError("Agent capabilities must contain only strings")

    def fail(self):
        self.status = AgentStatus.FAILED