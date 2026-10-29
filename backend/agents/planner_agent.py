import json
from .base_agent import call_llm

SYSTEM_PROMPT = """You are a Planning Agent. Break down a user's goal into sequential tasks for specialized agents.

Available agents:
- research: For researching topics, gathering information, understanding requirements
- coding: For writing code, implementing features, building solutions
- testing: For writing tests, validating code, quality assurance

Respond ONLY with a valid JSON array. Each item must have:
- "name": short descriptive task name
- "agent_type": one of "research", "coding", or "testing"
- "priority": one of "HIGH", "MEDIUM", or "LOW"

Example:
[
  {"name": "Research authentication best practices", "agent_type": "research", "priority": "HIGH"},
  {"name": "Implement JWT authentication", "agent_type": "coding", "priority": "HIGH"},
  {"name": "Write auth unit tests", "agent_type": "testing", "priority": "MEDIUM"}
]

Keep it minimal — only include steps that are truly needed."""


class PlannerAgent:

    def plan(self, goal: str) -> list[dict]:
        print(f"[PlannerAgent] Planning goal: {goal}")
        raw = call_llm(SYSTEM_PROMPT, f"Goal: {goal}")

        raw = raw.strip()

        # Strip <think>...</think> blocks (qwen reasoning model)
        import re
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        # Strip markdown code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        # Extract first JSON array found
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start != -1 and end > start:
            raw = raw[start:end]

        tasks = json.loads(raw)
        print(f"[PlannerAgent] Created {len(tasks)} tasks.")
        return tasks
