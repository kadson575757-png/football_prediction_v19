# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_docs_consistency_check_preview import run_docs_consistency_check
ROOT = Path(__file__).resolve().parents[1]


def test_docs_consistency_passes_repo_docs_and_fails_missing_phrase(tmp_path: Path) -> None:
    good = run_docs_consistency_check(tmp_path / "good", repo_root=ROOT)
    bad_root = tmp_path / "badroot"; (bad_root / "docs").mkdir(parents=True)
    for name in ["v19_final_pipeline_user_guide.md", "v19_release_candidate_scope.md", "v19_safe_usage_notes.md", "v19_commands.md"]:
        (bad_root / "docs" / name).write_text("preview analyst decision raw evidence match pack batch config single match no automatic betting", encoding="utf-8")
    bad = run_docs_consistency_check(tmp_path / "bad", repo_root=bad_root)
    assert good["docs_consistency_status"] == "PASSED"
    assert bad["docs_consistency_status"] == "FAILED"
    assert Path(good["docs_consistency_matrix_path"]).exists()
