# Evaluation Strategy

## Why evaluation is part of the architecture

Semantic segmentation can produce outputs that look plausible while still being structurally wrong.

NeuralMap therefore treats evaluation as a deployment gate, not as a cosmetic score.

## Development vs. blind evaluation

The private project separates:

- **development/calibration data** — allowed during iteration,
- **blind holdout data** — not used to tune the candidate policy.

Before blind evaluation, the selected policy is frozen and identified through immutable hashes.

Changing the policy after seeing holdout answers invalidates that holdout for future blind claims.

## Metrics

For macro activity-shift detection:

- **Precision** asks: when the system predicts a shift, how often is it correct?
- **Recall** asks: of all real shifts, how many did the system detect?
- **F1** balances the two.

A candidate can appear conservative and precise while still missing too many real boundaries.

## Example from the private project

One frozen policy produced:

| Metric | Result |
|---|---:|
| Precision | 0.750 |
| Recall | 0.286 |
| F1 | 0.414 |
| True positives | 6 |
| False positives | 2 |
| False negatives | 15 |

The policy was **rejected**.

That failure is intentionally disclosed because it demonstrates that the quality gate performed its job.

## Public demo evaluation

The public demo does not recreate the production benchmark.

Instead it includes unit tests for:

- source graph preservation,
- alternate branch handling,
- stable text-span provenance,
- deterministic exchange construction,
- expected synthetic boundary labels.
