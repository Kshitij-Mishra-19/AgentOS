from .base_agent import call_llm

SYSTEM_PROMPT = """You are a Coding Agent. Write clean, working code.
Provide a concise implementation with brief explanation.
Use markdown code blocks. Max 400 words. Focus on the core logic only."""


class CodingAgent:

    def run(self, task: str) -> str:
        print(f"[CodingAgent] Implementing: {task}")
        result = call_llm(SYSTEM_PROMPT, f"Coding task: {task}")
        print(f"[CodingAgent] Done.")
        return result
