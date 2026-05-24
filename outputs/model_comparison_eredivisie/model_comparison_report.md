# Model Comparison Report

Test season: 2024
Best model: random_forest (calibrated=False)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.4721 | 1.0980 | 0.6502 | 0.6201 |  |
| logistic_regression | True | 0.5475 | 0.9689 | 0.5816 | 0.5099 |  |
| random_forest | False | 0.5016 | 0.9682 | 0.5777 | 0.5161 | ✓ |
| random_forest | True | 0.5279 | 1.1644 | 0.5706 | 0.5611 |  |
| gradient_boosting | False | 0.5016 | 1.0162 | 0.6071 | 0.6074 |  |
| gradient_boosting | True | 0.5148 | 1.1037 | 0.5961 | 0.5360 |  |
