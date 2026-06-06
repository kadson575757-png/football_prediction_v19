# Trusted xG Sources

Place real trusted xG source CSV files in this folder.

Accepted schemas:

- match-pair: `date`, `home_team`, `away_team`, `home_xg`, `away_xg`
- FBref-long: `Date`, `Squad`, `Opponent`, `xG`, `xGA`, `Venue` when home/away pairing is safe
- Understat-pair: `date`, `home_team`, `away_team`, `home_xG`, `away_xG`

Files in this folder are not automatically used by the model. They must pass:

1. trusted xG fill preview
2. filled manual xG acceptance gate
3. manifest promotion preview and manual review

No xG values are inferred or invented by this workflow.
