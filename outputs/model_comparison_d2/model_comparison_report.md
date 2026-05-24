# Model Comparison Report

Test season: 2024
Best model: random_forest (calibrated=False)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.4158 | 1.2570 | 0.7451 | 0.6521 |  |
| logistic_regression | True | 0.4158 | 1.0773 | 0.6534 | 0.4926 |  |
| random_forest | False | 0.4521 | 1.0706 | 0.6467 | 0.4501 | ✓ |
| random_forest | True | 0.4521 | 1.0985 | 0.6577 | 0.5162 |  |
| gradient_boosting | False | 0.4422 | 1.1689 | 0.7045 | 0.5926 |  |
| gradient_boosting | True | 0.4224 | 1.0947 | 0.6605 | 0.4982 |  |
