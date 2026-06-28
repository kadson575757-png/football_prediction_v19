# v2.6 As-Of Protection

When a match date is known and no `--as-of-date` is provided, the runner uses the day before the match.

If `--as-of-date` is on or after the match date, normal pre-match analysis is blocked unless `--allow-post-match-analysis` is explicitly set. In that case outputs mark `post_match_analysis=true` and `leakage_warning=true`.

This protects practical winner analysis from accidental post-match leakage.
