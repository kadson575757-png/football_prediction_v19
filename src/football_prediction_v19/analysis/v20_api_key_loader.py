# -*- coding: utf-8 -*-
from __future__ import annotations
import os


def load_v20_api_key_status(env_names: list[str] | None = None) -> dict[str, object]:
    names = env_names or ["FOOTBALL_DATA_API_KEY", "APIFOOTBALL_KEY", "THE_ODDS_API_KEY"]
    return {"api_key_loader_status": "READY", "keys": {name: {"key_present": bool(os.getenv(name))} for name in names}, "secrets_logged": False}
