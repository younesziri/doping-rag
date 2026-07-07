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

======

## 004 — Baseline ingestion & parsing approach (2026-06-17)

**Decision:** For the weeks 1–2 baseline I'm parsing every document with flat
`get_text()` extraction plus content-based cleanup (frequency-detected running
headers + page-number removal), then fixed-size chunking. I'm deliberately not
building coordinate-aware extraction for the Prohibited List yet, even though I
can already see it needs it.

**Reasoning:**
- Reading the raw extraction, I found two very different document profiles. The
  Code is single-column prose and its `Article 4.x` numbering survives
  extraction cleanly, so I can eventually chunk it on article boundaries. The
  Prohibited List is multi-column, and flat extraction pulls its section
  headings out of order relative to the substance lists, so a substance can land
  under the wrong class. I confirmed it on a real page: Tamoxifen — a SERM,
  class S4.2 — comes out under the "S4.1 Aromatase Inhibitors" heading. If I
  chunked that naively, my system would confidently answer that Tamoxifen is an
  aromatase inhibitor, which is wrong.
- I know the fix is coordinate-aware extraction (`get_text("blocks")`, sort by
  position, bind each heading to the substances beneath it). I'm choosing not to
  do it now, because I can't justify the change until I can measure it and I
  don't have the eval harness yet. Fixing the parser before I can score it is
  exactly the mistake this project is built to avoid.
- I strip headers by how often a line repeats across pages rather than matching
  a hardcoded title, so the cleaner generalizes to any WADA document. Page
  numbers change every page, so frequency can't catch them — I remove those with
  a separate digit filter. Two mechanisms, two jobs.

**Tradeoff accepted:** My baseline knowingly carries garbage — displaced
headings on the List, surviving sidebar labels, footnotes detached from their
article. I've logged each as a hypothesis in EXPERIMENTS.md so I can fix them as
measured experiments later and show the metric actually moved.

---

## 005 — Fixed-size token chunking (baseline) (2026-06-21)

**Decision:** I turn the cleaned pages into fixed-size chunks of 512 tokens with
64 tokens of overlap, tokenized with the embedding model's own encoding
(`cl100k_base`, derived from the model name so it can't silently drift). Each
chunk carries its `source`, `version`, page span, and a deterministic id
(`{source}::{i}`). The `version` is read from the `sources.json` manifest, not
parsed from the filename.

**Reasoning:**
- I size in tokens, not characters, because the embedding model has a token
  budget and counts in tokens — so "512" means the same thing to me and to the
  model. Using the model's exact encoding keeps that equivalence honest.
- The 64-token overlap is insurance against a fixed window slicing an idea in
  half: the cut idea still appears whole in the neighbouring chunk. I can put a
  number on the cost — on the Code, overlap turned 143 chunks into 163 (~14%
  more), i.e. ~14% more embedding spend.
- I track each token's page of origin so a chunk records its true page span,
  which I'll need for citations. A naive "join all pages then slice" throws that
  mapping away; I also insert a separator between pages so words don't glue
  across the boundary.
- The manifest is the single source of truth for per-document metadata, so the
  version is read there rather than re-derived from the filename.
- Fixed chunking is deliberately the *baseline*. I can't justify structure-aware
  chunking on `Article x.y.z` boundaries until the harness shows where fixed
  chunking fails (logged as H3).

**Tradeoff accepted:** Overlap inflates the chunk count and embedding cost by
~14%. Fixed windows also cut articles mid-thought, and the chunker faithfully
embeds whatever the parser hands it — including the List's displaced headings and
table-of-contents noise. I keep these as measured experiments (H1, H3) rather
than fixing them blind.

---

## 006 — Embedding, vector store, and top-k retrieval (baseline) (2026-07-03)

**Decision:** I embed every chunk with OpenAI `text-embedding-3-small` (1536-dim),
batching by the request token budget, and upsert one point per chunk into a
single Qdrant collection `doping_chunks` (size 1536, cosine). Each point's
payload carries `source`, `version`, `pages`, `text`, and the original
`chunk_id`. Point ids are a deterministic `uuid5(namespace, chunk_id)`. Ingest
upserts with `wait=True`. Retrieval embeds the query with the *same* function,
runs a top-k `query_points`, and takes an optional `version` as a parameter that
becomes a Qdrant payload filter. All of it is hand-written — no retrieval
framework.

**Reasoning:**
- *One shared embedding function for ingest and query.* Documents and the query
  must be embedded by the same model, or they live in different coordinate
  systems and nearest-neighbour is meaningless. Keeping embedding in one module
  enforces that symmetry structurally.
- *Cosine + size 1536, derived from the model.* Text embeddings encode meaning in
  direction and OpenAI's vectors are unit-normalised, so cosine is the natural
  metric. The collection size is imported from the embedding module (`EMBED_DIM`),
  so the store's geometry is coupled to the model — swapping models forces a
  rebuild, which is correct.
- *One collection + a `version` payload filter, not one collection per version.*
  Payload filtering is the reason I chose Qdrant. One collection filtered on
  `version` beats juggling many collections and stitching results, and it's the
  mechanism the whole version-axis corpus was built for. The retriever takes
  `version` as a parameter — it does not parse the query. Deriving the version
  from natural language (regex or an LLM self-query) is a separate concern with
  its own failure modes, gated behind the eval harness.
- *Chunk text lives in the payload.* Embeddings are irreversible — I can't
  recover text from a vector — so the point stores its text. The vector finds the
  chunk; the payload text is what I feed the generator and cite. Inline payload
  keeps retrieval to a single round-trip.
- *Deterministic `uuid5` ids for idempotency.* Qdrant ids must be an unsigned int
  or a UUID, but my `chunk_id` is a string. `uuid5(namespace, chunk_id)` hashes
  it to a stable UUID, so re-ingesting overwrites in place instead of
  duplicating. `uuid4` would duplicate the corpus on every run.
- *`wait=True` on ingest* gives read-your-writes: the points are searchable the
  moment the upsert returns, so an ingest-then-search script can't read an empty
  store.

**Verified:** 163 points in the collection (size 1536, cosine). OpenAI billed
83,164 tokens vs my tiktoken estimate of ~83,130 — a 0.04% gap that confirms my
chunker and the embedding model share the `cl100k_base` encoding. Re-ingesting
with `recreate=False` kept the count at 163, so idempotency holds. Cost for the
Code: ~$0.0017.

**Tradeoff accepted:** At this scale Qdrant serves *exact* (brute-force) search —
the HNSW / approximate-NN recall tradeoff only appears once the collection passes
the indexing threshold (~20k vectors), so my baseline recall is effectively
perfect and I haven't stress-tested ANN yet. Inline payload stores all chunk text
inside Qdrant (fine now; on-disk payload or store-by-reference if RAM bites
later). I stay on OpenAI embeddings for the baseline and keep a local model (BGE)
as a measured weeks-5–6 experiment, since switching now would change the
embedding dimension and force a rebuild before the harness can score it.


## 007 — Generation provider: OpenAI gpt-4o-mini (code default), Mistral deferred (2026-07-07)

**Decision:** I generate answers with OpenAI `gpt-4o-mini` and made it the code
default, superseding the Mistral choice in 002. Mistral becomes a deferred,
measured provider A/B.

**Reasoning:** The provider sits behind a one-function `complete()` seam, so the
specific choice is low-stakes

---

## 008 — Enforce abstention rather than always answer (2026-07-07)

**Decision:** The system prompt instructs the model to refuse — to say the context
doesn't contain the answer — when the retrieved chunks don't support one, instead
of always producing an answer.

**Reasoning:** High-stakes domain: a confident wrong answer about an athlete's
eligibility can end a career, so an honest "I don't know" is safer than a
fabricated answer grounded in nothing.

**Tradeoff accepted:** I'll get false refusals — the model may abstain even when
the answer was actually in the retrieved context which I accept over
hallucination. Both the false-abstention rate and the hallucination rate will
measured later in he harness.