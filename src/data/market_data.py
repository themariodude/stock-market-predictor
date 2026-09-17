from abc import ABC, abstractmethod
import pandas as pd
import yfinance as yf


class MarketDataProvider(ABC):
    """Abstract Base Class to isolate market data provider implementations."""

    @abstractmethod
    def fetch_historical_data(
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Fetch historical stock data.
        Must return a DataFrame with standard columns:
        ['date', 'open', 'high', 'low', 'close', 'volume']
        """
        pass


class YFinanceProvider(MarketDataProvider):
    """Yahoo Finance implementation for prototype and educational use."""

    REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume"]

    def fetch_historical_data(
        self, ticker: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        if not ticker or not isinstance(ticker, str):
            raise ValueError("Ticker symbol must be a non-empty string.")

        # auto_adjust=False ensures Open, High, Low, Close, Volume remain standard
        df = yf.download(
            tickers=ticker,
            start = pd.to_datetime(start_date),
            end = pd.to_datetime(end_date),
            progress=False,
            auto_adjust=False,
        )

        if df.empty:
            raise ValueError(
                f"No data returned for ticker '{ticker}' between {start_date} and {end_date}."
            )

        # Handle multi-level index columns if returned by newer yfinance versions
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Reset index to turn 'Date' into a standard column
        df = df.reset_index()

        # Validate that required schema exists
        missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise KeyError(f"Missing expected columns from feed: {missing}")

        # Standardize column naming to lowercase
        df = df[self.REQUIRED_COLUMNS].copy()
        df.columns = ["date", "open", "high", "low", "close", "volume"]

        # Ensure date format is uniform datetime and drop any incomplete records
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna().reset_index(drop=True)

        return df