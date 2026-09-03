from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from .enums import JobStatus, PriorityLevel


@dataclass                #automatically make constructor of Job class no need to write __init__()
class Job:
    name: str
    agent_type: str

    priority: PriorityLevel = PriorityLevel.HIGH        #default priority 
    dependencies: list[str] = field(default_factory=list)    # if dependencies are not given then make an empty list

    job_id: str = field(default_factory=lambda: str(uuid4()))       #automatically assigning unique id to jo
    status: JobStatus = JobStatus.PENDING                   #default state

    created_at: datetime = field(default_factory=datetime.utcnow)  
    #create job +save current time