# Model Comparison Report

Test season: 2024
Best model: random_forest (calibrated=False)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.3410 | 1.5872 | 0.8497 | 0.6575 |  |
| logistic_regression | True | 0.3544 | 1.2128 | 0.6901 | 0.4728 |  |
| random_forest | False | 0.4598 | 1.0501 | 0.6327 | 0.4207 | ✓ |
| random_forest | True | 0.4464 | 1.1096 | 0.6599 | 0.5265 |  |
| gradient_boosting | False | 0.4100 | 1.1328 | 0.6767 | 0.5434 |  |
| gradient_boosting | True | 0.4540 | 1.0863 | 0.6547 | 0.4990 |  |
