import pandas as pd
from football_prediction_v19.features import build_extended_features
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score

df = pd.read_csv('data/processed/real_matches_clean.csv')
df = df[df['league'].isin(['La Liga','Premier League','Bundesliga'])].copy()
df = df[df['season'].isin(['2021-2022','2022-2023','2023-2024'])].copy()
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values('date').reset_index(drop=True)
df = df.dropna(subset=['home_goals','away_goals'])

print('Building all features (Phase 5 + 6)...')
df = build_extended_features(df)
df['btts'] = ((df['home_goals']>=1)&(df['away_goals']>=1)).astype(int)

train = df[df['season']!='2023-2024'].copy()
test  = df[df['season']=='2023-2024'].copy()

base = ['odds_home','odds_draw','odds_away']
p5 = [c for c in ['adj_home_xg','adj_away_xg','h2h_btts_rate',
      'home_td_goals_scored','away_td_goals_scored',
      'elo_diff','home_clean_sheet_rate','away_clean_sheet_rate'] if c in df.columns]
p6 = [c for c in ['ref_btts_rate','ref_avg_goals','ref_over25_rate',
      'home_days_since_last','away_days_since_last',
      'is_derby','dead_rubber_flag','rank_diff'] if c in df.columns]

print(f'P6 features available: {p6}')

def eval_btts(feats, label):
    X_tr = train[feats].fillna(0)
    X_te = test[feats].fillna(0)
    clf = GradientBoostingClassifier(n_estimators=100, random_state=42)
    clf.fit(X_tr, train['btts'])
    print(f'{label}: {accuracy_score(test["btts"], clf.predict(X_te)):.1%}')

eval_btts(base,        'Baseline (odds only)')
eval_btts(base+p5,     'Phase 5 features')
eval_btts(base+p5+p6,  'Phase 5 + 6 features')
