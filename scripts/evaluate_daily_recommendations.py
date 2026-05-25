# -*- coding: utf-8 -*-
"""Post-match evaluator for Daily Probability Report recommendations.

Joins pre-match recommendation CSVs with actual final scores and evaluates
whether each recommended_market_type call was correct.

Usage:
    python scripts/evaluate_daily_recommendations.py \\
        --scores data/final_scores.csv \\
        [--reports-dir outputs/daily_reports] \\
        [--out-dir outputs/diagnostics]

Inputs:
    outputs/daily_reports/<league>_<date>_daily_report.csv   (auto-detected)
    data/final_scores.csv  (user-provided; see template)

Outputs:
    outputs/diagnostics/daily_recommendation_eval.csv
    outputs/diagnostics/daily_recommendation_eval_summary.md

This script is diagnostic only. No betting rules, paper-test rules,
ledger entries, ROI, or profitability claims are produced.
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scores", default=str(ROOT / "data" / "final_scores.csv"),
                   help="CSV with actual final scores")
    p.add_argument("--reports-dir", default=str(ROOT / "outputs" / "daily_reports"),
                   help="Directory containing daily report CSVs")
    p.add_argument("--out-dir", default=str(ROOT / "outputs" / "diagnostics"),
                   help="Directory for evaluation outputs")
    return p


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(name: str) -> str:
    """Simple normalisation for join: lowercase, strip, collapse spaces."""
    return " ".join(str(name).lower().strip().split())


def _actual_result(hg: int, ag: int) -> str:
    if hg > ag:
        return "H"
    if hg < ag:
        return "A"
    return "D"


def _ctrl_bucket(ctrl_10: float) -> str:
    if ctrl_10 >= 7.0:
        return "high (7-10)"
    if ctrl_10 >= 5.0:
        return "medium (5-7)"
    if ctrl_10 >= 3.0:
        return "low (3-5)"
    return "very_low (<3)"


def _chaos_bucket(chaos_10: float) -> str:
    if chaos_10 >= 6.0:
        return "high (6-10)"
    if chaos_10 >= 4.0:
        return "medium (4-6)"
    return "low (<4)"


def _parse_bool_success(val) -> Optional[bool]:
    """Robustly coerce a success value to True/False/None.

    Accepts: True, False, 1, 0, "True", "False", "true", "false",
             "TRUE", "FALSE", "1", "0", "yes", "no", "YES", "NO".
    Returns None for NaN, None, empty string, or unrecognised values.
    """
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        if pd.isna(val):
            return None
        return bool(val)
    s = str(val).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def _wilson_ci(n: int, hits: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95 % confidence interval for a proportion.

    Parameters
    ----------
    n    : total observations (denominator).
    hits : successful outcomes (numerator).
    z    : normal quantile; 1.96 gives a two-sided 95 % CI.

    Returns
    -------
    (lo, hi) : lower and upper bound, both clipped to [0, 1].
               Returns (0.0, 1.0) when n == 0.

    The Wilson interval is preferred over the Wald interval because it
    has better coverage near 0 and 1 and for small samples.
    """
    if n <= 0:
        return 0.0, 1.0
    p_hat = hits / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p_hat + z2 / (2 * n)) / denom
    half = z * ((p_hat * (1 - p_hat) / n + z2 / (4 * n * n)) ** 0.5) / denom
    lo = max(0.0, centre - half)
    hi = min(1.0, centre + half)
    # Ensure integer arithmetic edge-cases (p=0 or p=1) land exactly on bounds
    if hits <= 0:
        lo = 0.0
    if hits >= n:
        hi = 1.0
    return lo, hi


def _tier_score_bucket(score) -> str:
    """Map a numeric market_tier_score (0-100) to a display bucket label."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "unknown"
    if s >= 80:
        return "80+"
    if s >= 70:
        return "70-79"
    if s >= 50:
        return "50-69"
    return "<50"


# ---------------------------------------------------------------------------
# Success logic per recommended_market_type
# ---------------------------------------------------------------------------

def _direction_success(row: pd.Series) -> Optional[bool]:
    """DIRECTION: read must match actual result."""
    read = str(row.get("recommended_market_read", "")).lower()
    actual = str(row.get("actual_result", ""))
    if not actual:
        return None
    if "home" in read:
        return actual == "H"
    if "away" in read:
        return actual == "A"
    if "draw" in read:
        return actual == "D"
    return None  # can't determine from read string


def _double_chance_success(row: pd.Series) -> Optional[bool]:
    """DOUBLE_CHANCE: 1X covers H or D; X2 covers A or D."""
    read = str(row.get("recommended_market_read", "")).lower()
    actual = str(row.get("actual_result", ""))
    if not actual:
        return None
    if "1x" in read or "home_or_draw" in read:
        return actual in {"H", "D"}
    if "x2" in read or "away_or_draw" in read:
        return actual in {"A", "D"}
    # Fallback: if model said home direction, treat as 1X
    likely = str(row.get("likely_1x2", "")).strip()
    if likely == "Home":
        return actual in {"H", "D"}
    if likely == "Away":
        return actual in {"A", "D"}
    return None


def _btts_over_success(row: pd.Series) -> Optional[bool]:
    """BTTS_OVER: success if Over 2.5 goals OR both teams scored (OR logic).

    Computed directly from raw home_goals / away_goals to avoid any dependency
    on pre-derived actual_over25 / actual_btts columns (which may have dtype
    or NaN-propagation issues after partial .loc assignment).

    Success conditions (either is sufficient):
      - actual_over25 : total goals > 2.5
      - actual_btts   : home_goals > 0 AND away_goals > 0
    """
    hg = row.get("home_goals")
    ag = row.get("away_goals")
    if pd.isna(hg) or pd.isna(ag):
        return None
    hg = float(hg)
    ag = float(ag)
    actual_over25 = (hg + ag) > 2.5          # e.g. 3+ goals total
    actual_btts   = (hg > 0) and (ag > 0)    # both teams on the scoresheet
    return actual_over25 or actual_btts


def _subtype_success(row: pd.Series) -> Optional[bool]:
    """Evaluate success for a specific recommended_market_subtype.

    Each subtype has a precise, unambiguous success condition computed directly
    from raw goals — no pre-derived columns needed.

    Subtypes that are diagnostic-only (AVOID_*, OBSERVE_*, NONE) return None.
    """
    subtype = str(row.get("recommended_market_subtype", "")).strip().upper()
    if not subtype or subtype in ("NONE", "AVOID_VOLATILE", "AVOID_LOW_CONTROL",
                                  "OBSERVE_DATA_WARNING"):
        return None

    hg = row.get("home_goals")
    ag = row.get("away_goals")
    if pd.isna(hg) or pd.isna(ag):
        return None
    hg = float(hg)
    ag = float(ag)
    total = hg + ag
    actual = "H" if hg > ag else ("A" if ag > hg else "D")

    if subtype == "OVER_25":
        return total > 2.5

    if subtype == "BTTS":
        return (hg > 0) and (ag > 0)

    if subtype == "BOTH_OVER25_BTTS":
        # Both conditions must hold: stricter than BTTS_OVER OR logic.
        return (total > 2.5) and (hg > 0) and (ag > 0)

    if subtype == "UNDER_25":
        return total < 2.5

    if subtype == "UNDER_35":
        return total < 3.5

    if subtype == "DIRECTION_HOME":
        return actual == "H"

    if subtype == "DIRECTION_AWAY":
        return actual == "A"

    if subtype == "DOUBLE_CHANCE_1X":
        return actual in ("H", "D")

    if subtype == "DOUBLE_CHANCE_X2":
        return actual in ("A", "D")

    return None


def _under_success(row: pd.Series) -> Optional[bool]:
    """UNDER: success if under 3.5 goals."""
    under35 = row.get("actual_under35")
    if pd.isna(under35):
        return None
    return bool(under35)


def _avoid_success(row: pd.Series) -> Optional[bool]:
    """AVOID: success if game was indeed unpredictable / messy.

    Operationalised as any of:
    - predicted direction was wrong (model 1X2 miss)
    - total goals >= 4
    - draw or upset occurred (away win when home was favourite or vice versa)
    - confidence was NO-CONFIDENCE
    """
    actual = str(row.get("actual_result", ""))
    likely = str(row.get("likely_1x2", "")).strip()
    conf   = str(row.get("confidence", "")).upper()
    total  = row.get("actual_total_goals", 0)
    if not actual:
        return None
    direction_wrong = (actual != likely[0] if likely else False)
    high_scoring    = float(total) >= 4 if not pd.isna(total) else False
    is_draw         = actual == "D"
    no_conf         = conf == "NO-CONFIDENCE"
    return direction_wrong or high_scoring or is_draw or no_conf


# ---------------------------------------------------------------------------
# League profile summary helper  (isolated for testability)
# ---------------------------------------------------------------------------

#: Ordered tiers for league_adjusted_strength display
_STRENGTH_TIERS = ["HIGH", "MEDIUM", "LOW", "SUPPRESSED"]


def build_league_profile_sections(scored: pd.DataFrame) -> list[str]:
    """Return Markdown summary lines for league-profile fields.

    Works on any DataFrame that contains a ``success`` boolean column plus
    (some or all of) the six league profile fields added by
    ``apply_league_market_profile()``.

    If none of the league profile fields are present the function returns a
    single informational line instead of crashing.

    Parameters
    ----------
    scored:
        Subset of the evaluated DataFrame where ``success`` is not null —
        i.e. the same ``scored`` slice used for the rest of the summary.

    Returns
    -------
    list[str]
        Markdown lines (no trailing newline needed; the caller joins them).
    """
    _LP_COLS = {
        "league_adjusted_strength",
        "league_profile",
        "league_warning_flags",
        "league_preferred_subtype",
        "league_suppressed_subtype",
    }
    present = _LP_COLS & set(scored.columns)

    lines: list[str] = []
    lines.append("## League Profile Analysis  [diagnostic only]")
    lines.append("")

    if not present:
        lines.append(
            "  league profile fields not available in this report set — "
            "re-run daily report scripts to include them."
        )
        lines.append("")
        return lines

    # ------------------------------------------------------------------ 6.1
    if "league_adjusted_strength" in scored.columns:
        lines.append("### 6.1 Success Rate by league_adjusted_strength")
        lines.append("")
        lines.append(f"  {'Strength':<14} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("  " + "-" * 38)
        col = scored["league_adjusted_strength"].fillna("UNKNOWN").str.upper()
        for tier in _STRENGTH_TIERS + sorted(set(col.unique()) - set(_STRENGTH_TIERS)):
            grp = scored[col == tier]
            if grp.empty:
                continue
            n    = len(grp)
            hits = int(grp["success"].sum())
            rate = hits / n if n else 0.0
            lines.append(f"  {tier:<14} {n:>4} {hits:>4} {rate:7.1%}")
        lines.append("")

    # ------------------------------------------------------------------ 6.2
    if "league_profile" in scored.columns:
        lines.append("### 6.2 Success Rate by league_profile")
        lines.append("")
        lines.append(f"  {'Profile':<32} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("  " + "-" * 52)
        col = scored["league_profile"].fillna("unknown")
        for profile, grp in scored.groupby(col):
            n    = len(grp)
            hits = int(grp["success"].sum())
            rate = hits / n if n else 0.0
            lines.append(f"  {profile:<32} {n:>4} {hits:>4} {rate:7.1%}")
        lines.append("")

    # ------------------------------------------------------------------ 6.3
    if "league_warning_flags" in scored.columns:
        lines.append("### 6.3 Success Rate — warned vs not warned")
        lines.append("")
        lines.append(f"  {'Category':<24} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("  " + "-" * 44)
        has_warn = (
            scored["league_warning_flags"]
            .fillna("")
            .str.strip()
            .str.len() > 0
        )
        for label, mask in [("has warning_flag", has_warn), ("no warning_flag", ~has_warn)]:
            grp  = scored[mask]
            n    = len(grp)
            if n == 0:
                continue
            hits = int(grp["success"].sum())
            rate = hits / n
            lines.append(f"  {label:<24} {n:>4} {hits:>4} {rate:7.1%}")
        lines.append("")

    # ------------------------------------------------------------------ 6.4  preferred subtype match
    if "league_preferred_subtype" in scored.columns and "recommended_market_subtype" in scored.columns:
        lines.append("### 6.4 Success Rate — recommended subtype is league-preferred")
        lines.append("")
        lines.append(f"  {'Category':<30} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("  " + "-" * 50)

        def _is_preferred(row: pd.Series) -> bool:
            sub  = str(row.get("recommended_market_subtype", "") or "").strip().upper()
            pref = str(row.get("league_preferred_subtype",   "") or "").upper()
            if not sub or not pref:
                return False
            return sub in {p.strip() for p in pref.split(",")}

        scored = scored.copy()
        scored["_is_preferred"] = scored.apply(_is_preferred, axis=1)
        for label, mask in [
            ("subtype is preferred",     scored["_is_preferred"]),
            ("subtype not preferred",    ~scored["_is_preferred"]),
        ]:
            grp  = scored[mask]
            n    = len(grp)
            if n == 0:
                continue
            hits = int(grp["success"].sum())
            rate = hits / n
            lines.append(f"  {label:<30} {n:>4} {hits:>4} {rate:7.1%}")
        lines.append("")

    # ------------------------------------------------------------------ 6.5  suppressed subtype match
    if "league_suppressed_subtype" in scored.columns and "recommended_market_subtype" in scored.columns:
        lines.append("### 6.5 Success Rate — recommended subtype is league-suppressed")
        lines.append("")
        lines.append(f"  {'Category':<30} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("  " + "-" * 50)

        def _is_suppressed(row: pd.Series) -> bool:
            sub  = str(row.get("recommended_market_subtype",  "") or "").strip().upper()
            supp = str(row.get("league_suppressed_subtype",   "") or "").upper()
            if not sub or not supp:
                return False
            return sub in {s.strip() for s in supp.split(",")}

        scored["_is_suppressed"] = scored.apply(_is_suppressed, axis=1)
        for label, mask in [
            ("subtype is suppressed",   scored["_is_suppressed"]),
            ("subtype not suppressed",  ~scored["_is_suppressed"]),
        ]:
            grp  = scored[mask]
            n    = len(grp)
            if n == 0:
                continue
            hits = int(grp["success"].sum())
            rate = hits / n
            lines.append(f"  {label:<30} {n:>4} {hits:>4} {rate:7.1%}")
        lines.append("")

    # ------------------------------------------------------------------ 6.6  comparison table
    lines.append("### 6.6 Comparison Summary")
    lines.append("")

    if "league_adjusted_strength" in scored.columns:
        lines.append("  **Adjusted Strength tiers:**")
        col = scored["league_adjusted_strength"].fillna("UNKNOWN").str.upper()
        for tier in _STRENGTH_TIERS:
            grp = scored[col == tier]
            if grp.empty:
                continue
            n    = len(grp)
            hits = int(grp["success"].sum())
            lines.append(f"    {tier:<14}: {hits}/{n}  ({hits/n:.1%})")
        lines.append("")

    if "league_warning_flags" in scored.columns:
        lines.append("  **Warning flags:**")
        has_warn = scored["league_warning_flags"].fillna("").str.strip().str.len() > 0
        for label, mask in [("Warned", has_warn), ("Not warned", ~has_warn)]:
            grp = scored[mask]
            n   = len(grp)
            if n == 0:
                continue
            hits = int(grp["success"].sum())
            lines.append(f"    {label:<14}: {hits}/{n}  ({hits/n:.1%})")
        lines.append("")

    if "league_suppressed_subtype" in scored.columns and "recommended_market_subtype" in scored.columns:
        lines.append("  **Suppressed vs non-suppressed subtype:**")
        def _supp_flag(row):
            sub  = str(row.get("recommended_market_subtype",  "") or "").strip().upper()
            supp = str(row.get("league_suppressed_subtype",   "") or "").upper()
            if not sub or not supp:
                return False
            return sub in {s.strip() for s in supp.split(",")}
        scored["_supp2"] = scored.apply(_supp_flag, axis=1)
        for label, mask in [("Suppressed", scored["_supp2"]), ("Not suppressed", ~scored["_supp2"])]:
            grp = scored[mask]
            n   = len(grp)
            if n == 0:
                continue
            hits = int(grp["success"].sum())
            lines.append(f"    {label:<14}: {hits}/{n}  ({hits/n:.1%})")
        lines.append("")

    lines.append(
        "  *League profile sections are diagnostic only. "
        "No betting claims are made.*"
    )
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# Phase-10: Ensemble analysis section
# ---------------------------------------------------------------------------

def _append_ensemble_analysis_section(lines: list, scored) -> None:
    """Append the ENSEMBLE ANALYSIS section to *lines*.

    Warns when ensemble diagnostics are absent or unpopulated.
    No betting, ROI, or staking logic.
    """
    ensemble_agreement_col = "ensemble_agreement"
    ensemble_note_col = "ensemble_note"
    success_col: str | None = None
    for col in ("type_success", "subtype_success"):
        if col in scored.columns and scored[col].notna().any():
            success_col = col
            break

    if success_col is None:
        return

    if ensemble_agreement_col not in scored.columns:
        lines.append("")
        lines.append("=== ENSEMBLE ANALYSIS ===")
        lines.append("")
        lines.append("WARNING: ensemble_agreement column is unavailable.")
        lines.append("")
        return

    agreement_values = scored[ensemble_agreement_col].fillna("").astype(str).str.strip()
    if agreement_values.eq("").all():
        lines.append("")
        lines.append("=== ENSEMBLE ANALYSIS ===")
        lines.append("")
        lines.append("WARNING: ensemble_agreement is blank for all rows.")
        lines.append("")
        return

    lines.append("")
    lines.append("=== ENSEMBLE ANALYSIS ===")
    lines.append("")

    def _hit_rate_ci(mask):
        sub = scored[mask & scored[success_col].notna()]
        n = len(sub)
        hits = int(sub[success_col].sum()) if n else 0
        rate = hits / n if n else 0.0
        lo, hi = _wilson_ci(n, hits)
        return n, hits, rate, lo, hi

    # SUPER_A_TIER
    if "market_tier" in scored.columns:
        super_a = scored["market_tier"].astype(str).str.strip() == "SUPER_A_TIER"
        n, hits, rate, lo, hi = _hit_rate_ci(super_a)
        lines.append("SUPER_A_TIER:")
        lines.append(f"  n={n}, Hit Rate: {rate:.1%} (CI: {lo:.1%}-{hi:.1%})")
        lines.append("")

    lines.append("SUCCESS RATE BY ENSEMBLE AGREEMENT:")
    agreement_norm = scored[ensemble_agreement_col].fillna("").astype(str).str.strip().str.upper()
    order = ["HIGH", "MEDIUM", "LOW", "NONE"]
    non_empty_agreements = set(agreement_norm[agreement_norm != ""])
    present = [v for v in order if v in non_empty_agreements]
    present += sorted(non_empty_agreements - set(order))
    for label in present:
        n, hits, rate, _, _ = _hit_rate_ci(agreement_norm == label)
        lines.append(f"  {label:<8} n={n}, Hit Rate: {rate:.1%}")
    lines.append("")

    if ensemble_note_col not in scored.columns:
        lines.append("WARNING: ensemble_note column is unavailable.")
        lines.append("")
        return

    # ENSEMBLE_DISAGREEMENT (downgraded matches)
    dis_mask = scored[ensemble_note_col].astype(str).str.strip() == "DISAGREEMENT"
    n, hits, rate, _, _ = _hit_rate_ci(dis_mask)
    lines.append("ENSEMBLE_DISAGREEMENT (downgraded):")
    lines.append(f"  n={n}, Hit Rate: {rate:.1%}")
    lines.append("")

    # ENSEMBLE_SPLIT
    split_mask = scored[ensemble_note_col].astype(str).str.strip() == "SPLIT"
    n, hits, rate, _, _ = _hit_rate_ci(split_mask)
    lines.append("ENSEMBLE_SPLIT:")
    lines.append(f"  n={n}, Hit Rate: {rate:.1%}")
    lines.append("")

    lines.append(
        "Zeigt ob Ensemble-Konsens mit höherer Erfolgsrate korreliert."
    )
    lines.append("")


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def evaluate(reports_dir: Path, scores_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Load pre-match recommendation CSVs ----
    csvs = sorted(reports_dir.glob("*_daily_report.csv"))
    if not csvs:
        print(f"[WARN] No daily report CSVs found in {reports_dir}")
        print("       Run the daily report scripts first to generate them.")
        print("       Expected pattern: outputs/daily_reports/<league>_<date>_daily_report.csv")
        return

    pre = pd.concat([pd.read_csv(f) for f in csvs], ignore_index=True)
    print(f"Loaded {len(pre)} pre-match rows from {len(csvs)} CSV(s):")
    for f in csvs:
        print(f"  {f.name}")

    # ---- Load actual scores ----
    if not scores_path.exists():
        print(f"\n[WARN] Final scores file not found: {scores_path}")
        print("       Create it with columns: date,league,home_team,away_team,home_goals,away_goals")
        print("       Template written to data/final_scores_template.csv")
        _write_template(scores_path.parent / "final_scores_template.csv", pre)
        return

    scores = pd.read_csv(scores_path, dtype={"home_goals": str, "away_goals": str,
                                              "verified": str, "source_note": str})

    # --- verified=yes gate ---------------------------------------------------
    # Only rows explicitly marked verified=yes are used.
    # All other rows (unverified, unknown, blank) are silently ignored.
    if "verified" not in scores.columns:
        print("  [STOP] 'verified' column missing from final_scores.csv.")
        print("         Add a 'verified' column and set to 'yes' for confirmed results.")
        print("         No scores will be used until at least one row is verified=yes.")
        return

    scores_verified = scores[scores["verified"].str.strip().str.lower() == "yes"].copy()
    total_rows      = len(scores)
    verified_count  = len(scores_verified)
    unverified_count = total_rows - verified_count

    print(f"\nLoaded {total_rows} rows from {scores_path}")
    print(f"  verified=yes : {verified_count}")
    print(f"  unverified   : {unverified_count}  (skipped)")

    if verified_count == 0:
        print()
        print("  [STOP] No rows with verified=yes found.")
        print("         Fill in actual scores in data/final_scores.csv,")
        print("         set verified=yes for each confirmed result,")
        print("         then re-run this script.")
        print()
        print("  Waiting for manually entered results. No evaluation performed.")
        return

    # Work only with verified rows from here on
    scores = scores_verified
    scores["home_goals"] = pd.to_numeric(scores["home_goals"], errors="coerce")
    scores["away_goals"] = pd.to_numeric(scores["away_goals"], errors="coerce")

    # Drop any verified rows where goals are still missing/non-numeric
    goals_ok = scores["home_goals"].notna() & scores["away_goals"].notna()
    if not goals_ok.all():
        bad = (~goals_ok).sum()
        print(f"  [WARN] {bad} verified row(s) have missing/non-numeric goals — skipped.")
        scores = scores[goals_ok].copy()

    if scores.empty:
        print("  [STOP] No verified rows with valid numeric goals. Nothing to evaluate.")
        return

    # ---- Normalise join keys ----
    for df in [pre, scores]:
        df["_home_key"] = df["home_team"].apply(_norm)
        df["_away_key"] = df["away_team"].apply(_norm)
        df["_league_key"] = df["league"].apply(_norm) if "league" in df.columns else "?"

    # Join on league + home + away
    merge_cols = ["_home_key", "_away_key", "_league_key", "home_goals", "away_goals"]
    if "source_note" in scores.columns:
        merge_cols.append("source_note")
    merged = pre.merge(scores[merge_cols], on=["_home_key", "_away_key", "_league_key"], how="left")

    # Fallback: retry without league key if everything is NaN
    unmatched_mask = merged["home_goals"].isna()
    if unmatched_mask.all():
        print("  [NOTE] League-key join returned 0 — retrying without league key")
        fallback_cols = ["_home_key", "_away_key", "home_goals", "away_goals"]
        if "source_note" in scores.columns:
            fallback_cols.append("source_note")
        merged = pre.merge(scores[fallback_cols], on=["_home_key", "_away_key"], how="left")
        unmatched_mask = merged["home_goals"].isna()

    matched = (~unmatched_mask).sum()
    print(f"  Joined: {matched} verified result(s) matched to pre-match rows")
    if matched == 0:
        print("  [WARN] Verified rows found but team names did not join.")
        print("         Check home_team / away_team spelling in final_scores.csv matches")
        print("         the names in outputs/daily_reports/*.csv exactly.")
        return

    # ---- Compute actuals ----
    m = merged.copy()
    m["home_goals"] = pd.to_numeric(m["home_goals"], errors="coerce")
    m["away_goals"] = pd.to_numeric(m["away_goals"], errors="coerce")

    has_score = m["home_goals"].notna() & m["away_goals"].notna()
    m.loc[has_score, "actual_result"]      = m.loc[has_score].apply(
        lambda r: _actual_result(int(r["home_goals"]), int(r["away_goals"])), axis=1)
    m.loc[has_score, "actual_total_goals"] = m.loc[has_score, "home_goals"] + m.loc[has_score, "away_goals"]
    m.loc[has_score, "actual_over25"]      = (m.loc[has_score, "actual_total_goals"] > 2.5).astype(int)
    m.loc[has_score, "actual_under25"]     = (m.loc[has_score, "actual_total_goals"] < 2.5).astype(int)
    m.loc[has_score, "actual_under35"]     = (m.loc[has_score, "actual_total_goals"] < 3.5).astype(int)
    m.loc[has_score, "actual_btts"]        = (
        (m.loc[has_score, "home_goals"] > 0) & (m.loc[has_score, "away_goals"] > 0)
    ).astype(int)
    m.loc[has_score, "home_or_draw_1x"]    = (m.loc[has_score, "actual_result"].isin(["H", "D"])).astype(int)
    m.loc[has_score, "away_or_draw_x2"]    = (m.loc[has_score, "actual_result"].isin(["A", "D"])).astype(int)

    # ---- BTTS_OVER sub-signals (computed directly from goals, not from derived cols) ----
    # over25_hit  : total goals > 2.5  (one sufficient condition for BTTS_OVER success)
    # btts_hit    : both teams scored  (other sufficient condition for BTTS_OVER success)
    # btts_over_or_success : True if EITHER hit — the canonical BTTS_OVER success value
    # These three are all written to the detail CSV so the ambiguity is fully visible.
    m.loc[has_score, "over25_hit"] = (
        (m.loc[has_score, "home_goals"] + m.loc[has_score, "away_goals"]) > 2.5
    ).astype(int)
    m.loc[has_score, "btts_hit"] = (
        (m.loc[has_score, "home_goals"] > 0) & (m.loc[has_score, "away_goals"] > 0)
    ).astype(int)
    m.loc[has_score, "btts_over_or_success"] = (
        (m.loc[has_score, "over25_hit"] == 1) | (m.loc[has_score, "btts_hit"] == 1)
    ).astype(int)
    m.loc[has_score, "under25_hit"] = m.loc[has_score, "actual_under25"]

    # ---- Evaluate by market type ----
    evaluators = {
        "DIRECTION":     _direction_success,
        "DOUBLE_CHANCE": _double_chance_success,
        "BTTS_OVER":     _btts_over_success,
        "UNDER":         _under_success,
        "AVOID":         _avoid_success,
        "OBSERVE_ONLY":  lambda _: None,  # no binary
    }

    def eval_row(row):
        mtype = str(row.get("recommended_market_type", ""))
        fn = evaluators.get(mtype)
        if fn is None:
            return None
        return fn(row)

    m["type_success"] = m.apply(eval_row, axis=1).apply(_parse_bool_success)

    # ---- Subtype success (more precise, per-subtype success criteria) --------
    m["subtype_success"] = m.apply(_subtype_success, axis=1).apply(_parse_bool_success)

    # Clean up temp keys
    m = m.drop(columns=[c for c in m.columns if c.startswith("_")])

    # ---- Save detailed CSV — preserve tier fields ----
    # Column order: put market_tier fields after standard fields if present
    eval_csv = out_dir / "daily_recommendation_eval.csv"
    m.to_csv(eval_csv, index=False)
    print(f"\nDetailed results saved: {eval_csv}")

    # ---- Build summary ----
    # Only rows with a verified score AND a non-null actual_result are included.
    # Unmatched rows (no verified score) are never evaluated.
    m_with_score = m[m["home_goals"].notna() & m["actual_result"].notna()].copy()
    scored = m_with_score[m_with_score["type_success"].notna()].copy()
    total_scored = len(scored)

    lines: list[str] = []
    lines.append("# Daily Recommendation Evaluation Summary")
    lines.append("")
    lines.append(f"- Total pre-match rows      : {len(m)}")
    lines.append(f"- Verified scores matched   : {matched}  (verified=yes only)")
    lines.append(f"- Unverified / not matched  : {len(m) - matched}  (excluded from all calculations)")
    lines.append(f"- Evaluatable rows          : {total_scored}  (matched + not OBSERVE_ONLY)")
    lines.append("")
    lines.append("*All success rates are based on verified=yes rows only.*")
    lines.append("")
    lines.append("")

    # By market type
    lines.append("## Success Rate by Recommended Market Type")
    lines.append("")
    lines.append(f"{'Type':<16} {'n':>4} {'hits':>4} {'rate':>7}  Notes")
    lines.append("-" * 55)
    type_rows = []
    btts_over_breakdown: dict = {}   # populated when BTTS_OVER is encountered
    for mtype, grp in scored.groupby("recommended_market_type"):
        n    = len(grp)
        hits = int(grp["type_success"].sum())
        rate = hits / n if n else 0.0
        notes = ""
        if mtype == "BTTS_OVER":
            # hits / rate already use OR logic (from _btts_over_success computed on raw goals)
            o_hit  = int(grp["over25_hit"].sum())  if "over25_hit"  in grp.columns else 0
            bt_hit = int(grp["btts_hit"].sum())    if "btts_hit"    in grp.columns else 0
            o_rate  = o_hit  / n if n else 0.0
            bt_rate = bt_hit / n if n else 0.0
            notes = (
                f"OR-success={hits}/{n} ({rate:.1%})  "
                f"over2.5={o_hit}/{n} ({o_rate:.1%})  "
                f"btts={bt_hit}/{n} ({bt_rate:.1%})"
            )
            btts_over_breakdown = {
                "n": n, "or_hits": hits, "or_rate": rate,
                "over25_hits": o_hit, "over25_rate": o_rate,
                "btts_hits": bt_hit, "btts_rate": bt_rate,
            }
        elif mtype == "UNDER":
            u25 = int(grp["under25_hit"].sum()) if "under25_hit" in grp.columns else "?"
            notes = f"under25_hit={u25}/{n}"
        lines.append(f"  {mtype:<14} {n:>4} {hits:>4} {rate:7.1%}  {notes}")
        type_rows.append({"type": mtype, "n": n, "hits": hits, "rate": rate})

    # ---- BTTS_OVER detail block (separate section, full transparency) --------
    if btts_over_breakdown:
        bd = btts_over_breakdown
        lines.append("")
        lines.append("### BTTS_OVER Detail (OR logic)")
        lines.append("")
        lines.append(
            f"  Success rule   : actual_over2.5  OR  actual_btts  (either is sufficient)"
        )
        lines.append(
            f"  OR success     : {bd['or_hits']}/{bd['n']}  ({bd['or_rate']:.1%})"
        )
        lines.append(
            f"  Over 2.5 alone : {bd['over25_hits']}/{bd['n']}  ({bd['over25_rate']:.1%})"
        )
        lines.append(
            f"  BTTS alone     : {bd['btts_hits']}/{bd['n']}  ({bd['btts_rate']:.1%})"
        )
        # Data-driven note: how much independent value does Over2.5 add beyond BTTS?
        over25_only_hits = bd["or_hits"] - bd["btts_hits"]   # hits contributed by Over2.5 alone
        if over25_only_hits > 0:
            _note = (
                f"Over2.5 contributed {over25_only_hits} independent hit(s) not covered by BTTS "
                f"(OR rate {bd['or_rate']:.1%} > BTTS-only {bd['btts_rate']:.1%})."
            )
        elif bd["or_rate"] == bd["btts_rate"]:
            _note = (
                f"All Over2.5 hits were also BTTS hits in this sample — "
                f"OR rate equals BTTS-only rate ({bd['btts_rate']:.1%}). "
                "Over2.5 added no independent lift here."
            )
        else:
            _note = (
                f"OR rate ({bd['or_rate']:.1%}) vs BTTS-only ({bd['btts_rate']:.1%}) — "
                "check for score overlap."
            )
        lines.append(f"  Note: {_note}")
        lines.append("")
    lines.append("")

    # ---- Success rate by recommended_market_subtype (more precise layer) -----
    if "recommended_market_subtype" in scored.columns:
        sub_scored = scored[scored["subtype_success"].notna()].copy()
        if not sub_scored.empty:
            lines.append("## Success Rate by Recommended Market Subtype")
            lines.append("")
            lines.append(
                "  Subtype success uses a precise, single-condition rule per subtype "
                "(e.g. OVER_25 = total > 2.5 only; BTTS = both scored only)."
            )
            lines.append("")
            lines.append(f"  {'Subtype':<22} {'n':>4} {'hits':>4} {'rate':>7}  {'Parent type'}")
            lines.append("  " + "-" * 60)
            sub_type_rows = []
            for subtype, sg in sub_scored.groupby("recommended_market_subtype"):
                sn   = len(sg)
                shits = int(sg["subtype_success"].sum())
                srate = shits / sn if sn else 0.0
                # show dominant parent type for context
                parent = sg["recommended_market_type"].mode().iloc[0] if len(sg) > 0 else "?"
                lines.append(f"  {subtype:<22} {sn:>4} {shits:>4} {srate:7.1%}  {parent}")
                sub_type_rows.append({
                    "subtype": subtype, "n": sn, "hits": shits, "rate": srate
                })
            lines.append("")

            # BTTS_OVER split comparison — the key diagnostic
            btts_over_sub = sub_scored[sub_scored["recommended_market_type"] == "BTTS_OVER"]
            if not btts_over_sub.empty:
                lines.append("  ### BTTS_OVER Split Comparison")
                lines.append("")
                lines.append(
                    "  BTTS_OVER (type-level OR):  "
                    f"{int(scored[scored['recommended_market_type']=='BTTS_OVER']['type_success'].sum())}/"
                    f"{len(scored[scored['recommended_market_type']=='BTTS_OVER'])}  "
                    f"({scored[scored['recommended_market_type']=='BTTS_OVER']['type_success'].mean():.1%})"
                )
                for subtype, sg in btts_over_sub.groupby("recommended_market_subtype"):
                    sv = int(sg["subtype_success"].sum())
                    lines.append(
                        f"  Subtype {subtype:<20}: {sv}/{len(sg)}  ({sv/len(sg):.1%})"
                    )
                lines.append(
                    "  Interpretation: a subtype with a higher rate than the OR rate "
                    "represents a more reliable narrower call."
                )
                lines.append("")
        else:
            lines.append("## Subtype Evaluation")
            lines.append("  (No subtype column in pre-match CSVs — re-run daily reports)")
            lines.append("")

    # ---- Success Rate by Market Tier -----------------------------------------
    if "market_tier" in scored.columns:
        tier_ev = scored[scored["market_tier"].notna() & (scored["market_tier"].astype(str).str.strip() != "")]
        if not tier_ev.empty:
            lines.append("## Success Rate by Market Tier")
            lines.append("")
            lines.append(f"  {'Tier':<14} {'n':>4} {'hits':>4} {'rate':>7}  {'95% CI (Wilson)'}")
            lines.append("  " + "-" * 56)
            tier_order = ["A_TIER", "B_TIER", "C_TIER", "DOWNGRADE", "HARD_NO_GO", "OBSERVE_ONLY"]
            present_tiers = tier_ev["market_tier"].unique().tolist()
            ordered = [t for t in tier_order if t in present_tiers]
            ordered += [t for t in present_tiers if t not in tier_order]
            for tier in ordered:
                grp = tier_ev[tier_ev["market_tier"] == tier]
                n = len(grp)
                ts_col = grp["type_success"]
                hits = int(ts_col.sum()) if n else 0
                rate = hits / n if n else 0.0
                lo, hi = _wilson_ci(n, hits)
                ci_str = f"[{lo:.1%}, {hi:.1%}]"
                lines.append(f"  {tier:<14} {n:>4} {hits:>4} {rate:7.1%}  {ci_str}")
            lines.append("")

            # A+B combined line with Wilson CI
            ab = tier_ev[tier_ev["market_tier"].isin(["A_TIER", "B_TIER"])]
            if not ab.empty:
                ab_n = len(ab)
                ab_hits = int(ab["type_success"].sum())
                ab_lo, ab_hi = _wilson_ci(ab_n, ab_hits)
                lines.append(
                    f"  A_TIER + B_TIER combined: {ab_hits}/{ab_n} "
                    f"({ab_hits/ab_n:.1%})  95% CI [{ab_lo:.1%}, {ab_hi:.1%}]"
                )
                lines.append("")

    # ---- Success Rate by Market Tier Score Bucket ----------------------------
    if "market_tier_score" in scored.columns:
        tier_score_ev = scored[scored["market_tier_score"].notna()].copy()
        if not tier_score_ev.empty:
            tier_score_ev["_score_bucket"] = tier_score_ev["market_tier_score"].apply(_tier_score_bucket)
            lines.append("## Success Rate by Market Tier Score Bucket")
            lines.append("")
            lines.append(f"  {'Score bucket':<14} {'n':>4} {'hits':>4} {'rate':>7}  {'95% CI (Wilson)'}")
            lines.append("  " + "-" * 56)
            bucket_order = ["80+", "70-79", "50-69", "<50"]
            present_buckets = tier_score_ev["_score_bucket"].unique().tolist()
            ordered_buckets = [b for b in bucket_order if b in present_buckets]
            ordered_buckets += [b for b in present_buckets if b not in bucket_order]
            for bucket in ordered_buckets:
                grp = tier_score_ev[tier_score_ev["_score_bucket"] == bucket]
                n = len(grp)
                hits = int(grp["type_success"].sum()) if n else 0
                rate = hits / n if n else 0.0
                lo, hi = _wilson_ci(n, hits)
                ci_str = f"[{lo:.1%}, {hi:.1%}]"
                lines.append(f"  {bucket:<14} {n:>4} {hits:>4} {rate:7.1%}  {ci_str}")
            lines.append("")

    # ---- Sektion A: Miss Cluster Analysis ------------------------------------
    _append_miss_cluster_section(lines, out_dir)

    # ---- Sektion B: Calibration Summary --------------------------------------
    _append_calibration_section(lines, out_dir)

    # ---- Sektion C: Drift Monitor --------------------------------------------
    _append_drift_section(lines, out_dir)

    # OBSERVE_ONLY separately
    obs = m[m["recommended_market_type"] == "OBSERVE_ONLY"]
    if len(obs) > 0 and obs["actual_result"].notna().any():
        obs_scored = obs[obs["actual_result"].notna()]
        lines.append(f"OBSERVE_ONLY: {len(obs_scored)} matches (no binary success)")
        if "actual_total_goals" in obs_scored.columns:
            avg_g = obs_scored["actual_total_goals"].mean()
            lines.append(f"  avg goals: {avg_g:.1f}")
        lines.append("")

    # By league
    if "league" in scored.columns:
        lines.append("## Success Rate by League")
        lines.append("")
        lines.append(f"{'League':<20} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("-" * 40)
        for league, grp in scored.groupby("league"):
            n = len(grp); hits = int(grp["type_success"].sum())
            lines.append(f"  {league:<18} {n:>4} {hits:>4} {hits/n:7.1%}")
        lines.append("")

    # By confidence
    if "confidence" in scored.columns:
        lines.append("## Success Rate by Confidence")
        lines.append("")
        lines.append(f"{'Confidence':<16} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("-" * 40)
        for conf, grp in scored.groupby("confidence"):
            n = len(grp); hits = int(grp["type_success"].sum())
            lines.append(f"  {conf:<14} {n:>4} {hits:>4} {hits/n:7.1%}")
        lines.append("")

    # By control bucket
    if "control_10" in scored.columns:
        scored["_ctrl_bucket"] = scored["control_10"].apply(_ctrl_bucket)
        lines.append("## Success Rate by Control Bucket (0-10 scale)")
        lines.append("")
        lines.append(f"{'Control':<18} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("-" * 40)
        for bucket, grp in scored.groupby("_ctrl_bucket"):
            n = len(grp); hits = int(grp["type_success"].sum())
            lines.append(f"  {bucket:<16} {n:>4} {hits:>4} {hits/n:7.1%}")
        lines.append("")

    # By chaos bucket
    if "chaos_10" in scored.columns:
        scored["_chaos_bucket"] = scored["chaos_10"].apply(_chaos_bucket)
        lines.append("## Success Rate by Chaos Bucket (0-10 scale)")
        lines.append("")
        lines.append(f"{'Chaos':<18} {'n':>4} {'hits':>4} {'rate':>7}")
        lines.append("-" * 40)
        for bucket, grp in scored.groupby("_chaos_bucket"):
            n = len(grp); hits = int(grp["type_success"].sum())
            lines.append(f"  {bucket:<16} {n:>4} {hits:>4} {hits/n:7.1%}")
        lines.append("")

    # Context signal analysis (Phase 9) — graceful if columns absent
    try:
        from _context_signals import compute_context_signal_analysis as _csa
        lines.append("## Context Signal Analysis")
        lines.append("")
        lines.extend(_csa(scored))
    except Exception:
        pass

    # Ensemble analysis (Phase 10) — graceful if columns absent
    _append_ensemble_analysis_section(lines, scored)

    # League profile analysis sections (graceful fallback if fields absent)
    lines.extend(build_league_profile_sections(scored))

    # Top misses
    misses = scored[scored["type_success"] == False].copy()
    if not misses.empty:
        lines.append("## Top Misses")
        lines.append("")
        lines.append(f"{'Match':<38} {'Type':<14} {'Read':<32} {'Conf':<14} {'Actual'}")
        lines.append("-" * 110)
        for _, row in misses.head(15).iterrows():
            game   = f"{row.get('home_team','?')} vs {row.get('away_team','?')}"
            mtype  = str(row.get("recommended_market_type", "?"))
            read   = str(row.get("recommended_market_read", "?"))[:30]
            conf   = str(row.get("confidence", "?"))
            actual = str(row.get("actual_result", "?"))
            goals  = row.get("actual_total_goals", "?")
            lines.append(f"  {game[:36]:<38} {mtype:<14} {read:<32} {conf:<14} {actual} ({goals:.0f}g)")
        lines.append("")

    # Best / worst categories
    if type_rows:
        sorted_types = sorted(type_rows, key=lambda x: x["rate"], reverse=True)
        lines.append("## Best-Performing Recommendation Types")
        for t in sorted_types[:3]:
            lines.append(f"  {t['type']:<16} {t['rate']:.1%} ({t['hits']}/{t['n']})")
        lines.append("")
        lines.append("## Worst-Performing Recommendation Types")
        for t in sorted(type_rows, key=lambda x: x["rate"])[:3]:
            lines.append(f"  {t['type']:<16} {t['rate']:.1%} ({t['hits']}/{t['n']})")
        lines.append("")

    # Usefulness assessment
    lines.append("## Recommended Market Layer Assessment")
    lines.append("")
    total_hits = sum(r["hits"] for r in type_rows)
    total_n    = sum(r["n"]    for r in type_rows)
    overall    = total_hits / total_n if total_n else 0.0
    lines.append(f"Overall evaluatable success rate: {overall:.1%} ({total_hits}/{total_n})")
    lines.append("")

    if overall >= 0.70:
        verdict = "STRONG — recommended market layer is performing well above a naive baseline."
    elif overall >= 0.55:
        verdict = "USEFUL — recommended market layer adds signal in most categories."
    elif overall >= 0.45:
        verdict = "MIXED — some categories work, others need refinement."
    else:
        verdict = "WEAK — recommended market classifications are not yet reliable."
    lines.append(f"Verdict: {verdict}")
    lines.append("")
    lines.append("*This is a diagnostic-only evaluation. No betting claims.*")

    summary_md = out_dir / "daily_recommendation_eval_summary.md"
    summary_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Summary saved:          {summary_md}")

    # ---- Print summary to console ----
    print()
    print("=" * 60)
    print("  EVALUATION SUMMARY")
    print("=" * 60)
    for line in lines:
        print(line)


# ---------------------------------------------------------------------------
# Phase-2 diagnostic section helpers
# ---------------------------------------------------------------------------

def _append_miss_cluster_section(lines: list, out_dir: Path) -> None:
    """Sektion A: Miss Cluster Analysis — reads miss_clusters.csv if present."""
    lines.append("## Miss Cluster Analysis")
    lines.append("")
    csv_path = out_dir / "miss_clusters.csv"
    if not csv_path.exists():
        lines.append("  (Run: python -m football_prediction_v19.diagnostics.miss_clusters)")
        lines.append("  Output: outputs/diagnostics/miss_clusters.csv")
        lines.append("")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        lines.append(f"  [Error reading {csv_path.name}: {exc}]")
        lines.append("")
        return

    if df.empty or "warning_level" not in df.columns:
        lines.append("  No miss clusters found above threshold.")
        lines.append("")
        return

    critical = df[df["warning_level"] == "CRITICAL"]
    warning  = df[df["warning_level"] == "WARNING"]

    lines.append(f"  CRITICAL clusters : {len(critical)}")
    lines.append(f"  WARNING  clusters : {len(warning)}")
    lines.append("")

    if not critical.empty:
        lines.append("  Top-5 CRITICAL clusters:")
        lines.append(f"  {'Group':<55} {'n':>4}  {'miss_rate':>9}")
        lines.append("  " + "-" * 72)
        for _, row in critical.head(5).iterrows():
            lines.append(
                f"  {str(row.get('group_key','')):<55} "
                f"{int(row.get('n', 0)):>4}  "
                f"{float(row.get('miss_rate', 0)):>9.1%}"
            )
        lines.append("")


def _append_calibration_section(lines: list, out_dir: Path) -> None:
    """Sektion B: Calibration Summary — reads calibration CSV if present."""
    lines.append("## Calibration Summary")
    lines.append("")
    cal_dir = out_dir / "calibration"
    csvs = sorted(cal_dir.glob("calibration_*.csv")) if cal_dir.exists() else []

    if not csvs:
        lines.append("  Run calibration analysis to populate")
        lines.append("  (python -m football_prediction_v19.diagnostics.calibration)")
        lines.append("")
        return

    for csv_path in csvs:
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            lines.append(f"  [Error reading {csv_path.name}: {exc}]")
            continue

        if df.empty or "ece" not in df.columns:
            continue

        label = df["label"].iloc[0] if "label" in df.columns else csv_path.stem
        ece   = df["ece"].iloc[0]
        n_bins = len(df)
        lines.append(f"  [{label}]  ECE = {ece:.4f}  ({n_bins} non-empty bins)")

    lines.append("")


def _append_drift_section(lines: list, out_dir: Path) -> None:
    """Sektion C: Drift Monitor — reads drift_monitor.csv if present."""
    lines.append("## Drift Monitor")
    lines.append("")
    csv_path = out_dir / "drift_monitor.csv"

    if not csv_path.exists():
        lines.append("  Run drift monitor to populate")
        lines.append("  (python -m football_prediction_v19.diagnostics.drift)")
        lines.append("")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        lines.append(f"  [Error reading {csv_path.name}: {exc}]")
        lines.append("")
        return

    if df.empty:
        lines.append("  No drift windows available.")
        lines.append("")
        return

    lines.append(f"  {'Window start':<13} {'Window end':<13} {'n':>4}  {'hit_rate':>8}  {'overall':>8}  Flag")
    lines.append("  " + "-" * 68)

    last4 = df.tail(4)
    for _, row in last4.iterrows():
        flag    = str(row.get("drift_flag", ""))
        flag_str = "⚠️  DRIFT_WARNING" if flag == "DRIFT_WARNING" else ""
        lines.append(
            f"  {str(row.get('window_start', ''))[:10]:<13} "
            f"{str(row.get('window_end', ''))[:10]:<13} "
            f"{int(row.get('n', 0)):>4}  "
            f"{float(row.get('hit_rate', 0)):>8.1%}  "
            f"{float(row.get('overall_rate', 0)):>8.1%}  "
            f"{flag_str}"
        )

    active_drifts = int((df["drift_flag"] == "DRIFT_WARNING").sum()) if "drift_flag" in df.columns else 0
    if active_drifts:
        lines.append(f"\n  ⚠️  {active_drifts} DRIFT_WARNING window(s) in full history.")
    lines.append("")


# ---------------------------------------------------------------------------
# Template writer
# ---------------------------------------------------------------------------

def _write_template(path: Path, pre: pd.DataFrame) -> None:
    """Write a template final_scores.csv with the team names from pre-match CSVs."""
    rows = []
    for _, r in pre.iterrows():
        rows.append({
            "date":       r.get("date", "2026-05-17"),
            "league":     r.get("league", ""),
            "home_team":  r.get("home_team", ""),
            "away_team":  r.get("away_team", ""),
            "home_goals": "",
            "away_goals": "",
        })
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"  Template: {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = build_parser().parse_args()
    evaluate(
        reports_dir=Path(args.reports_dir),
        scores_path=Path(args.scores),
        out_dir=Path(args.out_dir),
    )
