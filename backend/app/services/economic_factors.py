"""Present stored macro features available before a forecast's price date."""

import logging
from datetime import date, timedelta
from math import isfinite

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_session
from app.services.macro_features import FEATURE_NAMES, macro_features_for_dates

logger = logging.getLogger(__name__)

FACTOR_LABELS = {
    "CPIAUCNS": "Inflation (CPI, year over year)",
    "UNRATE": "Unemployment rate",
    "DFF": "Federal funds rate",
}


def get_economic_factors(as_of_date: str | None) -> list[dict]:
    """Return published macro context for the latest price used by a forecast.

    These indicators are context; the current direction forecast uses stock
    prices rather than macro features. Missing data never blocks the forecast.
    """
    if not as_of_date:
        return []

    try:
        price_date = date.fromisoformat(as_of_date)
    except (TypeError, ValueError):
        return []

    try:
        with get_session() as session:
            aligned = macro_features_for_dates(session, [price_date]).iloc[0]
    except RuntimeError:
        return []
    except SQLAlchemyError:
        logger.warning("Stored economic factors are unavailable.")
        return []

    factors = []
    for series_id, label in FACTOR_LABELS.items():
        feature = FEATURE_NAMES.get(series_id)
        if feature is None:
            continue
        value = aligned[feature]
        age_days = aligned[f"{feature}_age_days"]
        if pd.isna(value) or pd.isna(age_days) or not isfinite(float(value)):
            continue

        age_days = int(age_days)
        factors.append(
            {
                "id": feature,
                "name": label,
                "value": round(float(value), 2),
                "unit": "%",
                "published_on": (price_date - timedelta(days=age_days)).isoformat(),
                "age_days": age_days,
            }
        )

    return factors
