import pandas as pd
from football_prediction_v19.features import build_extended_features

# Mit mehr Prior-Daten testen:
df = pd.read_csv('data/processed/real_matches_clean.csv')
df = df[df['league']=='La Liga'].copy()
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

# Mehr History - alle verfuegbaren Saisons:
prior_df = df.iloc[:500].copy()
recent_prior = build_extended_features(prior_df)

print(f'Total prior rows: {len(prior_df)}')
if 'h2h_btts_rate' in recent_prior.columns:
    nan_rate = recent_prior['h2h_btts_rate'].isna().mean()
    valid = recent_prior['h2h_btts_rate'].dropna()
    print(f'h2h_btts_rate NaN rate: {nan_rate:.1%}')
    print(f'h2h_btts_rate valid values: {len(valid)}')
    print(f'h2h_btts_rate mean: {valid.mean():.3f}' if len(valid)>0 else 'no valid values')

if 'elo_diff' in recent_prior.columns:
    print(f'elo_diff NaN rate: {recent_prior["elo_diff"].isna().mean():.1%}')
    print(f'elo_diff range: {recent_prior["elo_diff"].min():.1f} to {recent_prior["elo_diff"].max():.1f}')
