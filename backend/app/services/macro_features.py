"""Align stored FRED observations to trading dates without look-ahead.

A macro value is usable only on trading days strictly after its
available_date (the day it was published). Output has one row per trading
date: each feature's value plus its age in days since publication.

Run a quick check with real data:
    docker compose exec backend python -m app.services.macro_features LMT
"""

from collections.abc import Iterable
from datetime import date

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.macro import MacroObservation

# Output feature name for each stored series.
FEATURE_NAMES = {
    "CPIAUCNS": "cpi_yoy_pct",
    "UNRATE": "unemployment_rate",
    "DFF": "fed_funds_rate",
}


def load_macro_observations(session: Session) -> pd.DataFrame:
    """Load all stored macro observations."""
    rows = session.execute(
        select(
            MacroObservation.series_id,
            MacroObservation.observation_date,
            MacroObservation.available_date,
            MacroObservation.value,
        )
    ).all()
    return pd.DataFrame(
        rows,
        columns=["series_id", "observation_date", "available_date", "value"],
    )


def cpi_year_over_year(cpi: pd.DataFrame) -> pd.DataFrame:
    """12-month % change computed from first-release CPI levels.

    Both levels are first releases, so the result only uses information that
    was public on the later of the two release dates. A missing level (e.g.
    Oct 2025) makes that month's change and the one 12 months later NaN.
    """
    year_ago = cpi[["observation_date", "available_date", "value"]].copy()
    year_ago["observation_date"] = year_ago["observation_date"] + pd.DateOffset(years=1)
    merged = cpi.merge(
        year_ago, on="observation_date", how="left", suffixes=("", "_year_ago")
    )
    merged["value"] = (merged["value"] / merged["value_year_ago"] - 1) * 100
    merged["available_date"] = merged[
        ["available_date", "available_date_year_ago"]
    ].max(axis=1)
    return merged[["observation_date", "available_date", "value"]]


def _usable_releases(series: pd.DataFrame) -> pd.DataFrame:
    """Drop missing values, keep one row per release date, never go back in time."""
    series = series.dropna(subset=["value"]).sort_values(
        ["available_date", "observation_date"]
    )
    series = series.drop_duplicates("available_date", keep="last")
    newest_so_far = series["observation_date"].cummax()
    return series[series["observation_date"] == newest_so_far]


def align_to_trading_dates(
    observations: pd.DataFrame,
    trading_dates: Iterable[date],
) -> pd.DataFrame:
    """One row per trading date with each macro feature and its age in days.

    Accepts plain dates or timestamps. Timezone-aware timestamps (e.g. a
    yfinance index) are converted to their New York calendar date.
    """
    stamps = pd.DatetimeIndex(pd.to_datetime(list(trading_dates)))
    if stamps.tz is not None:
        stamps = stamps.tz_convert("America/New_York").tz_localize(None)
    dates = pd.DataFrame({"date": stamps.normalize().unique().sort_values()})
    obs = observations.copy()
    obs["observation_date"] = pd.to_datetime(obs["observation_date"])
    obs["available_date"] = pd.to_datetime(obs["available_date"])

    result = dates.copy()
    for series_id, feature in FEATURE_NAMES.items():
        series = obs[obs["series_id"] == series_id]
        if series_id == "CPIAUCNS":
            series = cpi_year_over_year(series)
        series = _usable_releases(series)[["available_date", "value"]]

        merged = pd.merge_asof(
            dates,
            series,
            left_on="date",
            right_on="available_date",
            direction="backward",
            allow_exact_matches=False,
        )
        result[feature] = merged["value"].to_numpy()
        age = merged["date"] - merged["available_date"]
        result[f"{feature}_age_days"] = age.dt.days.to_numpy()

    return result


def macro_features_for_dates(
    session: Session,
    trading_dates: Iterable[date],
) -> pd.DataFrame:
    """Load stored observations and align them to the given trading dates."""
    return align_to_trading_dates(load_macro_observations(session), trading_dates)


if __name__ == "__main__":
    import sys

    import yfinance as yf

    from app.database import get_session

    ticker = sys.argv[1] if len(sys.argv) > 1 else "LMT"
    history = yf.Ticker(ticker).history(period="2y", auto_adjust=False)
    trading_dates = [timestamp.date() for timestamp in history.index]

    with get_session() as session:
        features = macro_features_for_dates(session, trading_dates)

    print(features.tail(10).to_string(index=False))
