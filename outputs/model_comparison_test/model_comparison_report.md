# Model Comparison Report

Test season: 2023
Best model: random_forest (calibrated=True)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.5536 | 1.7979 | 0.6926 | 0.8197 |  |
| logistic_regression | True | 0.5179 | 1.0660 | 0.6257 | 0.4853 |  |
| random_forest | False | 0.5179 | 0.9766 | 0.5833 | 0.4783 |  |
| random_forest | True | 0.5357 | 0.9695 | 0.5799 | 0.5568 | ✓ |
| gradient_boosting | False | 0.5000 | 1.2100 | 0.6760 | 0.7203 |  |
| gradient_boosting | True | 0.5714 | 0.9882 | 0.5907 | 0.5442 |  |

## Warnings

- **logistic_regression** (calibrated=False): Overconfident: avg confidence 0.82 > 0.75
