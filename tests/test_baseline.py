import sys
from pathlib import Path

import pytest

# Add the project root directory to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.baseline import persistence_baseline


def test_persistence_baseline():
    prices = [100, 102, 101, 105]

    predictions = persistence_baseline(prices)

    assert predictions == [100, 102, 101]


def test_persistence_baseline_requires_two_prices():
    with pytest.raises(ValueError):
        persistence_baseline([100])

def test_persistence_baseline_with_float_prices():
    prices = [101.5, 102.25, 103.0]

    predictions = persistence_baseline(prices)

    assert predictions == [101.5, 102.25]

