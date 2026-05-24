# Model Comparison Report

Test season: 2023
Best model: random_forest (calibrated=False)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.3651 | 1.7145 | 0.8999 | 0.7258 |  |
| logistic_regression | True | 0.4013 | 1.1154 | 0.6778 | 0.4769 |  |
| random_forest | False | 0.5395 | 0.9868 | 0.5922 | 0.4829 | ✓ |
| random_forest | True | 0.5362 | 0.9877 | 0.5904 | 0.5217 |  |
| gradient_boosting | False | 0.4375 | 1.1698 | 0.6913 | 0.6573 |  |
| gradient_boosting | True | 0.4671 | 1.1638 | 0.6381 | 0.5282 |  |
