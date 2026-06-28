# v2.4 Decision Policy Config

`config/v24_winner_decision_policy.yaml` enables cautious results-only `WINNER_LEAN` decisions while keeping `WINNER_PICK` without xG disabled by default.

`NO_DECISION` remains a valid model outcome when edge, confidence, source quality, or early-season risk are not strong enough.
