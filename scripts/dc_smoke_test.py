import pandas as pd
from football_prediction_v19.models.dixon_coles import DixonColesModel

df = pd.read_csv('data/processed/real_matches_clean.csv')
df = df[(df['league']=='La Liga') & (df['season']=='2023-2024')].copy()
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)
print(f'Total rows: {len(df)}')

# Smoke Test: ein Modell trainieren
prior = df.iloc[:150]
model = DixonColesModel()
model.fit(prior)
print('Fit OK')

probs = model.predict_probabilities(
    df.iloc[150]['home_team'],
    df.iloc[150]['away_team']
)
print(f'Home win: {probs["home_win"]:.3f}')
print(f'BTTS:     {probs["btts"]:.3f}')
print(f'Under35:  {probs["under_35"]:.3f}')
print('Model works.')
