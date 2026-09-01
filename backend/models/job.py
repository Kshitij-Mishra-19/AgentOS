from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from .enums import JobStatus, PriorityLevel


@dataclass
class Job:
    name: str
    agent_type: str

    priority: PriorityLevel = PriorityLevel.HIGH
    dependencies: list[str] = field(default_factory=list)

    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.PENDING

    created_at: datetime = field(default_factory=datetime.utcnow)