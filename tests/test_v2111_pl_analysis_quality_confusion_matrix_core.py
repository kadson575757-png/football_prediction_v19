import pandas as pd

from scripts.evaluate_v2111_pl_2025_26_analysis_quality import compute_confusion_matrix


def test_v2111_confusion_matrix_counts_predictions_vs_actuals():
    rows = pd.DataFrame([
        {"top_probability_outcome": "HOME", "actual_result": "HOME"},
        {"top_probability_outcome": "HOME", "actual_result": "DRAW"},
        {"top_probability_outcome": "AWAY", "actual_result": "AWAY"},
    ])

    matrix = compute_confusion_matrix(rows)
    home = matrix[matrix["predicted"] == "HOME"].iloc[0]
    away = matrix[matrix["predicted"] == "AWAY"].iloc[0]

    assert home["actual_home"] == 1
    assert home["actual_draw"] == 1
    assert home["total"] == 2
    assert away["actual_away"] == 1

