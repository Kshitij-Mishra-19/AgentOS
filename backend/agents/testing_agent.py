from .base_agent import call_llm

SYSTEM_PROMPT = """You are a Testing Agent. Write concise pytest tests.
Cover the main functionality and one edge case.
Use markdown code blocks. Max 300 words."""


class TestingAgent:

    def run(self, task: str) -> str:
        print(f"[TestingAgent] Writing tests for: {task}")
        result = call_llm(SYSTEM_PROMPT, f"Write tests for: {task}")
        print(f"[TestingAgent] Done.")
        return result
