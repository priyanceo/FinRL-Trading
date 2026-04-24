"""Data processor module for fetching and preprocessing stock market data.

Handles downloading historical price data, computing technical indicators,
and preparing datasets for RL environment consumption.
"""

import logging
from datetime import datetime
from typing import List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from stockstats import StockDataFrame

from finrl_trading.config import DataConfig

logger = logging.getLogger(__name__)


class DataProcessor:
    """Fetches and preprocesses market data for RL training and backtesting."""

    def __init__(self, config: DataConfig):
        self.config = config

    def download(self, tickers: List[str]) -> pd.DataFrame:
        """Download OHLCV data for a list of tickers using yfinance.

        Args:
            tickers: List of ticker symbols to download.

        Returns:
            DataFrame with columns [date, tic, open, high, low, close, volume].
        """
        logger.info(
            "Downloading data for %d tickers from %s to %s",
            len(tickers),
            self.config.start_date,
            self.config.end_date,
        )

        raw = yf.download(
            tickers,
            start=self.config.start_date,
            end=self.config.end_date,
            auto_adjust=True,
            progress=False,
        )

        if raw.empty:
            raise ValueError("yfinance returned empty DataFrame — check tickers/dates.")

        # Flatten multi-level columns when multiple tickers are requested
        if isinstance(raw.columns, pd.MultiIndex):
            raw = raw.stack(level=1).rename_axis(["date", "tic"]).reset_index()
        else:
            raw = raw.reset_index()
            raw["tic"] = tickers[0]

        raw.columns = [c.lower() for c in raw.columns]
        raw = raw.rename(columns={"adj close": "close"} if "adj close" in raw.columns else {})
        raw = raw[["date", "tic", "open", "high", "low", "close", "volume"]]
        raw["date"] = pd.to_datetime(raw["date"])
        raw = raw.sort_values(["date", "tic"]).reset_index(drop=True)

        logger.info("Downloaded %d rows.", len(raw))
        return raw

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute technical indicators defined in DataConfig.

        Args:
            df: Raw OHLCV DataFrame (multi-ticker, long format).

        Returns:
            DataFrame augmented with indicator columns.
        """
        indicators = self.config.technical_indicators
        if not indicators:
            return df

        logger.info("Computing indicators: %s", indicators)
        frames = []
        for tic, group in df.groupby("tic"):
            stock = StockDataFrame.retype(group.copy())
            for ind in indicators:
                try:
                    _ = stock[ind]  # triggers stockstats computation
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Could not compute %s for %s: %s", ind, tic, exc)
            frames.append(stock)

        result = pd.concat(frames).sort_values(["date", "tic"]).reset_index(drop=True)
        # Drop rows with NaN introduced by indicator look-back windows
        result = result.dropna(subset=indicators, how="any").reset_index(drop=True)
        return result

    def add_vix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merge CBOE VIX close price as a turbulence proxy column."""
        logger.info("Fetching VIX data.")
        vix_raw = yf.download("^VIX", start=self.config.start_date, end=self.config.end_date,
                              auto_adjust=True, progress=False)
        if vix_raw.empty:
            logger.warning("VIX data unavailable; skipping.")
            return df

        vix = vix_raw[["Close"]].rename(columns={"Close": "vix"}).reset_index()
        vix.columns = [c.lower() for c in vix.columns]
        vix["date"] = pd.to_datetime(vix["date"])
        df = df.merge(vix, on="date", how="left")
        df["vix"] = df["vix"].ffill()
        return df

    def split(self, df: pd.DataFrame):
        """Split data into train and test sets by date.

        Returns:
            Tuple of (train_df, test_df).
        """
        split_date = pd.Timestamp(self.config.split_date)
        train = df[df["date"] < split_date].reset_index(drop=True)
        test = df[df["date"] >= split_date].reset_index(drop=True)
        logger.info("Train rows: %d | Test rows: %d", len(train), len(test))
        return train, test

    def process(self, tickers: List[str]) -> tuple:
        """Full pipeline: download → indicators → VIX → split.

        Returns:
            Tuple of (train_df, test_df).
        """
        df = self.download(tickers)
        df = self.add_technical_indicators(df)
        if self.config.use_vix:
            df = self.add_vix(df)
        return self.split(df)
