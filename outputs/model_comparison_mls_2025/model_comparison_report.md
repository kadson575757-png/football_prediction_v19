# Model Comparison Report

Test season: 2025
Best model: random_forest (calibrated=False)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.4156 | 1.1787 | 0.6917 | 0.5780 |  |
| logistic_regression | True | 0.4434 | 1.0639 | 0.6416 | 0.4790 |  |
| random_forest | False | 0.4620 | 1.0545 | 0.6345 | 0.4486 | ✓ |
| random_forest | True | 0.4416 | 1.0590 | 0.6367 | 0.4784 |  |
| gradient_boosting | False | 0.4787 | 1.0945 | 0.6509 | 0.5476 |  |
| gradient_boosting | True | 0.4490 | 1.0602 | 0.6382 | 0.4619 |  |
