# v2.5 Batch Winner Analysis

Use `scripts/run_match_winner_batch.py --input config/v25_match_batch_template.csv` to analyze multiple matches.

The input columns are `competition,season,match_date,home_team,away_team`.

The batch output writes CSV, JSON, Markdown, data-blocked rows, and no-clear-winner rows. Counts summarize winner picks, winner leans, no clear winner, no decision, and data blocked.

This workflow does not create stake, ROI, profit, yield, or money-management metrics.
