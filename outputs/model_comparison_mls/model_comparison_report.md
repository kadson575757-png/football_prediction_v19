# Model Comparison Report

Test season: 2025
Best model: random_forest (calibrated=True)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.4304 | 1.1932 | 0.7044 | 0.5781 |  |
| logistic_regression | True | 0.4397 | 1.0704 | 0.6460 | 0.4787 |  |
| random_forest | False | 0.4712 | 1.0591 | 0.6388 | 0.4230 |  |
| random_forest | True | 0.4490 | 1.0539 | 0.6350 | 0.4727 | ✓ |
| gradient_boosting | False | 0.4082 | 1.1315 | 0.6814 | 0.5070 |  |
| gradient_boosting | True | 0.4453 | 1.0596 | 0.6385 | 0.4654 |  |
