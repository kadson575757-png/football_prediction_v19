from pathlib import Path

from scripts.audit_v295_goal_difference_sources import audit_goal_difference_sources


def test_v295_goal_difference_source_audit_script_exists():
    assert Path("scripts/audit_v295_goal_difference_sources.py").exists()
    assert callable(audit_goal_difference_sources)
