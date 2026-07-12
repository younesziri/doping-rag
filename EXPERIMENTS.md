# Experiments

## Backlog — hypotheses I want to test once the eval harness exists

- **H1 — Block extraction for the Prohibited List.** Flat extraction currently
  displaces section headings from their substance lists and mislabels drug
  classes (I saw Tamoxifen fall under "S4.1 Aromatase Inhibitors"). Hypothesis:
  if I switch to coordinate-aware extraction and bind each heading to the
  substances beneath it, I'll fix the class-attribution errors and raise
  answer-correctness on "what class is X?" questions.
- **H2 — Footnote handling (Code).** Footnote markers glue onto words
  ("justification.13") and the footnote text dumps at the bottom of the page,
  detached from the article it explains. Hypothesis: reattaching each comment to
  its article instead of dropping it changes retrieval on interpretive questions.
- **H3 — Structure-aware chunking (Code).** Hypothesis: chunking on
  `Article x.y.z` boundaries instead of fixed 512-token windows improves
  retrieval precision, because I stop splitting articles in half.
- **H4 — Residual furniture (minor).** Per-section sidebar labels slip through my
  frequency-based cleaning, and the bullet delimiter isn't consistent (`• \t` vs
  `• `). I want to measure whether these actually hurt before spending time on
  them.
- **H5 — Embedding model A/B (retriever quality vs cost).** My baseline is OpenAI
  `text-embedding-3-small` (1536-dim). Hypothesis: `text-embedding-3-large`
  (3072-dim, ~6.5× the cost) and/or a local model (BGE — free, but a different
  dimension and CPU latency) change recall@k. I want to measure whether the gain
  justifies the cost/latency before upgrading the embedder..
- **H6 — Generation provider A/B (via `complete()` ).** I generate with
  OpenAI `gpt-4o-mini`. Hypothesis: swapping to Mistral `mistral-small-latest` moves faithfulness,
  answer-correctness, and cost-per-query. This turns "which LLM generates" into a
  measured choice instead of a default.
- **H7 — Version filtering strategy.** Retrieval takes `version` as an explicit
  parameter today (no query parsing). Hypothesis: on version-sensitive questions
  (2021↔2027 Code, 2025↔2026 List), filtering by `version` raises correctness and
  avoids near-duplicate confusion versus no filter — while an LLM "self-query"
  that extracts the version from the question adds recall but also a new failure
  mode (a wrong filter silently excludes the answer). Three arms: no filter /
  explicit filter / LLM-extracted filter.
- **H8 — Retrieval-score threshold for abstention.** On an out-of-corpus probe
  the top similarity scores collapsed (~0.10 vs 0.6+ for
  in-corpus questions). Hypothesis: abstaining when the top (or mean top-k) score
  is below a threshold cuts hallucinations without hurting the in-corpus answer
  rate ,, a cheap retrieval-confidence signal layered on top of the prompt-based
  abstention.
- **H9 — Cross-encoder reranking.** Hypothesis: reranking the top-k dense hits
  with a cross-encoder improves precision@k / MRR (moving the truly-relevant
  chunk to rank 1), at the cost of extra latency. Already in the plan;
  logging it here so it's measured, 

## Run log

### 2026-07-12 — Pre-harness observation from eval-set annotation: realistic phrasing collapses the abstention score gap (reframes H8)

While hand-labeling the eval set, I ran the annotation helper (top-8 retrieval)
over 50 clean-room questions phrased like real users (lay / informed /
misconception / niche), and the retrieval-confidence signal H8 leans on did not
hold:

- My earlier out-of-corpus probe was phrased like the regulation and separated
  cleanly — in-corpus ~0.76 vs out-of-corpus ~0.10.
- Lay-phrased real questions compress the whole cosine range: in-corpus top-1
  landed ~0.45–0.68, while genuinely out-of-corpus questions landed ~0.39–0.47
  (e.g. "how does the biological passport work" and whereabouts mechanics — both
  governed by International Standards I never indexed). The bands overlap.

Implication for H8: a single global score threshold is probably infeasible once
queries are realistic — set it high and I over-abstain on real users, set it low
and I still answer out-of-corpus questions (hallucinate). The clean 0.10-vs-0.6
separation was an artifact of corpus-vocabulary phrasing — the same
question-phrasing bias I control for by tagging each eval row with its `source`.

Revised H8 to measure once recall@k / MRR exist: does a *relative* confidence
signal beat an absolute cutoff — e.g. the score gap between rank 1 and rank k, or
top-1 minus the mean of the tail?

Second observation (labeling, not scoring): retrieval score cannot auto-label
answerability. "Biological passport" scored 0.442 — not obviously low — yet is
out-of-corpus; only reading the retrieved text (all merely adjacent) reveals
nothing answers it. So gold/answerable labeling stays manual.

Caveat: these are single-run top-1 similarity reads from the annotation pass, not
metrics from a harness report — directional signal, n≈50, no confidence interval
yet.