import pandas as pd
from football_prediction_v19.models.dixon_coles import DixonColesModel

df = pd.read_csv('data/processed/real_matches_clean.csv')
df = df[(df['league']=='La Liga') & (df['season']=='2023-2024')].copy()
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)

RETRAIN_EVERY = 10
MIN_WARMUP = 100
btts_probs = []
model = None
last_trained = -RETRAIN_EVERY

for i in range(MIN_WARMUP, len(df)):
    if i - last_trained >= RETRAIN_EVERY:
        model = DixonColesModel()
        model.fit(df.iloc[:i])
        last_trained = i
    row = df.iloc[i]
    try:
        probs = model.predict_probabilities(row['home_team'], row['away_team'])
        h, a = row.get('home_goals', None), row.get('away_goals', None)
        if pd.notna(h) and pd.notna(a):
            btts_probs.append({
                'dc_btts': probs['btts'],
                'actual_btts': int(h) >= 1 and int(a) >= 1
            })
    except: pass

bdf = pd.DataFrame(btts_probs)
print('=== DC BTTS Threshold Analysis ===')
print(f'Mean DC BTTS prob:    {bdf["dc_btts"].mean():.3f}')
print(f'Actual BTTS rate:     {bdf["actual_btts"].mean():.3f}')
print(f'DC probs > 0.5:       {(bdf["dc_btts"] > 0.5).mean():.1%}')
print(f'DC probs > 0.45:      {(bdf["dc_btts"] > 0.45).mean():.1%}')
print(f'DC probs > 0.40:      {(bdf["dc_btts"] > 0.40).mean():.1%}')
print()
# Accuracy bei verschiedenen Schwellen:
for thresh in [0.35, 0.40, 0.45, 0.50, 0.55]:
    acc = ((bdf['dc_btts'] > thresh) == bdf['actual_btts']).mean()
    print(f'Threshold {thresh}: Accuracy {acc:.1%}')
