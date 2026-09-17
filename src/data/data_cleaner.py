import pandas as pd


class MarketDataCleaner:
    """Validate and clean normalized market data."""

    REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
    NUMERIC_COLUMNS = ["open", "high", "low", "close", "volume"]

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Input must be a pandas DataFrame.")

        missing = [
            column for column in self.REQUIRED_COLUMNS
            if column not in df.columns
        ]

        if missing:
            raise KeyError(f"Missing required columns: {missing}")

        cleaned = df[self.REQUIRED_COLUMNS].copy()

        # Validate dates while distinguishing malformed from missing values
        non_missing_dates = cleaned["date"].notna()

        converted_dates = pd.to_datetime(
            cleaned.loc[non_missing_dates, "date"],
            errors="coerce"
        )
        if converted_dates.isna().any():
            raise ValueError(
                "Column 'date' contains invalid date values."
            )

        cleaned.loc[non_missing_dates, "date"] = converted_dates

        #Explicit Vaidation for Numeric Column
        for column in self.NUMERIC_COLUMNS:
            non_missing = cleaned[column].notna()

            converted = pd.to_numeric(
                cleaned.loc[non_missing, column],
                errors="coerce",
            )
            if converted.isna().any():
                raise ValueError(
                    f"Column '{column}' contains non-numeric values."
                )
            cleaned.loc[non_missing, column] = converted

        cleaned = cleaned.dropna(
            subset=self.REQUIRED_COLUMNS
        )

        cleaned = cleaned.drop_duplicates(
            subset=["date"],
            keep="first",
        )

        if (cleaned["volume"] < 0).any():
            raise ValueError("Volume cannot be negative.")

        price_columns = ["open", "high", "low", "close"]

        if (cleaned[price_columns] < 0).any().any():
            raise ValueError("Price values cannot be negative.")

        if (cleaned["high"] < cleaned["low"]).any():
            raise ValueError(
                "High price cannot be lower than low price."
            )

        invalid_open = (
            (cleaned["open"] < cleaned["low"])
            | (cleaned["open"] > cleaned["high"])
        )

        if invalid_open.any():
            raise ValueError(
                "Open price must fall within the daily high/low range."
            )

        invalid_close = (
            (cleaned["close"] < cleaned["low"])
            | (cleaned["close"] > cleaned["high"])
        )

        if invalid_close.any():
            raise ValueError(
                "Close price must fall within the daily high/low range."
            )

        cleaned = cleaned.sort_values("date").reset_index(drop=True)

        return cleaned