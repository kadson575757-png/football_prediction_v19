# -*- coding: utf-8 -*-
"""Deep analysis of top form-pattern candidates: per-league, per-season,
odds-band stability, and comparison with MLS Away benchmark."""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path

OUT_DIR = Path("outputs/diagnostics")
WINDOW = 5


def load_base(path):
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


def rolling_form(df):
    df = df.copy().sort_values("date").reset_index(drop=True)
    home_r = df[["date","home_team","home_goals","away_goals","result","over25","btts"]].copy()
    home_r.columns = ["date","team","gf","ga","result","over25","btts"]
    home_r["is_home"] = True
    home_r["pts"]  = home_r["result"].map({"H":3,"D":1,"A":0})
    home_r["win"]  = (home_r["result"]=="H").astype(int)
    home_r["draw"] = (home_r["result"]=="D").astype(int)
    home_r["loss"] = (home_r["result"]=="A").astype(int)
    away_r = df[["date","away_team","away_goals","home_goals","result","over25","btts"]].copy()
    away_r.columns = ["date","team","gf","ga","result","over25","btts"]
    away_r["is_home"] = False
    away_r["pts"]  = away_r["result"].map({"A":3,"D":1,"H":0})
    away_r["win"]  = (away_r["result"]=="A").astype(int)
    away_r["draw"] = (away_r["result"]=="D").astype(int)
    away_r["loss"] = (away_r["result"]=="H").astype(int)
    tm = pd.concat([home_r, away_r], ignore_index=True).sort_values(["team","date"]).reset_index(drop=True)
    cols_to_roll = ["pts","win","draw","loss","gf","ga","over25","btts"]
    grp = tm.groupby("team")[cols_to_roll]
    rolled = grp.transform(lambda s: s.shift(1).rolling(WINDOW, min_periods=1).sum())
    cnt    = tm.groupby("team")["pts"].transform(lambda s: s.shift(1).rolling(WINDOW, min_periods=1).count())
    tm["f_pts"]  = rolled["pts"];   tm["f_wins"] = rolled["win"]
    tm["f_draws"]= rolled["draw"];  tm["f_losses"]= rolled["loss"]
    tm["f_gf"]   = rolled["gf"];    tm["f_ga"]   = rolled["ga"]
    tm["f_over25_rate"] = rolled["over25"] / cnt.clip(lower=1)
    tm["f_btts_rate"]   = rolled["btts"]   / cnt.clip(lower=1)
    tm["f_n"]    = cnt

    def streak_features(group):
        results   = group["result"].values
        is_home   = group["is_home"].values
        stypes, slens = [], []
        for i in range(len(results)):
            if i == 0: stypes.append("N"); slens.append(0); continue
            cur_out = None; length = 0
            for j in range(i-1, -1, -1):
                o = ("W" if ((is_home[j] and results[j]=="H") or (not is_home[j] and results[j]=="A"))
                     else "D" if results[j]=="D" else "L")
                if cur_out is None: cur_out = o; length = 1
                elif o == cur_out: length += 1
                else: break
            stypes.append(cur_out or "N"); slens.append(length)
        return pd.DataFrame({"streak_type": stypes, "streak_len": slens}, index=group.index)

    streaks = tm.groupby("team", group_keys=False).apply(streak_features)
    tm["streak_type"] = streaks["streak_type"]; tm["streak_len"] = streaks["streak_len"]

    def merge_side(df_main, side_name, is_home_val, team_col):
        side = tm[tm["is_home"]==is_home_val].copy()
        side = side.rename(columns={
            "f_pts":f"{side_name}_f_pts","f_wins":f"{side_name}_f_wins",
            "f_draws":f"{side_name}_f_draws","f_losses":f"{side_name}_f_losses",
            "f_gf":f"{side_name}_f_gf","f_ga":f"{side_name}_f_ga",
            "f_over25_rate":f"{side_name}_f_over25_rate","f_btts_rate":f"{side_name}_f_btts_rate",
            "f_n":f"{side_name}_f_n","streak_type":f"{side_name}_streak_type",
            "streak_len":f"{side_name}_streak_len","team":"_team"})
        merge_cols = [c for c in side.columns if c.startswith(f"{side_name}_")] + ["date","_team"]
        return df_main.merge(side[merge_cols].rename(columns={"_team":team_col}),
                             on=["date",team_col], how="left")

    df = merge_side(df, "home", True,  "home_team")
    df = merge_side(df, "away", False, "away_team")
    return df


# -- Load all data -------------------------------------------------------------
print("Loading data...")
frames = []
for path in ["data/processed/combined_top5_2021_2023.csv",
             "data/processed/d2_clean.csv",
             "data/processed/eredivisie_clean.csv"]:
    frames.append(load_base(path))
mls_raw = pd.read_csv("data/processed/mls_matches_clean_with_odds.csv")
mls_raw["date"] = pd.to_datetime(mls_raw["date"])
mls_raw = mls_raw.dropna(subset=["home_goals","away_goals","odds_home","odds_draw","odds_away"])
mls_raw["result"] = mls_raw.apply(lambda r: "H" if r["home_goals"]>r["away_goals"] else ("D" if r["home_goals"]==r["away_goals"] else "A"),axis=1)
mls_raw["total_goals"]=mls_raw["home_goals"]+mls_raw["away_goals"]
mls_raw["over25"]=(mls_raw["total_goals"]>2.5).astype(int)
mls_raw["over35"]=(mls_raw["total_goals"]>3.5).astype(int)
mls_raw["btts"]=((mls_raw["home_goals"]>0)&(mls_raw["away_goals"]>0)).astype(int)
frames.append(mls_raw.sort_values("date").reset_index(drop=True))

all_data = pd.concat(frames,ignore_index=True).sort_values("date").reset_index(drop=True)
print("Building form features...")
all_data = rolling_form(all_data)
all_data = all_data[(all_data["home_f_n"]>=3)&(all_data["away_f_n"]>=3)].copy()

df = all_data.copy()
df["strong_home_form"] = df["home_f_pts"] >= 10
df["weak_away_form"]   = df["away_f_pts"] <= 5
df["strong_away_form"] = df["away_f_pts"] >= 10
df["over_home"]        = df["home_f_over25_rate"] >= 0.60
df["over_away"]        = df["away_f_over25_rate"] >= 0.60
df["btts_home"]        = df["home_f_btts_rate"] >= 0.60
df["btts_away"]        = df["away_f_btts_rate"] >= 0.60
df["both_over"]        = df["over_home"] & df["over_away"]
df["both_btts"]        = df["btts_home"] & df["btts_away"]
df["both_strong"]      = df["strong_home_form"] & df["strong_away_form"]
df["form_mismatch_H"]  = df["strong_home_form"] & df["weak_away_form"]
df["drawish_home"]     = df["home_f_draws"] >= 2
df["drawish_away"]     = df["away_f_draws"] >= 2
df["home_dominant"]    = df["strong_home_form"] & (df["home_streak_type"]=="W") & ~df["strong_away_form"]
df["home_gf_high"]     = df["home_f_gf"] >= 10
df["away_gf_high"]     = df["away_f_gf"] >= 10
df["home_streak_W3p"]  = (df["home_streak_type"]=="W") & (df["home_streak_len"]>=3)
df["form_mismatch_A"]  = df["strong_away_form"] & df["weak_away_form"]


def stats(sub, target_col, target_val, odds_col=None, est_odds=None):
    n = len(sub)
    if n == 0: return None
    if odds_col:
        profits = sub.apply(lambda r: (r[odds_col]-1) if r[target_col]==target_val else -1.0, axis=1)
        avg_odds = sub[odds_col].mean()
    else:
        eo = est_odds or 1.88
        profits = sub[target_col].apply(lambda v: (eo-1) if v==target_val else -1.0)
        avg_odds = eo
    profit = profits.sum()
    roi    = profit/n*100
    hit    = (sub[target_col]==target_val).sum()
    cum    = profits.cumsum().values
    rm     = np.maximum.accumulate(np.concatenate([[0],cum[:-1]]))
    dd     = (cum-rm).min()
    top3   = profits.nlargest(3).sum()
    return {"n":n,"profit":round(profit,2),"roi":round(roi,1),
            "hit":int(hit),"hit_rate":round(hit/n*100,1),
            "avg_odds":round(avg_odds,2),"max_dd":round(dd,2),
            "top3_wins":round(top3,2),"profit_ex_top3":round(profit-top3,2),
            "roi_ex_top3":round((profit-top3)/n*100,1)}


SEP = "=" * 72

print(f"\n{SEP}")
print("TOP CANDIDATES — DEEP ANALYSIS")
print(SEP)


# -- CANDIDATE 1: both_strong + Draw + odds 4.50-5.50 -------------------------
print(f"\n{'-'*60}")
print("CANDIDATE 1: both_strong | Draw | odds 4.50-5.50")
print("both teams in last-5 points >= 10 (both high form)")
print(f"{'-'*60}")
mask = df["both_strong"] & (df["odds_draw"]>=4.50) & (df["odds_draw"]<5.50)
sub0 = df[mask]
s = stats(sub0, "result", "D", "odds_draw")
print(f"Overall: n={s['n']}, ROI={s['roi']:.1f}%, hit={s['hit_rate']:.1f}%, "
      f"avg_odds={s['avg_odds']:.2f}, ex-top3={s['roi_ex_top3']:.1f}%, dd={s['max_dd']:.2f}")
print("\nPer league:")
for lg in sorted(sub0["league"].unique()):
    sub_l = sub0[sub0["league"]==lg]
    s2 = stats(sub_l,"result","D","odds_draw")
    if s2: print(f"  {lg}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%, ex-top3={s2['roi_ex_top3']:.1f}%")
print("\nPer year:")
for yr in sorted(sub0["date"].dt.year.unique()):
    sub_y = sub0[sub0["date"].dt.year==yr]
    s2 = stats(sub_y,"result","D","odds_draw")
    if s2: print(f"  {yr}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")
# Also check both_strong+Draw across all odds
print("\nboth_strong | Draw — odds sensitivity:")
for lo,hi in [(3.0,4.0),(3.5,5.0),(4.0,5.5),(4.5,5.5),(5.0,6.5),(4.0,999)]:
    m2 = df["both_strong"] & (df["odds_draw"]>=lo) & (df["odds_draw"]<hi)
    s3 = stats(df[m2],"result","D","odds_draw")
    if s3 and s3["n"]>=20:
        print(f"  {lo}-{hi}: n={s3['n']}, ROI={s3['roi']:.1f}%, hit={s3['hit_rate']:.1f}%, ex-top3={s3['roi_ex_top3']:.1f}%")


# -- CANDIDATE 2: home_gf_high + Over25 ----------------------------------------
print(f"\n{'-'*60}")
print("CANDIDATE 2: home_gf_high | Over 2.5 (using est odds 1.88)")
print("home team scored >= 10 goals in last 5 matches")
print(f"{'-'*60}")
sub1 = df[df["home_gf_high"]]
s = stats(sub1,"over25",1,est_odds=1.88)
print(f"Overall: n={s['n']}, ROI={s['roi']:.1f}%, hit={s['hit_rate']:.1f}%, "
      f"ex-top3={s['roi_ex_top3']:.1f}%, dd={s['max_dd']:.2f}")
print("\nPer league:")
for lg in sorted(sub1["league"].unique()):
    s2 = stats(sub1[sub1["league"]==lg],"over25",1,est_odds=1.88)
    if s2: print(f"  {lg}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")
print("\nPer year:")
for yr in sorted(sub1["date"].dt.year.unique()):
    s2 = stats(sub1[sub1["date"].dt.year==yr],"over25",1,est_odds=1.88)
    if s2: print(f"  {yr}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")
# With odds band filter for 1X2 context
print("\nBase rate check: Over25 by home_gf bucket:")
for lo,hi,label in [(0,5,"0-4 goals"),(5,8,"5-7 goals"),(8,10,"8-9 goals"),(10,99,"10+ goals")]:
    m2 = (df["home_f_gf"]>=lo)&(df["home_f_gf"]<hi)
    s2 = stats(df[m2],"over25",1,est_odds=1.88)
    if s2: print(f"  {label}: n={s2['n']}, hit={s2['hit_rate']:.1f}%, ROI={s2['roi']:.1f}%")


# -- CANDIDATE 3: form_mismatch_H + Over25 -------------------------------------
print(f"\n{'-'*60}")
print("CANDIDATE 3: form_mismatch_H | Over 2.5")
print("home >= 10 pts last-5 AND away <= 5 pts last-5")
print(f"{'-'*60}")
sub2 = df[df["form_mismatch_H"]]
s = stats(sub2,"over25",1,est_odds=1.88)
print(f"Overall: n={s['n']}, ROI={s['roi']:.1f}%, hit={s['hit_rate']:.1f}%, "
      f"ex-top3={s['roi_ex_top3']:.1f}%, dd={s['max_dd']:.2f}")
print("\nPer league:")
for lg in sorted(sub2["league"].unique()):
    s2 = stats(sub2[sub2["league"]==lg],"over25",1,est_odds=1.88)
    if s2: print(f"  {lg}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")
print("\nPer year:")
for yr in sorted(sub2["date"].dt.year.unique()):
    s2 = stats(sub2[sub2["date"].dt.year==yr],"over25",1,est_odds=1.88)
    if s2: print(f"  {yr}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")


# -- CANDIDATE 4: home_streak_W3p + Draw + 4.50-5.50 -------------------------
print(f"\n{'-'*60}")
print("CANDIDATE 4: home_streak_W3p | Draw | odds 4.50-5.50")
print("home on 3+ game winning streak, draw odds 4.50-5.50")
print(f"{'-'*60}")
mask4 = df["home_streak_W3p"] & (df["odds_draw"]>=4.50) & (df["odds_draw"]<5.50)
sub4 = df[mask4]
s = stats(sub4,"result","D","odds_draw")
print(f"Overall: n={s['n']}, ROI={s['roi']:.1f}%, hit={s['hit_rate']:.1f}%, "
      f"avg_odds={s['avg_odds']:.2f}, ex-top3={s['roi_ex_top3']:.1f}%, dd={s['max_dd']:.2f}")
print("\nPer league:")
for lg in sorted(sub4["league"].unique()):
    s2 = stats(sub4[sub4["league"]==lg],"result","D","odds_draw")
    if s2: print(f"  {lg}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")
print("\nPer year:")
for yr in sorted(sub4["date"].dt.year.unique()):
    s2 = stats(sub4[sub4["date"].dt.year==yr],"result","D","odds_draw")
    if s2: print(f"  {yr}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")


# -- CANDIDATE 5: both_over + Over25 ------------------------------------------
print(f"\n{'-'*60}")
print("CANDIDATE 5: both_over | Over 2.5")
print("both teams Over25 rate >= 60% in last 5 (3733 matches!)")
print(f"{'-'*60}")
sub5 = df[df["both_over"]]
s = stats(sub5,"over25",1,est_odds=1.88)
print(f"Overall: n={s['n']}, ROI={s['roi']:.1f}%, hit={s['hit_rate']:.1f}%, "
      f"ex-top3={s['roi_ex_top3']:.1f}%, dd={s['max_dd']:.2f}")
print("\nPer league:")
for lg in sorted(sub5["league"].unique()):
    s2 = stats(sub5[sub5["league"]==lg],"over25",1,est_odds=1.88)
    if s2: print(f"  {lg}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")
print("\nPer year:")
for yr in sorted(sub5["date"].dt.year.unique()):
    s2 = stats(sub5[sub5["date"].dt.year==yr],"over25",1,est_odds=1.88)
    if s2: print(f"  {yr}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")


# -- CANDIDATE 6: form_mismatch_A + Draw + 3.20-3.80 -------------------------
print(f"\n{'-'*60}")
print("CANDIDATE 6: form_mismatch_A | Draw | odds 3.20-3.80")
print("away >= 10 pts last-5 AND home weak, draw odds 3.20-3.80")
print(f"{'-'*60}")
# Note: form_mismatch_A = strong_away & weak_home. Check in original full audit csv.
# Reconstruct: away_f_pts>=10 AND home_f_pts<=5
mask6 = (df["away_f_pts"]>=10) & (df["home_f_pts"]<=5) & (df["odds_draw"]>=3.20) & (df["odds_draw"]<3.80)
sub6 = df[mask6]
s = stats(sub6,"result","D","odds_draw")
print(f"Overall: n={s['n']}, ROI={s['roi']:.1f}%, hit={s['hit_rate']:.1f}%, "
      f"avg_odds={s['avg_odds']:.2f}, ex-top3={s['roi_ex_top3']:.1f}%, dd={s['max_dd']:.2f}")
print("\nPer league:")
for lg in sorted(sub6["league"].unique()):
    s2 = stats(sub6[sub6["league"]==lg],"result","D","odds_draw")
    if s2: print(f"  {lg}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")
print("\nPer year:")
for yr in sorted(sub6["date"].dt.year.unique()):
    s2 = stats(sub6[sub6["date"].dt.year==yr],"result","D","odds_draw")
    if s2: print(f"  {yr}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")


# -- CANDIDATE 7: home_streak_W3p + Away + 2.50-4.00 -------------------------
print(f"\n{'-'*60}")
print("CANDIDATE 7: home_streak_W3p | Away_win | odds 2.50-4.00")
print("home on 3+ win streak, away team priced 2.50-4.00")
print(f"{'-'*60}")
mask7 = df["home_streak_W3p"] & (df["odds_away"]>=2.50) & (df["odds_away"]<4.00)
sub7 = df[mask7]
s = stats(sub7,"result","A","odds_away")
print(f"Overall: n={s['n']}, ROI={s['roi']:.1f}%, hit={s['hit_rate']:.1f}%, "
      f"avg_odds={s['avg_odds']:.2f}, ex-top3={s['roi_ex_top3']:.1f}%, dd={s['max_dd']:.2f}")
print("\nPer league:")
for lg in sorted(sub7["league"].unique()):
    s2 = stats(sub7[sub7["league"]==lg],"result","A","odds_away")
    if s2: print(f"  {lg}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")
print("\nPer year:")
for yr in sorted(sub7["date"].dt.year.unique()):
    s2 = stats(sub7[sub7["date"].dt.year==yr],"result","A","odds_away")
    if s2: print(f"  {yr}: n={s2['n']}, ROI={s2['roi']:.1f}%, hit={s2['hit_rate']:.1f}%")


# -- ODDS SENSITIVITY: Over25 signals ------------------------------------------
print(f"\n{SEP}")
print("ODDS SENSITIVITY: home_gf_high + Over25 by implied probability")
print("(What if market already prices in high-scoring form?)")
print(SEP)
# Does market already discount the form? Split by odds_home odds as proxy for match competitiveness
sub_high = df[df["home_gf_high"]]
print("home_gf_high | Over25 by home_odds band:")
for lo,hi in [(1.30,1.60),(1.60,2.00),(2.00,2.75),(2.75,99)]:
    m2 = sub_high[(sub_high["odds_home"]>=lo)&(sub_high["odds_home"]<hi)]
    s2 = stats(m2,"over25",1,est_odds=1.88)
    if s2: print(f"  home_odds {lo}-{hi}: n={s2['n']}, hit={s2['hit_rate']:.1f}%, ROI={s2['roi']:.1f}%")

# Over25 by odds_draw as proxy for game balance
print("\nboth_over | Over25 by draw-odds band:")
sub_over = df[df["both_over"]]
for lo,hi in [(3.0,3.5),(3.5,4.0),(4.0,4.5),(4.5,5.5),(5.5,99)]:
    m2 = sub_over[(sub_over["odds_draw"]>=lo)&(sub_over["odds_draw"]<hi)]
    s2 = stats(m2,"over25",1,est_odds=1.88)
    if s2 and s2["n"]>=30:
        print(f"  draw_odds {lo}-{hi}: n={s2['n']}, hit={s2['hit_rate']:.1f}%, ROI={s2['roi']:.1f}%")


# -- BENCHMARK COMPARISON ------------------------------------------------------
print(f"\n{SEP}")
print("BENCHMARK COMPARISON: MLS Away edge>=0.04 vs top form patterns")
print(SEP)
print("MLS Away edge>=0.04 (combined 2024+2025 OOS): n=142, ROI=+9.1%")
print("Note: form patterns use historical odds estimates; MLS Away uses")
print("real backtest output with model edge calculation. Direct comparison")
print("requires caution (different methodology).\n")

candidates_vs_bench = [
    ("both_strong | Draw | 4.50-5.50", df["both_strong"] & (df["odds_draw"]>=4.5) & (df["odds_draw"]<5.5), "result","D","odds_draw",None),
    ("home_gf_high | Over25",          df["home_gf_high"],                                                   "over25",1,None,1.88),
    ("form_mismatch_H | Over25",       df["form_mismatch_H"],                                                 "over25",1,None,1.88),
    ("both_over | Over25",             df["both_over"],                                                       "over25",1,None,1.88),
    ("home_streak_W3p | Draw | 4.50-5.50", df["home_streak_W3p"] & (df["odds_draw"]>=4.5) & (df["odds_draw"]<5.5),"result","D","odds_draw",None),
]
for name, mask, tcol, tval, ocol, eodds in candidates_vs_bench:
    sub = df[mask]
    s = stats(sub, tcol, tval, ocol, eodds)
    if s:
        note = "(est odds)" if ocol is None else "(real odds)"
        print(f"  {name} {note}:")
        print(f"    n={s['n']}, ROI={s['roi']:.1f}%, ex-top3={s['roi_ex_top3']:.1f}%, "
              f"5-season positive={s['n_seasons'] if 'n_seasons' in s else 'see above'}")

print(f"\n{'-'*60}")
print("IMPORTANT CAVEAT:")
print("Form-pattern ROI uses estimated market odds (1.88 for Over25).")
print("Actual bookmaker odds vary 1.72-2.10+. The real edge above the")
print("market depends on whether the form signal is priced-in.")
print("A pattern with 59% hit rate at true market 1.88 is +11% ROI,")
print("but at market 1.72 (implied 58.1%) the same 59% is only +1.7%.")
print("These signals need odds-obtained validation, not just hit-rate.")
