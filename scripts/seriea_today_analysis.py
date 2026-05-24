import sys
sys.path.insert(0, 'src')
import pandas as pd
import joblib
from football_prediction_v19.data import clean_matches
from football_prediction_v19.features import build_fixture_features
from football_prediction_v19.model import load_model, predict_feature_rows
from football_prediction_v19.rules_v19 import assess_prediction
from football_prediction_v19.diagnostics.recommended_market import build_recommended_market
from football_prediction_v19.diagnostics.market_tier import build_market_tier

history = pd.read_csv('data/processed/real_matches_clean.csv')
history = clean_matches(history)

result = load_model('models/sample_pipeline_model.joblib')
model_path, feature_cols_path, meta_path = result
model = joblib.load(model_path)
import json
feature_cols = json.loads(open(feature_cols_path).read()) if feature_cols_path.endswith('.json') else joblib.load(feature_cols_path)

fixtures = [
    ('Milan',     'Cagliari', 1.45, 4.50, 7.00),
    ('Cremonese', 'Como',     5.00, 3.40, 1.75),
    ('Verona',    'Roma',     4.50, 3.50, 1.80),
    ('Lecce',     'Genoa',    2.80, 3.10, 2.60),
    ('Torino',    'Juventus', 4.00, 3.40, 1.90),
]

print('=== SERIE A - 38. Spieltag - 24.05.2026 ===')
print(f'{"Match":<25} {"Type":<15} {"Tier":<12} {"Score":>5}  Reason')
print('-'*90)

for home, away, oh, od, oa in fixtures:
    try:
        feats = build_fixture_features(
            history_df=history,
            home_team=home,
            away_team=away,
            match_date='2026-05-24',
            odds_home=oh,
            odds_draw=od,
            odds_away=oa
        )
        feat_df = pd.DataFrame([feats])
        preds = predict_feature_rows(model, feature_cols, feat_df)
        probs = {'H': float(preds[0][0]), 'D': float(preds[0][1]), 'A': float(preds[0][2])}
        rules = assess_prediction(feats, probs)
        rec = build_recommended_market(feats, rules)
        tier = build_market_tier(feats, rules, rec)
        print(f'{home} vs {away:<15} {rec["recommended_market_type"]:<15} {tier["market_tier"]:<12} {tier["market_tier_score"]:>5}  {tier["market_tier_reason"][:40]}')
    except Exception as e:
        print(f'{home} vs {away}: ERROR - {e}')
