from .base_agent import call_llm

SYSTEM_PROMPT = """You are a Research Agent. Research the given topic and provide:
- Key findings (3-5 bullet points)
- Important considerations
- Recommended approach

Be concise. Max 300 words."""


class ResearchAgent:

    def run(self, task: str) -> str:
        print(f"[ResearchAgent] Researching: {task}")
        result = call_llm(SYSTEM_PROMPT, f"Research task: {task}")
        print(f"[ResearchAgent] Done.")
        return result
