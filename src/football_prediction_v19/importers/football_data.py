from __future__ import annotations

from pathlib import Path

import requests

from ..data import prepare_real_matches_file


def download_football_data_csv(url: str, output_path: str) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    output.write_bytes(response.content)
    return output


def normalize_football_data_csv(input_path: str, output_path: str) -> dict[str, int | str]:
    return prepare_real_matches_file(input_path, output_path, input_format="football-data")
