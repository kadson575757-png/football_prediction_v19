from scripts.run_v20_match import run_v20_match


def test_one_command_match_runner_outputs(tmp_path):
    run_v20_match(home_team="Demo Home", away_team="Demo Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_one_command_runner", output_dir=tmp_path, base_dir=".")
    for name in ["final_tip_card.md", "final_match_report.md", "model_probabilities.csv", "missing_data_report.md", "machine_result.json", "artifact_index.csv"]:
        assert (tmp_path / name).exists()
