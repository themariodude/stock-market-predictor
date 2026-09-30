"""Align stored FRED observations to trading dates without look-ahead.

A macro value is usable only on trading days strictly after its
available_date (the day it was published). Output has one row per trading
date: each feature's value plus its age in days since publication.

Run a quick check with real data:
    docker compose exec backend python -m app.services.macro_features LMT
"""

import argparse
from collections.abc import Iterable
from datetime import date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.models.macro import MacroObservation

SERIES_IDS = ("CPIAUCNS", "UNRATE", "DFF")


def _normalize_trading_dates(
    trading_dates: Iterable[date | datetime | str | pd.Timestamp],
) -> pd.DataFrame:
    dates = pd.to_datetime(list(trading_dates), errors="raise")

    frame = pd.DataFrame({"trading_date": dates})
    frame["trading_date"] = frame["trading_date"].dt.normalize()

    return (
        frame.drop_duplicates(subset=["trading_date"])
        .sort_values("trading_date")
        .reset_index(drop=True)
    )


def _load_macro_observations(session: Session) -> pd.DataFrame:
    statement = (
        select(
            MacroObservation.id,
            MacroObservation.series_id,
            MacroObservation.observation_date,
            MacroObservation.available_date,
            MacroObservation.value,
        )
        .where(MacroObservation.series_id.in_(SERIES_IDS))
        .order_by(
            MacroObservation.series_id,
            MacroObservation.observation_date,
            MacroObservation.available_date,
            MacroObservation.id,
        )
    )

    rows = session.execute(statement).mappings().all()

    if not rows:
        return pd.DataFrame(
            columns=[
                "id",
                "series_id",
                "observation_date",
                "available_date",
                "value",
            ]
        )

    frame = pd.DataFrame(rows)

    frame["observation_date"] = pd.to_datetime(
        frame["observation_date"]
    )
    frame["available_date"] = pd.to_datetime(frame["available_date"])

    return frame


def _keep_forward_moving_events(
    events: pd.DataFrame,
    value_column: str,
) -> pd.DataFrame:
    if events.empty:
        return events

    # A NULL release must not overwrite the last usable value.
    events = events.dropna(
        subset=["available_date", "observation_date", value_column]
    ).copy()

    if events.empty:
        return events

    # If several observations become available on the same day,
    # keep the newest observation period.
    events = events.sort_values(
        ["available_date", "observation_date", "id"]
    )
    events = events.drop_duplicates(
        subset=["available_date"],
        keep="last",
    )

    # Do not allow a later availability event to move us backward
    # to an older observation period.
    previous_latest = events["observation_date"].cummax().shift()

    events = events.loc[
        previous_latest.isna()
        | (events["observation_date"] > previous_latest)
    ]

    return events.sort_values("available_date").reset_index(drop=True)


def _build_cpi_yoy(cpi: pd.DataFrame) -> pd.DataFrame:
    if cpi.empty:
        return pd.DataFrame(
            columns=[
                "id",
                "observation_date",
                "available_date",
                "cpi_yoy_pct",
            ]
        )

    # CPIAUCNS is stored as first-release data. If more than one row
    # somehow exists for a month, use the earliest availability date.
    cpi = cpi.sort_values(
        ["observation_date", "available_date", "id"]
    ).drop_duplicates(
        subset=["observation_date"],
        keep="first",
    )

    current = cpi[
        ["id", "observation_date", "available_date", "value"]
    ].rename(
        columns={
            "available_date": "current_available_date",
            "value": "current_value",
        }
    )

    previous = cpi[
        ["observation_date", "available_date", "value"]
    ].copy()

    # Move the prior observation forward twelve months so it joins
    # against the current month's observation_date.
    previous["observation_date"] = (
        previous["observation_date"] + pd.DateOffset(months=12)
    )

    previous = previous.rename(
        columns={
            "available_date": "prior_available_date",
            "value": "prior_value",
        }
    )

    yoy = current.merge(
        previous,
        on="observation_date",
        how="left",
        validate="one_to_one",
    )

    yoy["cpi_yoy_pct"] = (
        (yoy["current_value"] / yoy["prior_value"]) - 1.0
    ) * 100.0

    # If either CPI value is NULL, pandas produces NaN here.
    missing_value = (
        yoy["current_value"].isna() | yoy["prior_value"].isna()
    )
    yoy.loc[missing_value, "cpi_yoy_pct"] = float("nan")

    # The derived YoY value is not usable until BOTH source months
    # were public.
    yoy["available_date"] = yoy[
        ["current_available_date", "prior_available_date"]
    ].max(axis=1)

    events = yoy[
        [
            "id",
            "observation_date",
            "available_date",
            "cpi_yoy_pct",
        ]
    ]

    return _keep_forward_moving_events(events, "cpi_yoy_pct")


def _build_series_events(
    observations: pd.DataFrame,
    series_id: str,
    value_column: str,
) -> pd.DataFrame:
    events = observations.loc[
        observations["series_id"] == series_id,
        [
            "id",
            "observation_date",
            "available_date",
            "value",
        ],
    ].copy()

    events = events.rename(columns={"value": value_column})

    return _keep_forward_moving_events(events, value_column)


def _align_feature(
    trading_dates: pd.DataFrame,
    events: pd.DataFrame,
    value_column: str,
    age_column: str,
) -> pd.DataFrame:
    if events.empty:
        result = trading_dates.copy()
        result[value_column] = float("nan")
        result[age_column] = pd.Series(
            pd.NA,
            index=result.index,
            dtype="Int64",
        )
        return result

    right = events[
        ["available_date", value_column]
    ].sort_values("available_date")

    result = pd.merge_asof(
        trading_dates.sort_values("trading_date"),
        right,
        left_on="trading_date",
        right_on="available_date",
        direction="backward",
        allow_exact_matches=False,
    )

    age = result["trading_date"] - result["available_date"]
    result[age_column] = age.dt.days.astype("Int64")

    return result[
        [
            "trading_date",
            value_column,
            age_column,
        ]
    ]


def _build_macro_features(
    trading_dates: Iterable[date | datetime | str | pd.Timestamp],
    session: Session,
) -> pd.DataFrame:
    dates = _normalize_trading_dates(trading_dates)

    if dates.empty:
        return pd.DataFrame(
            columns=[
                "trading_date",
                "cpi_yoy_pct",
                "cpi_yoy_age_days",
                "unemployment_rate",
                "unemployment_rate_age_days",
                "fed_funds_rate",
                "fed_funds_rate_age_days",
            ]
        )

    observations = _load_macro_observations(session)

    cpi = observations.loc[
        observations["series_id"] == "CPIAUCNS"
    ].copy()

    cpi_events = _build_cpi_yoy(cpi)

    unemployment_events = _build_series_events(
        observations,
        "UNRATE",
        "unemployment_rate",
    )

    fed_funds_events = _build_series_events(
        observations,
        "DFF",
        "fed_funds_rate",
    )

    cpi_aligned = _align_feature(
        dates,
        cpi_events,
        "cpi_yoy_pct",
        "cpi_yoy_age_days",
    )

    unemployment_aligned = _align_feature(
        dates,
        unemployment_events,
        "unemployment_rate",
        "unemployment_rate_age_days",
    )

    fed_funds_aligned = _align_feature(
        dates,
        fed_funds_events,
        "fed_funds_rate",
        "fed_funds_rate_age_days",
    )

    result = dates.copy()

    result["cpi_yoy_pct"] = cpi_aligned["cpi_yoy_pct"]
    result["cpi_yoy_age_days"] = cpi_aligned[
        "cpi_yoy_age_days"
    ]

    result["unemployment_rate"] = unemployment_aligned[
        "unemployment_rate"
    ]
    result["unemployment_rate_age_days"] = unemployment_aligned[
        "unemployment_rate_age_days"
    ]

    result["fed_funds_rate"] = fed_funds_aligned[
        "fed_funds_rate"
    ]
    result["fed_funds_rate_age_days"] = fed_funds_aligned[
        "fed_funds_rate_age_days"
    ]

    return result


def build_macro_features(
    trading_dates: Iterable[date | datetime | str | pd.Timestamp],
    *,
    session: Session | None = None,
) -> pd.DataFrame:
    if session is not None:
        return _build_macro_features(trading_dates, session)

    with Session(engine) as database_session:
        return _build_macro_features(
            trading_dates,
            database_session,
        )


def _quick_check_dates() -> list[pd.Timestamp]:
    # CLI smoke-test dates only. The production/ML path should pass
    # the actual trading dates from the stock dataset.
    return list(
        pd.bdate_range(
            end=pd.Timestamp.today().normalize(),
            periods=10,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quick-check point-in-time macro features."
    )
    parser.add_argument(
        "symbol",
        help=(
            "Ticker label for the quick check. "
            "No stock table is queried."
        ),
    )
    args = parser.parse_args()

    features = build_macro_features(_quick_check_dates())

    print(f"{args.symbol} macro feature quick check")
    print(features.to_string(index=False))


if __name__ == "__main__":
    main()
