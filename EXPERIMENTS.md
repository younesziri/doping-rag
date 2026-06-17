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

## Run log

(empty until the harness produces its first report)