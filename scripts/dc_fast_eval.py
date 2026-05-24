import pandas as pd
from football_prediction_v19.models.dixon_coles import DixonColesModel

RETRAIN_EVERY = 10  # Nur alle 10 Spiele neu trainieren

df = pd.read_csv('data/processed/real_matches_clean.csv')
df = df[(df['league']=='La Liga') & (df['season']=='2023-2024')].copy()
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

MIN_WARMUP = 100
results = []
model = None
last_trained = -RETRAIN_EVERY

print(f'Evaluating {len(df)} matches, retrain every {RETRAIN_EVERY}...')

for i in range(MIN_WARMUP, len(df)):
    prior = df.iloc[:i]
    
    # Nur alle RETRAIN_EVERY Schritte neu trainieren:
    if i - last_trained >= RETRAIN_EVERY:
        model = DixonColesModel()
        model.fit(prior)
        last_trained = i
        if i % 50 == 0:
            print(f'  Step {i}/{len(df)}')
    
    row = df.iloc[i]
    try:
        probs = model.predict_probabilities(
            row['home_team'], row['away_team'])
    except ValueError:
        continue
    
    actual_h = row.get('home_goals', None)
    actual_a = row.get('away_goals', None)
    if pd.isna(actual_h) or pd.isna(actual_a):
        continue
    
    actual_h, actual_a = int(actual_h), int(actual_a)
    actual_btts = actual_h >= 1 and actual_a >= 1
    actual_total = actual_h + actual_a
    
    results.append({
        'home_team': row['home_team'],
        'away_team': row['away_team'],
        'dc_home_win': probs['home_win'],
        'dc_btts': probs['btts'],
        'dc_under35': probs['under_35'],
        'home_correct': (probs['home_win'] > 0.4) == (actual_h > actual_a),
        'btts_correct': (probs['btts'] > 0.5) == actual_btts,
        'under35_correct': (probs['under_35'] > 0.5) == (actual_total <= 3),
    })

results_df = pd.DataFrame(results)
print(f'\n=== DC Results: La Liga 2023-2024 ===')
print(f'Evaluated:        {len(results_df)} matches')
print(f'Home Accuracy:    {results_df["home_correct"].mean():.1%}')
print(f'BTTS Accuracy:    {results_df["btts_correct"].mean():.1%}')
print(f'Under35 Accuracy: {results_df["under35_correct"].mean():.1%}')
