# SCRUM-20 — Generate Stock Prediction

## Overview

SCRUM-20 implements the project's initial machine learning stock-price
prediction workflow for supported defense-sector stocks.

The prediction workflow retrieves historical stock data from the existing
backend data pipeline, creates model-ready features and next-day closing-price
targets, trains a LinearRegression model, and generates predictions against
chronologically held-out test data.

## Model

Initial model:

- LinearRegression
- scikit-learn 1.5.2

Features:

- Open
- High
- Low
- Close
- Volume

Target:

- Next trading day's closing price

## Training and Test Split

Historical observations are kept in chronological order.

The first 80% of model-ready observations are used for training and the
remaining 20% are held out for testing.

Data is not randomly shuffled because doing so could introduce future market
information into the training set.

## Prediction Workflow

Historical Stock Data
→ Feature/Target Preparation
→ Chronological Train/Test Split
→ LinearRegression Training
→ Held-Out Predictions
→ Actual / Predicted Output

## API Endpoint

```text
GET /stocks/{ticker}/prediction