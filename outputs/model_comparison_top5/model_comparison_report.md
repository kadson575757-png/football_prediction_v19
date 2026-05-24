# Model Comparison Report

Test season: 2023
Best model: random_forest (calibrated=True)

**Note:** Better backtest metrics do not guarantee future betting profit. This report shows historical model performance only.

## Results

| Model | Calibrated | Accuracy | Log Loss | Brier | Avg Conf | Best |
|---|---|---|---|---|---|---|
| logistic_regression | False | 0.4865 | 1.0799 | 0.6383 | 0.5984 |  |
| logistic_regression | True | 0.4831 | 1.0215 | 0.6121 | 0.4898 |  |
| random_forest | False | 0.5352 | 0.9752 | 0.5811 | 0.4653 |  |
| random_forest | True | 0.5490 | 0.9627 | 0.5726 | 0.5399 | ✓ |
| gradient_boosting | False | 0.5163 | 0.9866 | 0.5893 | 0.5448 |  |
| gradient_boosting | True | 0.5215 | 0.9982 | 0.5965 | 0.5038 |  |
