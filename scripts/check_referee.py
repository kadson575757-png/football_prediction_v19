import pandas as pd
df = pd.read_csv('data/processed/real_matches_clean.csv')
print('referee column:', 'referee' in df.columns)
if 'referee' in df.columns:
    filled = df['referee'].notna().mean()
    print(f'Filled: {filled:.1%}')
    print(df['referee'].value_counts().head(5))
else:
    print('No referee column found')
print()
card_cols = [c for c in df.columns if 'card' in c.lower()]
print('Card columns:', card_cols)
