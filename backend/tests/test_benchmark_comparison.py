import pytest

from app.services import benchmark_comparison as comparison


def history(ticker, points):
    return {
        "ticker": ticker,
        "time_range": "1Y",
        "data": [
            {"date": day, "close": price}
            for day, price in points
        ],
    }


def mock_history(monkeypatch, stock_points, spy_points):
    histories = {
        "LMT": history("LMT", stock_points),
        "SPY": history("SPY", spy_points),
    }

    monkeypatch.setattr(
        comparison,
        "get_historical_stock_data",
        lambda ticker, time_range: histories[ticker],
    )


def test_outperformed_with_shared_dates(monkeypatch):
    mock_history(
        monkeypatch,
        [
            ("2026-01-02", 100),
            ("2026-01-05", 150),
            ("2026-01-06", 110),
        ],
        [
            ("2026-01-02", 200),
            ("2026-01-06", 210),
        ],
    )

    result = comparison.compare_stock_against_spy("lmt")

    assert result["stock_return_pct"] == 10
    assert result["benchmark_return_pct"] == 5
    assert result["excess_return_percentage_points"] == 5
    assert result["status"] == "OUTPERFORMED"
    assert result["shared_trading_days"] == 2


def test_underperformed(monkeypatch):
    mock_history(
        monkeypatch,
        [
            ("2026-01-02", 100),
            ("2026-01-06", 90),
        ],
        [
            ("2026-01-02", 200),
            ("2026-01-06", 210),
        ],
    )

    result = comparison.compare_stock_against_spy("LMT")

    assert result["status"] == "UNDERPERFORMED"


def test_matched(monkeypatch):
    mock_history(
        monkeypatch,
        [
            ("2026-01-02", 100),
            ("2026-01-06", 105),
        ],
        [
            ("2026-01-02", 200),
            ("2026-01-06", 210),
        ],
    )

    result = comparison.compare_stock_against_spy("LMT")

    assert result["status"] == "MATCHED"


def test_rejects_unsupported_stock():
    with pytest.raises(ValueError, match="Unsupported"):
        comparison.compare_stock_against_spy("SPY")


def test_requires_two_shared_dates(monkeypatch):
    mock_history(
        monkeypatch,
        [
            ("2026-01-02", 100),
            ("2026-01-05", 110),
        ],
        [
            ("2026-01-02", 200),
            ("2026-01-06", 210),
        ],
    )

    with pytest.raises(ValueError, match="two shared"):
        comparison.compare_stock_against_spy("LMT")


@pytest.mark.parametrize(
    "bad_price",
    [0, -1, float("nan"), float("inf")],
)
def test_rejects_bad_prices(monkeypatch, bad_price):
    mock_history(
        monkeypatch,
        [
            ("2026-01-02", 100),
            ("2026-01-06", bad_price),
        ],
        [
            ("2026-01-02", 200),
            ("2026-01-06", 210),
        ],
    )

    with pytest.raises(ValueError, match="positive and finite"):
        comparison.compare_stock_against_spy("LMT")
