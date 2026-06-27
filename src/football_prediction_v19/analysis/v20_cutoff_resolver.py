# -*- coding: utf-8 -*-
from __future__ import annotations
from datetime import timedelta

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext, parse_dt


def resolve_analysis_cutoff(context: HistoricalMatchContext, *, manual_cutoff: str = "") -> HistoricalMatchContext:
    if context.cutoff_policy == "MANUAL_CUTOFF":
        cutoff = parse_dt(manual_cutoff or context.analysis_cutoff)
    elif context.cutoff_policy == "KICKOFF_MINUS_1_MINUTE":
        kickoff = f"{context.match_date} {context.kickoff_time}" if context.kickoff_time else context.match_date
        cutoff = parse_dt(kickoff) - timedelta(minutes=1)
    else:
        cutoff = parse_dt(context.match_date)
    return HistoricalMatchContext(**{**context.to_dict(), "analysis_cutoff": cutoff.strftime("%Y-%m-%d %H:%M:%S")})
