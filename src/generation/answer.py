"""Answer a question: retrieve context, prompt the LLM, return a cited answer.

This closes the weeks 1-2 baseline: question -> retrieve -> grounded, cited
answer (with abstention).

GRIND provided for you: the Answer result type and the __main__ CLI.
YOUR CONCEPTUAL CORE: the prompt (grounding + abstention + citations) and the
retrieve -> context -> generate -> assemble wiring, inside answer_question().
"""

from dataclasses import dataclass

from src.config import settings
from src.retrieval.search import RetrievedChunk
from src.retrieval.search import retrieve
from src.generation.llm import complete


@dataclass
class Answer:
    """A grounded answer plus the chunks it was built from (for citation) and cost."""

    text: str
    sources: list[RetrievedChunk]
    prompt_tokens: int
    completion_tokens: int


def answer_question(
    query: str,
    top_k: int = settings.top_k,
    version: str | None = None,
) -> Answer:
    """Retrieve context for `query`, prompt the LLM, and return a cited Answer."""

    hits = retrieve(query, top_k=top_k, version=version)

    context = ""
    for i, hit in enumerate(hits, start=1):
        context += f"\n[{i}] {hit.source} (v{hit.version}, pp. {hit.pages})\n{hit.text}\n"
    system = (
        "answer ONLY from the provided context, not prior knowledge; "
        "if the context doesn't contain the answer, say so plainly instead of guessing (high-stakes domain);"
        "cite the source(s) (e.g. [1], and the file · version · pages) backing each claim."
    )
    user = f"query:{query} , context;{context}"

    resp = complete(system, user)
    return Answer(
        text=resp.text,
        sources=hits,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
    )


if __name__ == "__main__":
    import sys

    default_q = "What is the sanction for a first anti-doping rule violation?"
    query = sys.argv[1] if len(sys.argv) > 1 else default_q

    ans = answer_question(query)
    print(f"Q: {query}\n")
    print(ans.text)
    print("\nSources:")
    for s in ans.sources:
        print(f"  - {s.source} v{s.version} pages={s.pages}  (score {s.score:.3f})")
    print(f"\ntokens: prompt={ans.prompt_tokens} completion={ans.completion_tokens}")
