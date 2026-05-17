# -*- coding: utf-8 -*-
"""Form-pattern mining audit.

Builds rolling pre-match form features (no look-ahead) and mines
form-pattern + odds-band combinations for 1X2, Over 2.5, Over 3.5, BTTS.

Outputs:
  outputs/diagnostics/form_pattern_audit.csv
  outputs/diagnostics/form_pattern_summary.md
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
from pathlib import Path

OUT_DIR = Path("outputs/diagnostics")
OUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOW = 5  # last-N-matches rolling window


# ─────────────────────────────────────────────────────────────────────────────
# 1. Load & normalise datasets
# ─────────────────────────────────────────────────────────────────────────────

def load_base(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["home_goals", "away_goals", "odds_home", "odds_draw", "odds_away"])
    df["result"] = df.apply(
        lambda r: "H" if r["home_goals"] > r["away_goals"]
        else ("D" if r["home_goals"] == r["away_goals"] else "A"), axis=1)
    df["total_goals"] = df["home_goals"] + df["away_goals"]
    df["over25"] = (df["total_goals"] > 2.5).astype(int)
    df["over35"] = (df["total_goals"] > 3.5).astype(int)
    df["btts"]   = ((df["home_goals"] > 0) & (df["away_goals"] > 0)).astype(int)
    return df.sort_values("date").reset_index(drop=True)


frames: list[pd.DataFrame] = []

# Top-5 (2021-2023, 4 seasons, full odds)
top5 = load_base("data/processed/combined_top5_2021_2023.csv")
frames.append(top5)

# D2 (2021-2024, 4 seasons)
d2 = load_base("data/processed/d2_clean.csv")
frames.append(d2)

# Eredivisie (2021-2024, 4 seasons)
n1 = load_base("data/processed/eredivisie_clean.csv")
frames.append(n1)

# MLS (2023-2025, with odds)
mls_raw = pd.read_csv("data/processed/mls_matches_clean_with_odds.csv")
mls_raw["date"] = pd.to_datetime(mls_raw["date"])
mls_raw = mls_raw.dropna(subset=["home_goals", "away_goals", "odds_home", "odds_draw", "odds_away"])
mls_raw["result"] = mls_raw.apply(
    lambda r: "H" if r["home_goals"] > r["away_goals"]
    else ("D" if r["home_goals"] == r["away_goals"] else "A"), axis=1)
mls_raw["total_goals"] = mls_raw["home_goals"] + mls_raw["away_goals"]
mls_raw["over25"] = (mls_raw["total_goals"] > 2.5).astype(int)
mls_raw["over35"] = (mls_raw["total_goals"] > 3.5).astype(int)
mls_raw["btts"]   = ((mls_raw["home_goals"] > 0) & (mls_raw["away_goals"] > 0)).astype(int)
mls = mls_raw.sort_values("date").reset_index(drop=True)
frames.append(mls)

all_data = pd.concat(frames, ignore_index=True).sort_values("date").reset_index(drop=True)

print(f"Total rows loaded: {len(all_data)}")
for league in sorted(all_data["league"].unique()):
    sub = all_data[all_data["league"] == league]
    print(f"  {league}: {len(sub)} rows, "
          f"seasons {sub['date'].dt.year.min()}-{sub['date'].dt.year.max()}")


# ─────────────────────────────────────────────────────────────────────────────
# 2. Rolling form features (strict no look-ahead)
# ─────────────────────────────────────────────────────────────────────────────

def rolling_form(df: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Add rolling form columns.  All form is calculated from matches
    strictly BEFORE the current row date, per team."""

    df = df.copy().sort_values("date").reset_index(drop=True)

    # Build a long team-match index: one row per team per match
    home_records = df[["date", "home_team", "home_goals", "away_goals", "result",
                        "over25", "btts"]].copy()
    home_records.columns = ["date", "team", "gf", "ga", "result", "over25", "btts"]
    home_records["is_home"] = True
    home_records["pts"] = home_records["result"].map({"H": 3, "D": 1, "A": 0})
    home_records["win"]  = (home_records["result"] == "H").astype(int)
    home_records["draw"] = (home_records["result"] == "D").astype(int)
    home_records["loss"] = (home_records["result"] == "A").astype(int)

    away_records = df[["date", "away_team", "away_goals", "home_goals", "result",
                        "over25", "btts"]].copy()
    away_records.columns = ["date", "team", "gf", "ga", "result", "over25", "btts"]
    away_records["is_home"] = False
    away_records["pts"] = away_records["result"].map({"A": 3, "D": 1, "H": 0})
    away_records["win"]  = (away_records["result"] == "A").astype(int)
    away_records["draw"] = (away_records["result"] == "D").astype(int)
    away_records["loss"] = (away_records["result"] == "H").astype(int)

    team_matches = pd.concat([home_records, away_records], ignore_index=True)
    team_matches = team_matches.sort_values(["team", "date"]).reset_index(drop=True)

    # For each team compute rolling stats (shifted by 1 = look-behind only)
    cols_to_roll = ["pts", "win", "draw", "loss", "gf", "ga", "over25", "btts"]
    grp = team_matches.groupby("team")[cols_to_roll]
    rolled = grp.transform(lambda s: s.shift(1).rolling(window, min_periods=1).sum())
    rolled_cnt = team_matches.groupby("team")["pts"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).count())

    team_matches["f_pts"]    = rolled["pts"]
    team_matches["f_wins"]   = rolled["win"]
    team_matches["f_draws"]  = rolled["draw"]
    team_matches["f_losses"] = rolled["loss"]
    team_matches["f_gf"]     = rolled["gf"]
    team_matches["f_ga"]     = rolled["ga"]
    team_matches["f_over25_rate"] = rolled["over25"] / rolled_cnt.clip(lower=1)
    team_matches["f_btts_rate"]   = rolled["btts"]   / rolled_cnt.clip(lower=1)
    team_matches["f_n"]      = rolled_cnt  # how many prior matches counted

    # Venue-specific rolling (last 5 home games / last 5 away games)
    grp_venue = team_matches.groupby(["team", "is_home"])[cols_to_roll]
    rolled_v = grp_venue.transform(lambda s: s.shift(1).rolling(window, min_periods=1).sum())
    rolled_v_cnt = team_matches.groupby(["team", "is_home"])["pts"].transform(
        lambda s: s.shift(1).rolling(window, min_periods=1).count())
    team_matches["fv_pts"]  = rolled_v["pts"]
    team_matches["fv_gf"]   = rolled_v["gf"]
    team_matches["fv_ga"]   = rolled_v["ga"]
    team_matches["fv_n"]    = rolled_v_cnt

    # Streak: current run of identical outcomes
    def streak_features(group):
        results = group["result"].values
        is_home = group["is_home"].values
        streak_types, streak_lens = [], []
        for i in range(len(results)):
            # look back from match i-1
            if i == 0:
                streak_types.append("N")
                streak_lens.append(0)
                continue
            outcomes = []
            for j in range(i - 1, -1, -1):
                outcome = "W" if ((is_home[j] and results[j] == "H") or
                                  (not is_home[j] and results[j] == "A")) \
                         else "D" if results[j] == "D" else "L"
                outcomes.append(outcome)
            if not outcomes:
                streak_types.append("N"); streak_lens.append(0); continue
            cur = outcomes[0]
            length = 1
            for o in outcomes[1:]:
                if o == cur:
                    length += 1
                else:
                    break
            streak_types.append(cur)
            streak_lens.append(length)
        return pd.DataFrame({"streak_type": streak_types, "streak_len": streak_lens},
                            index=group.index)

    streaks = team_matches.groupby("team", group_keys=False).apply(streak_features)
    team_matches["streak_type"] = streaks["streak_type"]
    team_matches["streak_len"]  = streaks["streak_len"]

    # Split back into home/away perspectives
    home_tm = team_matches[team_matches["is_home"]].set_index(["date", "team"])
    away_tm = team_matches[~team_matches["is_home"]].set_index(["date", "team"])

    def merge_side(df_main, side_tm, prefix):
        team_col = f"{prefix}_team"
        side_tm = side_tm.add_prefix(prefix + "_").reset_index()
        side_tm = side_tm.rename(columns={
            prefix + "_date": "date",
            prefix + "_team": team_col,
        })
        return df_main.merge(side_tm[["date", team_col] +
                                     [c for c in side_tm.columns if c.startswith(prefix + "_f")]
                                     + [prefix + "_streak_type", prefix + "_streak_len"]],
                             on=["date", team_col], how="left")

    df = merge_side(df, home_tm.reset_index(), "home")
    df = merge_side(df, away_tm.reset_index(), "away")
    return df


print("\nBuilding rolling form features...")
all_data = rolling_form(all_data)
print(f"Done. Rows with home form: {all_data['home_f_pts'].notna().sum()}")

# Drop rows where we have fewer than 3 prior matches (cold-start)
all_data = all_data[all_data["home_f_n"] >= 3].copy()
all_data = all_data[all_data["away_f_n"] >= 3].copy()
print(f"After cold-start filter (min 3 prior): {len(all_data)} rows")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Pattern buckets
# ─────────────────────────────────────────────────────────────────────────────

df = all_data.copy()
df["strong_home_form"]  = df["home_f_pts"] >= 10
df["weak_home_form"]    = df["home_f_pts"] <= 5
df["strong_away_form"]  = df["away_f_pts"] >= 10
df["weak_away_form"]    = df["away_f_pts"] <= 5
df["drawish_home"]      = df["home_f_draws"] >= 2
df["drawish_away"]      = df["away_f_draws"] >= 2
df["over_home"]         = df["home_f_over25_rate"] >= 0.60
df["over_away"]         = df["away_f_over25_rate"] >= 0.60
df["btts_home"]         = df["home_f_btts_rate"] >= 0.60
df["btts_away"]         = df["away_f_btts_rate"] >= 0.60
df["home_streak_W"]     = df["home_streak_type"] == "W"
df["away_streak_W"]     = df["away_streak_type"] == "W"
df["home_streak_L"]     = df["home_streak_type"] == "L"
df["away_streak_L"]     = df["away_streak_type"] == "L"
df["home_streak_W3p"]   = (df["home_streak_type"] == "W") & (df["home_streak_len"] >= 3)
df["away_streak_W3p"]   = (df["away_streak_type"] == "W") & (df["away_streak_len"] >= 3)
df["home_gf_high"]      = df["home_f_gf"] >= 10   # >= 10 goals in last 5
df["away_gf_high"]      = df["away_f_gf"] >= 10
df["home_ga_low"]       = df["home_f_ga"] <= 4    # defensive solidity
df["away_ga_low"]       = df["away_f_ga"] <= 4
# Combined patterns
df["form_mismatch_H"]   = df["strong_home_form"] & df["weak_away_form"]
df["form_mismatch_A"]   = df["strong_away_form"] & df["weak_home_form"]
df["both_drawish"]      = df["drawish_home"] & df["drawish_away"]
df["both_over"]         = df["over_home"]   & df["over_away"]
df["both_btts"]         = df["btts_home"]   & df["btts_away"]
df["home_dominant"]     = df["strong_home_form"] & df["home_streak_W"] & ~df["strong_away_form"]
df["away_dominant"]     = df["strong_away_form"] & df["away_streak_W"] & ~df["strong_home_form"]

PATTERNS = {
    "strong_home_form":  df["strong_home_form"],
    "weak_home_form":    df["weak_home_form"],
    "strong_away_form":  df["strong_away_form"],
    "weak_away_form":    df["weak_away_form"],
    "drawish_home":      df["drawish_home"],
    "drawish_away":      df["drawish_away"],
    "both_drawish":      df["both_drawish"],
    "over_home":         df["over_home"],
    "over_away":         df["over_away"],
    "both_over":         df["both_over"],
    "btts_home":         df["btts_home"],
    "btts_away":         df["btts_away"],
    "both_btts":         df["both_btts"],
    "home_streak_W":     df["home_streak_W"],
    "away_streak_W":     df["away_streak_W"],
    "home_streak_W3p":   df["home_streak_W3p"],
    "away_streak_W3p":   df["away_streak_W3p"],
    "home_streak_L":     df["home_streak_L"],
    "away_streak_L":     df["away_streak_L"],
    "form_mismatch_H":   df["form_mismatch_H"],
    "form_mismatch_A":   df["form_mismatch_A"],
    "both_strong":       df["strong_home_form"] & df["strong_away_form"],
    "home_dominant":     df["home_dominant"],
    "away_dominant":     df["away_dominant"],
    "home_gf_high":      df["home_gf_high"],
    "home_ga_low":       df["home_ga_low"],
    "away_gf_high":      df["away_gf_high"],
    "away_ga_low":       df["away_ga_low"],
    "all_matches":       pd.Series([True] * len(df), index=df.index),
}

ODDS_BANDS = {
    "home": {
        "H_1.30-1.60": (df["odds_home"] >= 1.30) & (df["odds_home"] < 1.60),
        "H_1.60-2.00": (df["odds_home"] >= 1.60) & (df["odds_home"] < 2.00),
        "H_2.00-2.75": (df["odds_home"] >= 2.00) & (df["odds_home"] < 2.75),
        "H_2.75+":     df["odds_home"] >= 2.75,
        "H_any":       pd.Series([True] * len(df), index=df.index),
    },
    "draw": {
        "D_3.20-3.80": (df["odds_draw"] >= 3.20) & (df["odds_draw"] < 3.80),
        "D_3.80-4.50": (df["odds_draw"] >= 3.80) & (df["odds_draw"] < 4.50),
        "D_4.50-5.50": (df["odds_draw"] >= 4.50) & (df["odds_draw"] < 5.50),
        "D_5.50+":     df["odds_draw"] >= 5.50,
        "D_any":       pd.Series([True] * len(df), index=df.index),
    },
    "away": {
        "A_1.30-1.80": (df["odds_away"] >= 1.30) & (df["odds_away"] < 1.80),
        "A_1.80-2.50": (df["odds_away"] >= 1.80) & (df["odds_away"] < 2.50),
        "A_2.50-4.00": (df["odds_away"] >= 2.50) & (df["odds_away"] < 4.00),
        "A_4.00+":     df["odds_away"] >= 4.00,
        "A_any":       pd.Series([True] * len(df), index=df.index),
    },
}

MARKETS = {
    "Home_win":  ("result", "H", "odds_home"),
    "Draw":      ("result", "D", "odds_draw"),
    "Away_win":  ("result", "A", "odds_away"),
    "Over25":    ("over25", 1,   None),
    "Over35":    ("over35", 1,   None),
    "BTTS":      ("btts",   1,   None),
}

# Fixed over/BTTS odds estimates for ROI calc (average market)
MARKET_ODDS_EST = {"Over25": 1.88, "Over35": 2.60, "BTTS": 1.78}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Analysis engine
# ─────────────────────────────────────────────────────────────────────────────

def analyse(sub: pd.DataFrame, market: str, target_col: str,
            target_val, odds_col: str | None) -> dict | None:
    if len(sub) < 10:
        return None
    hit = (sub[target_col] == target_val).sum()
    n   = len(sub)
    hit_rate = hit / n

    if odds_col:
        profits = sub.apply(
            lambda r: (r[odds_col] - 1) if r[target_col] == target_val else -1.0, axis=1)
    else:
        est_odds = MARKET_ODDS_EST[market]
        profits = sub[target_col].apply(
            lambda v: (est_odds - 1) if v == target_val else -1.0)

    total_profit = profits.sum()
    roi = total_profit / n * 100

    cum = profits.cumsum().values
    rm  = np.maximum.accumulate(np.concatenate([[0], cum[:-1]]))
    dd  = (cum - rm).min()

    top3  = profits.nlargest(3).sum()
    ex3_p = total_profit - top3
    ex3_r = ex3_p / n * 100

    avg_odds = sub[odds_col].mean() if odds_col else MARKET_ODDS_EST[market]

    leagues  = sub["league"].unique().tolist() if "league" in sub.columns else []
    seasons  = sorted(sub["date"].dt.year.unique().tolist())

    return {
        "market": market,
        "n": n,
        "hit": int(hit),
        "hit_rate": round(hit_rate * 100, 1),
        "profit": round(total_profit, 2),
        "roi": round(roi, 1),
        "avg_odds": round(avg_odds, 2),
        "max_dd": round(dd, 2),
        "top3_wins": round(top3, 2),
        "profit_ex_top3": round(ex3_p, 2),
        "roi_ex_top3": round(ex3_r, 1),
        "seasons": seasons,
        "n_seasons": len(seasons),
        "leagues": leagues,
        "n_leagues": len(leagues),
    }


def hard_reject(r: dict) -> str | None:
    if r["n"] < 50:
        return f"n={r['n']}<50"
    if r["roi"] <= 0:
        return f"ROI={r['roi']:.1f}%<=0"
    if r["profit_ex_top3"] <= 0:
        return "profit_ex_top3<=0"
    if r["n_seasons"] < 2:
        return f"only {r['n_seasons']} season"
    if r["n_leagues"] < 2 and r["n_seasons"] < 3:
        return f"1 league, only {r['n_seasons']} seasons"
    dd = r["max_dd"]
    profit = r["profit"]
    if profit > 0 and dd < 0 and abs(dd) > profit * 2:
        return f"dd({dd:.1f})>2x profit({profit:.1f})"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. Run all combinations
# ─────────────────────────────────────────────────────────────────────────────

print("\nRunning pattern x odds-band x market sweep...")
results = []

for pat_name, pat_mask in PATTERNS.items():
    pat_sub = df[pat_mask]

    for mkt_name, (target_col, target_val, odds_col) in MARKETS.items():
        # odds-band sweep
        if odds_col:
            side = {"odds_home": "home", "odds_draw": "draw", "odds_away": "away"}[odds_col]
            bands = ODDS_BANDS[side]
        else:
            bands = {"any": pd.Series([True] * len(df), index=df.index)}

        for band_name, band_mask in bands.items():
            sub = pat_sub[band_mask.loc[pat_sub.index]]
            if len(sub) < 10:
                continue
            r = analyse(sub, mkt_name, target_col, target_val, odds_col)
            if r is None:
                continue
            r["pattern"] = pat_name
            r["odds_band"] = band_name
            r["reject"] = hard_reject(r)
            results.append(r)

rdf = pd.DataFrame(results)
rdf = rdf.drop_duplicates(subset=["pattern", "odds_band", "market"])

passed  = rdf[rdf["reject"].isna()].copy()
rejected = rdf[rdf["reject"].notna()].copy()

print(f"Total candidates: {len(rdf)}")
print(f"  Passed all hard filters: {len(passed)}")
print(f"  Rejected: {len(rejected)}")

# Save full audit CSV
rdf.to_csv(OUT_DIR / "form_pattern_audit.csv", index=False)
print(f"\nSaved: {OUT_DIR}/form_pattern_audit.csv")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Per-league breakdown for passed candidates
# ─────────────────────────────────────────────────────────────────────────────

def per_league_breakdown(pat_mask, band_mask, mkt_name, target_col, target_val, odds_col):
    rows = []
    sub_all = df[pat_mask & band_mask]
    for league in sorted(sub_all["league"].unique()):
        sub = sub_all[sub_all["league"] == league]
        r = analyse(sub, mkt_name, target_col, target_val, odds_col)
        if r:
            r["league_check"] = league
            rows.append(r)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 7. Generate markdown summary
# ─────────────────────────────────────────────────────────────────────────────

lines = []
lines.append("# Form Pattern Mining Audit — Diagnostic Report")
lines.append("\n> DIAGNOSTIC ONLY. No betting recommendations.")
lines.append(f"\n**Total rows analysed:** {len(df)}")
lines.append(f"**Leagues:** {', '.join(sorted(df['league'].unique()))}")
lines.append(f"**Date range:** {df['date'].min().date()} – {df['date'].max().date()}")
lines.append(f"**Candidates evaluated:** {len(rdf)}")
lines.append(f"**Passed hard filters:** {len(passed)}")
lines.append(f"**Rejected:** {len(rejected)}")

# Passed table
lines.append("\n---\n## Passed Candidates (all hard filters cleared)\n")
if passed.empty:
    lines.append("*No candidates passed all hard filters.*")
else:
    passed_sorted = passed.sort_values("roi", ascending=False)
    for _, row in passed_sorted.iterrows():
        lines.append(f"### {row['pattern']} | {row['market']} | {row['odds_band']}")
        lines.append(f"- **n:** {row['n']} | **ROI:** {row['roi']:.1f}% | **Hit rate:** {row['hit_rate']:.1f}%")
        lines.append(f"- **Profit:** {row['profit']:.2f} | **Avg odds:** {row['avg_odds']:.2f}")
        lines.append(f"- **Max drawdown:** {row['max_dd']:.2f} | **ex-top3 ROI:** {row['roi_ex_top3']:.1f}%")
        lines.append(f"- **Seasons:** {row['seasons']} ({row['n_seasons']} seasons)")
        lines.append(f"- **Leagues:** {row['leagues']} ({row['n_leagues']} leagues)")
        lines.append("")

# Near-miss: ROI > 0, n >= 30
lines.append("\n---\n## Near-Miss Candidates (ROI > 0 but failed at least one hard filter)\n")
near = rejected[(rejected["roi"] > 5) & (rejected["n"] >= 30)].sort_values("roi", ascending=False).head(25)
if near.empty:
    lines.append("*None.*")
else:
    for _, row in near.iterrows():
        lines.append(f"### {row['pattern']} | {row['market']} | {row['odds_band']}")
        lines.append(f"- **n:** {row['n']} | **ROI:** {row['roi']:.1f}% | **Hit:** {row['hit_rate']:.1f}%")
        lines.append(f"- **Profit:** {row['profit']:.2f} | **Avg odds:** {row['avg_odds']:.2f} | **ex-top3:** {row['roi_ex_top3']:.1f}%")
        lines.append(f"- **Seasons:** {row['seasons']} | **Leagues:** {row['n_leagues']}")
        lines.append(f"- **REJECTED:** {row['reject']}")
        lines.append("")

# Over/BTTS base rates
lines.append("\n---\n## Market Base Rates (no pattern filter)\n")
base_mask = pd.Series([True] * len(df), index=df.index)
for mkt_name, (target_col, target_val, odds_col) in MARKETS.items():
    sub = df
    hit = (sub[target_col] == target_val).sum()
    n   = len(sub)
    lines.append(f"- **{mkt_name}:** {hit}/{n} = {hit/n*100:.1f}%")

# Benchmark comparison
lines.append("\n---\n## Comparison with Benchmark (MLS Away edge>=0.04, ROI~9%)\n")
lines.append("The validated MLS Away paper-test strategy achieves:")
lines.append("- n=116 (2025 strict OOS), ROI=+9.2%, ex-top3=-4.4%  (fragile at low edge)")
lines.append("- n=142 (combined 2024+2025), ROI=+9.1%, 3/3 positive seasons")
lines.append("")
if passed.empty:
    lines.append("**No form-pattern strategy passed all hard filters.**")
    lines.append("Nothing beats the benchmark from this audit.")
else:
    beats = passed[passed["roi"] > 9.2]
    lines.append(f"Candidates with ROI > 9.2% (benchmark): {len(beats)}")
    lines.append("Whether they beat the benchmark on cross-season robustness: see individual entries above.")

# Final verdict
lines.append("\n---\n## Final Verdict\n")
lines.append("**Paper-test eligible from form patterns:** See 'Passed Candidates' section.")
lines.append("**Watchlist (near-miss, needs more seasons):** See 'Near-Miss' section.")
lines.append("")
lines.append("> DIAGNOSTIC ONLY. No betting recommendations. No live betting.")
lines.append("> Minimum 100 tracked bets required before any new strategy is paper-test eligible.")

md = "\n".join(lines)
(OUT_DIR / "form_pattern_summary.md").write_text(md, encoding="utf-8")
print(f"Saved: {OUT_DIR}/form_pattern_summary.md")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Console summary
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "=" * 72)
print("PASSED CANDIDATES")
print("=" * 72)
if passed.empty:
    print("  None passed all hard filters.")
else:
    for _, row in passed.sort_values("roi", ascending=False).iterrows():
        print(f"\n  {row['pattern']} | {row['market']} | {row['odds_band']}")
        print(f"    n={row['n']}, ROI={row['roi']:.1f}%, hit={row['hit_rate']:.1f}%, "
              f"avg_odds={row['avg_odds']:.2f}")
        print(f"    profit={row['profit']:.2f}, ex-top3={row['roi_ex_top3']:.1f}%, "
              f"max_dd={row['max_dd']:.2f}")
        print(f"    seasons={row['seasons']} leagues={row['n_leagues']}")

print("\n" + "=" * 72)
print("NEAR-MISS CANDIDATES (ROI>5%, n>=30, failed >=1 filter)")
print("=" * 72)
for _, row in near.iterrows():
    print(f"\n  {row['pattern']} | {row['market']} | {row['odds_band']}")
    print(f"    n={row['n']}, ROI={row['roi']:.1f}%, ex-top3={row['roi_ex_top3']:.1f}%")
    print(f"    seasons={row['n_seasons']} leagues={row['n_leagues']}")
    print(f"    REJECTED: {row['reject']}")

print("\n" + "=" * 72)
print("MARKET BASE RATES")
print("=" * 72)
for mkt_name, (target_col, target_val, _) in MARKETS.items():
    hit = (df[target_col] == target_val).sum()
    n   = len(df)
    print(f"  {mkt_name}: {hit/n*100:.1f}% ({hit}/{n})")
