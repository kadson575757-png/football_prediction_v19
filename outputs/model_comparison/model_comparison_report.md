# Model Comparison Report

Test season: 2023
Best model: gradient_boosting (calibrated=True)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.5536 | 1.7994 | 0.6927 | 0.8196 |  |
| logistic_regression | True | 0.5357 | 1.0675 | 0.6268 | 0.4846 |  |
| random_forest | False | 0.5000 | 0.9858 | 0.5889 | 0.4777 |  |
| random_forest | True | 0.5179 | 1.5357 | 0.5899 | 0.5487 |  |
| gradient_boosting | False | 0.4821 | 1.1817 | 0.6827 | 0.7248 |  |
| gradient_boosting | True | 0.5714 | 0.9822 | 0.5870 | 0.5450 | ✓ |

## Warnings

- **logistic_regression** (calibrated=False): Overconfident: avg confidence 0.82 > 0.75
