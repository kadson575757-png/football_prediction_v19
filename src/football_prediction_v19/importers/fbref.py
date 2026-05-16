from __future__ import annotations

from ..data import prepare_real_matches_file


def normalize_fbref_csv(input_path: str, output_path: str) -> dict[str, int | str]:
    return prepare_real_matches_file(input_path, output_path, input_format="fbref")
