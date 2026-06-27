# v2.3 Results-Only Prediction Tier

`TIER_2_RESULTS_ONLY` is used when football-data style results/form data is available but xG is unavailable.

The winner model still creates 1X2 probabilities from results/form features. Confidence is capped, and the decision policy may return `NO_DECISION`, `NO_CLEAR_WINNER`, or `WINNER_LEAN`.

`WINNER_PICK` is not forced by this tier. The goal is eligibility correctness, not more aggressive recommendations.

Missing odds remain optional and are treated as risk context, not a hard block.
