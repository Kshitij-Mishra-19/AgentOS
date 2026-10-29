import os
from groq import Groq


def get_llm_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set. Add it to your .env file."
        )
    return Groq(api_key=api_key)


def call_llm(system_prompt: str, user_message: str, model: str = "qwen/qwen3.8-27b") -> str:
    client = get_llm_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=800,
    )
    return response.choices[0].message.content.strip()
