from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PriorityLevel(int, Enum):
    HIGH = 0
    MEDIUM = 1
    LOW = 2