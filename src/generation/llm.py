"""LLM generation  — the *provider seam*.

This module is the ONLY place that knows which provider we call. The RAG logic
in answer.py just calls `complete()`, so swapping OpenAI <-> Mistral for an A/B
experiment later is a one-function change here, not a rewrite. That's the whole
point of isolating it: the generation model becomes a variable the eval harness
can compare, not something baked through the codebase.
"""

from dataclasses import dataclass

from openai import OpenAI

from src.config import settings

# Our handle to openai's API. Like the OpenAI/Qdrant clients, constructing it
# only stores the key — no network call until we send a request. So importing
# this module is safe even with a placeholder key.
_client = OpenAI(api_key=settings.openai_api_key)


@dataclass
class LLMResponse:
    """The model's answer plus token usage (for cost tracking / the harness)."""

    text: str
    prompt_tokens: int
    completion_tokens: int


def complete(system: str, user: str, temperature: float = 0.0) -> LLMResponse:
    """Send a system + user prompt to the LLM and return the answer + token usage.

    Why temperature=0.0: I want the model to
    stick to the retrieved context, not get creative. Low temperature minimises
    variability and hallucination, and makes runs closer to reproducible (which
    matters once the harness starts scoring answers).

    `system` and `user` are the two halves of the prompt; answer.py builds them.
    This function stays dumb about their content,it just transports strings.
    """
    resp = _client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )

    # the llm returns a list of choices; for a single completion we take the first.
    text = resp.choices[0].message.content
    usage = resp.usage  # .prompt_tokens / .completion_tokens / .total_tokens

    return LLMResponse(
        text=text,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
    )
