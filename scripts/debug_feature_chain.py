import sys
sys.path.insert(0, 'src')
import pandas as pd
from football_prediction_v19.features import build_extended_features

# Simuliere was der Replay macht:
df = pd.read_csv('data/processed/real_matches_clean.csv')
df = df[df['league']=='La Liga'].copy()
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

# prior_df wie im Replay:
prior_df = df.iloc[:200].copy()

# recent_prior wie in Phase 7:
recent_prior = prior_df.tail(200)
recent_prior = build_extended_features(recent_prior)

print('Columns in recent_prior:')
new_cols = [c for c in recent_prior.columns if c not in prior_df.columns]
print(f'New columns added: {new_cols}')
print(f'h2h_btts_rate NaN rate: {recent_prior["h2h_btts_rate"].isna().mean():.1%}' if 'h2h_btts_rate' in recent_prior.columns else 'h2h_btts_rate: NOT FOUND')
print(f'elo_diff sample: {recent_prior["elo_diff"].dropna().head(3).tolist()}' if 'elo_diff' in recent_prior.columns else 'elo_diff: NOT FOUND')

# Was bekommt build_match_features:
from football_prediction_v19.features import build_features
match = df.iloc[200]
result = build_features(recent_prior)
print(f'build_features output columns: {list(result.columns)[:10]}')
print(f'h2h_btts_rate in output: {"h2h_btts_rate" in result.columns}')
print(f'elo_diff in output: {"elo_diff" in result.columns}')
