class EloRatingSystem:
    def __init__(self, k=32.0, home_advantage=100.0, initial_rating=1500.0):
        self.k = k
        self.home_advantage = home_advantage
        self.initial_rating = initial_rating
        self.ratings = {}

    def _get(self, team):
        return self.ratings.get(team, self.initial_rating)

    def update(self, home_team, away_team, home_goals, away_goals):
        rh = self._get(home_team)
        ra = self._get(away_team)
        exp_h = 1.0 / (1.0 + 10 ** ((ra - rh - self.home_advantage) / 400.0))
        if home_goals > away_goals:
            act_h = 1.0
        elif home_goals == away_goals:
            act_h = 0.5
        else:
            act_h = 0.0
        self.ratings[home_team] = rh + self.k * (act_h - exp_h)
        self.ratings[away_team] = ra + self.k * ((1 - act_h) - (1 - exp_h))

    def get_ratings_before_match(self, df):
        import pandas as pd
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        elo_h, elo_a, elo_d = [], [], []
        self.ratings = {}
        for _, row in df.iterrows():
            elo_h.append(self._get(row['home_team']))
            elo_a.append(self._get(row['away_team']))
            elo_d.append(self._get(row['home_team']) - self._get(row['away_team']))
            if 'home_goals' in row and 'away_goals' in row:
                try:
                    self.update(row['home_team'], row['away_team'],
                                int(row['home_goals']), int(row['away_goals']))
                except Exception:
                    pass
        df['elo_home'] = elo_h
        df['elo_away'] = elo_a
        df['elo_diff'] = elo_d
        return df

    def get_all_ratings(self):
        return dict(self.ratings)
