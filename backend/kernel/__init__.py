from .executor import SimpleTaskExecutor
from .registry import AgentRegistry

def __init__(self):
    
    self.status = "initialized"
    self.registry = AgentRegistry()
    self.executor = SimpleTaskExecutor()