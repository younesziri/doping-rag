# Decision Log

Format: each entry records the decision, the reasoning, and the tradeoff accepted.

---

## 001 — English-only corpus (2026-06-12)

**Decision:** Build the corpus and the entire pipeline (prompts, eval dataset,
documentation) in English only.

**Reasoning:** The WADA ecosystem is English-first — the Code, the Prohibited
List, TUE guidelines and CAS decisions all designate English as the
authoritative version. Working in English removes multilingual embedding
quality as a confounding variable in retrieval experiments, and the README
and write-up target an English-speaking recruiter audience anyway.

**Tradeoff accepted:** I lose the French drug-name → active-substance mapping
subplot (e.g. "Ventoline" → salbutamol via the French public drug database).
Could be reintroduced later as a stretch experiment with a multilingual
embedding model.

---

## 002 — Initial stack (2026-06-12)

| Layer | Choice | Justification |
|---|---|---|
| Package manager | uv | Lockfile-based, fully reproducible env for CI and anyone cloning the repo |
| API framework | FastAPI | Async, typed, auto-generated OpenAPI docs; industry standard |
| Vector DB | Qdrant (Docker) | Payload filtering needed for version-aware retrieval (e.g. "2026 list only") |
| Embeddings | OpenAI text-embedding-3-small | ~$0.02/M tokens — negligible cost; strong baseline. Local model (BGE) to be tested later as a measured experiment |
| LLM | Mistral API (mistral-small-latest) | Cheap, capable; OpenAI key kept as fallback |
| PDF parsing | PyMuPDF | Fast and reliable baseline; will escalate to Docling only if tables prove problematic |
| Lint/format | ruff + pre-commit | Quality gates installed before any code exists, so they never need retrofitting |
| Tests | pytest | Standard; smoke test in place so CI starts green in week 7 |

**Deliberate non-choices:**
- **No LangChain/LlamaIndex.** Retrieval logic is ~200 lines I want to
  understand and defend end-to-end. Frameworks would be evaluated for a
  production setting.
- **No cloud deployment until week 7.** Local-first keeps iteration fast and
  free during the experimentation phase.


===
## 003 — Corpus inclusion policy (2026-06-16)

**Decision:** The corpus contains only clean-text, English, currently-in-force
versions of WADA documents, plus the clean future versions (2027) where they
already exist. Excluded: redline / tracked-changes documents, non-English
translations, and short "explanatory notes" summaries.

**Reasoning:**
- *Clean text only.* Redline documents interleave old and new wording with
  strikethroughs and insertion marks. PyMuPDF extracts that as overlapping,
  self-contradicting text that would corrupt chunks and degrade retrieval.
  They are human diff artifacts, not source documents.
- *In-force + future versions, deliberately.* A real query is answered against
  the version in force on a given date, so the in-force versions are the
  baseline. The future versions are included on purpose to create the version
  axes (2025↔2026 List, 2021↔2027 Code, 2023↔2027 ISTUE) that motivate
  version-aware retrieval later.
- *English-only* follows decision 001 and matches WADA's authoritative texts.
- *Explanatory notes excluded* as supplementary and non-authoritative.

**Tradeoff accepted:** Including two versions of several documents injects
near-duplicate content into the corpus. This is intentional — it's the
retrieval difficulty I want — but it forces a hard requirement: every chunk
must carry a `version` (year) field in its Qdrant payload from day one, or
retrieval will conflate years and return the wrong edition. I also forgo the
redlines as a potential source of structured version-diff metadata, which
could be reintroduced later as a stretch feature.