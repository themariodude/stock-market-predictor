# SCRUM-25: Compare Models Against a Baseline

## Overview
Implements a naive persistence baseline and evaluation utilities for comparing
trained stock prediction models against that baseline.

## Baseline Method
The persistence baseline predicts the next stock price using the current stock
price.

Example:
Current prices: [100, 102, 101, 105]
Baseline predictions: [100, 102, 101]
Actual next prices: [102, 101, 105]

## Evaluation Metrics
- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)

## Implementation
- `src/models/baseline.py`
- `src/models/evaluation.py`
- `tests/test_baseline.py`
- `tests/test_evaluation.py`

## Testing

Run:

```bash
python -m pytest tests/test_baseline.py tests/test_evaluation.py