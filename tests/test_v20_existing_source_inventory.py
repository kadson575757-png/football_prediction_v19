# -*- coding: utf-8 -*-
from pathlib import Path
from football_prediction_v19.analysis.v20_existing_source_inventory import build_existing_source_inventory
ROOT = Path(__file__).resolve().parents[1]
def test_source_inventory_finds_existing_building_blocks(tmp_path):
    r=build_existing_source_inventory(tmp_path, repo_root=ROOT)
    assert r["existing_source_inventory_status"]=="READY"
    assert Path(r["existing_source_inventory_json_path"]).exists()
