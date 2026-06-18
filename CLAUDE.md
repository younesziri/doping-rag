# doping-rag

RAG system over WADA anti-doping regulations (the Code, Prohibited List, ISTUE,
TUE guidelines) with a self-built, versioned evaluation harness. The focus is
evaluation rigor: a versioned eval dataset, retrieval-vs-generation metrics,
A/B experiments between strategies, and CI regression testing.

## Stack
- Python 3.12, managed with uv (lockfile committed).
- FastAPI · Qdrant (Docker) · OpenAI embeddings (text-embedding-3-small) ·
  Mistral generation (mistral-small-latest) · PyMuPDF · tiktoken.
- Quality gates: ruff + pre-commit + pytest.

## Layout
- `src/ingestion/` — PDF loading, cleaning, chunking.
- `src/retrieval/`, `src/generation/`, `src/evaluation/`, `src/api/`.
- `src/config.py` — pydantic-settings configuration.
- `data/raw/` — source PDFs (gitignored) + `sources.json` provenance manifest.
- `data/eval/` — versioned evaluation dataset.

## Commands
- Run a module: `uv run python -m src.<package>.<module>`
- Tests: `uv run pytest`
- Vector DB: `docker compose up -d` (Qdrant at localhost:6333)

## Conventions
- Conventional Commits, atomic commits.
- Configuration via environment / `.env` (never hardcoded); `.env.example` is the template.
- Decisions recorded in `DECISIONS.md`; experiments in `EXPERIMENTS.md`.
- Measure-first: a component is optimized only once the eval harness can score the change.
