import pandas as pd
from football_prediction_v19.features import build_extended_features
from football_prediction_v19.elo import EloRatingSystem
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score
import numpy as np

df = pd.read_csv('data/processed/real_matches_clean.csv')
df = df[(df['league']=='La Liga') & (df['season'].isin(['2021-2022','2022-2023','2023-2024']))].copy()
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)
df = df.dropna(subset=['home_goals','away_goals'])

print(f'Rows: {len(df)}')
print('Building extended features...')
df = build_extended_features(df)

# Elo hinzufuegen:
elo = EloRatingSystem()
df = elo.get_ratings_before_match(df)

# BTTS Target:
df['btts'] = ((df['home_goals'] >= 1) & (df['away_goals'] >= 1)).astype(int)

# Features auswaehlen:
base_features = ['odds_home','odds_draw','odds_away']
new_features = [c for c in [
    'adj_home_xg','adj_away_xg',
    'home_td_goals_scored','away_td_goals_scored',
    'home_td_win_rate','away_td_win_rate',
    'h2h_btts_rate','h2h_avg_goals','h2h_n',
    'home_clean_sheet_rate','away_clean_sheet_rate',
    'home_failed_to_score_rate','away_failed_to_score_rate',
    'elo_diff'
] if c in df.columns]

print(f'New features available: {new_features}')

# Train/Test Split - letzte Saison als Test:
train = df[df['season'] != '2023-2024'].copy()
test  = df[df['season'] == '2023-2024'].copy()

def eval_btts(features, label):
    X_train = train[features].fillna(0)
    y_train = train['btts']
    X_test  = test[features].fillna(0)
    y_test  = test['btts']
    clf = GradientBoostingClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    acc = accuracy_score(y_test, clf.predict(X_test))
    print(f'{label}: {acc:.1%}')

eval_btts(base_features, 'Baseline (odds only)')
eval_btts(base_features + new_features, 'Extended features')
