from datetime import date

import pandas as pd
import pytest

from app.services.macro_features import align_to_trading_dates, cpi_year_over_year

COLUMNS = ["series_id", "observation_date", "available_date", "value"]


def observations(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


def cpi_levels():
    """CPI levels Aug 2024 - Aug 2026, +0.25 per month, released on the 11th.

    Oct 2025 is missing and Oct/Nov 2025 were released together on
    2025-12-18, as happened after the 2025 government shutdown.
    """
    rows, level = [], 310.0
    for month in pd.date_range("2024-08-01", "2026-08-01", freq="MS"):
        released = (month + pd.DateOffset(months=1)).replace(day=11)
        value = level
        if month == pd.Timestamp("2025-10-01"):
            value, released = None, pd.Timestamp("2025-12-18")
        if month == pd.Timestamp("2025-11-01"):
            released = pd.Timestamp("2025-12-18")
        rows.append(("CPIAUCNS", month.date(), released.date(), value))
        level += 0.25
    return rows


def as_datetimes(frame):
    frame = frame.copy()
    frame["observation_date"] = pd.to_datetime(frame["observation_date"])
    frame["available_date"] = pd.to_datetime(frame["available_date"])
    return frame


def test_cpi_year_over_year_math():
    yoy = cpi_year_over_year(as_datetimes(observations(cpi_levels())))
    aug_2026 = yoy.set_index("observation_date").loc["2026-08-01"]

    assert aug_2026["value"] == pytest.approx((316.0 / 313.0 - 1) * 100)


def test_cpi_year_over_year_is_nan_when_a_month_is_missing():
    yoy = cpi_year_over_year(as_datetimes(observations(cpi_levels())))

    assert pd.isna(yoy.set_index("observation_date").loc["2025-10-01", "value"])


def test_value_is_not_used_on_its_release_day():
    rows = [
        ("UNRATE", date(2026, 7, 1), date(2026, 8, 7), 4.2),
        ("UNRATE", date(2026, 8, 1), date(2026, 9, 4), 4.1),  # released Fri 09-04
    ]
    result = align_to_trading_dates(
        observations(rows), [date(2026, 9, 4), date(2026, 9, 8)]
    ).set_index("date")

    assert result.loc["2026-09-04", "unemployment_rate"] == 4.2
    assert result.loc["2026-09-08", "unemployment_rate"] == 4.1


def test_dff_over_labor_day_uses_values_only_after_publication():
    # DFF value = day of month, published the next Fed business day.
    rows = [
        ("DFF", date(2026, 9, 3), date(2026, 9, 4), 3.0),
        ("DFF", date(2026, 9, 4), date(2026, 9, 8), 4.0),
        ("DFF", date(2026, 9, 5), date(2026, 9, 8), 5.0),
        ("DFF", date(2026, 9, 6), date(2026, 9, 8), 6.0),
        ("DFF", date(2026, 9, 7), date(2026, 9, 8), 7.0),
    ]
    result = align_to_trading_dates(
        observations(rows), [date(2026, 9, 8), date(2026, 9, 9)]
    ).set_index("date")

    assert result.loc["2026-09-08", "fed_funds_rate"] == 3.0
    assert result.loc["2026-09-09", "fed_funds_rate"] == 7.0


def test_shutdown_gap_carries_last_value_and_reports_its_age():
    result = align_to_trading_dates(
        observations(cpi_levels()), [date(2025, 12, 18), date(2025, 12, 19)]
    ).set_index("date")

    assert result.loc["2025-12-18", "cpi_yoy_pct_age_days"] == 68
    assert result.loc["2025-12-19", "cpi_yoy_pct_age_days"] == 1


def test_never_switches_back_to_an_older_month():
    rows = [
        ("UNRATE", date(2026, 8, 1), date(2026, 9, 4), 4.1),
        ("UNRATE", date(2026, 7, 1), date(2026, 9, 10), 9.9),  # late re-release
    ]
    result = align_to_trading_dates(observations(rows), [date(2026, 9, 11)])

    assert result["unemployment_rate"].iloc[0] == 4.1


def test_every_used_value_was_published_before_its_trading_date():
    rows = cpi_levels() + [
        ("UNRATE", date(2026, 8, 1), date(2026, 9, 4), 4.1),
        ("DFF", date(2026, 9, 3), date(2026, 9, 4), 3.63),
    ]
    trading_dates = pd.bdate_range("2025-11-01", "2026-09-30").date
    result = align_to_trading_dates(observations(rows), trading_dates)

    for feature in ["cpi_yoy_pct", "unemployment_rate", "fed_funds_rate"]:
        ages = result[f"{feature}_age_days"].dropna()
        assert (ages > 0).all()


def test_accepts_timezone_aware_yfinance_index():
    rows = [("UNRATE", date(2026, 8, 1), date(2026, 9, 4), 4.1)]
    index = pd.DatetimeIndex(["2026-09-08", "2026-09-09"]).tz_localize(
        "America/New_York"
    )

    result = align_to_trading_dates(observations(rows), index)

    assert list(result["date"].dt.date) == [date(2026, 9, 8), date(2026, 9, 9)]
    assert (result["unemployment_rate"] == 4.1).all()


def test_no_stored_data_gives_nan_rows():
    result = align_to_trading_dates(observations([]), [date(2026, 9, 8)])

    assert len(result) == 1
    assert result.drop(columns="date").isna().all().all()


def test_cpi_year_over_year_handles_absent_base_month():
    # Feb 2023 is missing entirely (no row), so Feb 2024 has no base month.
    # A shift(12)/pct_change(12) implementation would compare the wrong months.
    rows = [
        ("CPIAUCNS", month.date(), (month + pd.DateOffset(days=40)).date(), 100.0 + i)
        for i, month in enumerate(pd.date_range("2023-01-01", "2024-02-01", freq="MS"))
        if month != pd.Timestamp("2023-02-01")
    ]
    yoy = cpi_year_over_year(as_datetimes(observations(rows))).set_index(
        "observation_date"
    )

    assert pd.isna(yoy.loc["2024-02-01", "value"])
    assert yoy.loc["2024-01-01", "value"] == pytest.approx((112.0 / 100.0 - 1) * 100)


def test_cpi_year_over_year_is_available_only_after_both_months_are():
    rows = [
        ("CPIAUCNS", date(2023, 1, 1), date(2024, 3, 1), 100.0),  # base published late
        ("CPIAUCNS", date(2024, 1, 1), date(2024, 2, 13), 110.0),
    ]
    yoy = cpi_year_over_year(as_datetimes(observations(rows))).set_index(
        "observation_date"
    )

    assert yoy.loc["2024-01-01", "available_date"] == pd.Timestamp("2024-03-01")


def test_missing_release_does_not_erase_last_value():
    rows = [
        ("UNRATE", date(2024, 1, 1), date(2024, 2, 2), 3.7),
        ("UNRATE", date(2024, 2, 1), date(2024, 3, 8), None),
    ]
    result = align_to_trading_dates(observations(rows), [date(2024, 3, 11)])

    assert result["unemployment_rate"].iloc[0] == 3.7
    assert result["unemployment_rate_age_days"].iloc[0] == 38
