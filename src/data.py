from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pathlib import Path


import pandas as pd
import yfinance as yf
from pandas_datareader import data as pdr


@dataclass(frozen=True)
class DataDownloadResult:
    source: str
    df: pd.DataFrame


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure we return columns:
    open, high, low, close, adj_close, volume
    indexed by DatetimeIndex (ascending), with no NaNs.
    """
    out = df.copy()
    out.index = pd.to_datetime(out.index)
    out = out.sort_index()

    required = {"open", "high", "low", "close", "adj_close", "volume"}
    missing = required - set(out.columns)
    if missing:
        raise ValueError(f"Missing columns after normalization: {missing}")

    out = out.dropna()
    return out


def _download_yfinance(ticker: str, start: str, end: Optional[str]) -> pd.DataFrame:
    df = yf.download(
        tickers=ticker,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        actions=False,
        threads=False,
    )

    if df is None or df.empty:
        return pd.DataFrame()

    # Handle possible MultiIndex columns
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    needed = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
    if not needed.issubset(set(df.columns)):
        return pd.DataFrame()

    out = pd.DataFrame(index=df.index)
    out["open"] = df["Open"].astype(float)
    out["high"] = df["High"].astype(float)
    out["low"] = df["Low"].astype(float)
    out["close"] = df["Close"].astype(float)
    out["adj_close"] = df["Adj Close"].astype(float)
    out["volume"] = df["Volume"].astype(float)

    return _normalize_ohlcv(out)


def _download_stooq(ticker: str, start: str, end: Optional[str]) -> pd.DataFrame:
    """
    Stooq symbols can differ. We'll try a list of candidates.
    For US tickers, common form is 'spy.us'.
    """
    base = ticker.lower().replace("^", "")

    candidates = []
    # Most common for US equities/ETFs
    if "." not in base:
        candidates.append(f"{base}.us")
    candidates.append(base)  # as-is (in case user passed "spy.us")
    # Some users pass uppercase; pandas_datareader is ok but we keep consistent
    candidates.append(f"{base.upper()}.US".lower())

    last_err = None
    for sym in candidates:
        try:
            df = pdr.DataReader(sym, "stooq")
            if df is None or df.empty:
                continue

            df = df.sort_index()

            out = pd.DataFrame(index=df.index)
            out["open"] = df["Open"].astype(float)
            out["high"] = df["High"].astype(float)
            out["low"] = df["Low"].astype(float)
            out["close"] = df["Close"].astype(float)
            out["adj_close"] = out["close"]  # Stooq may not provide adj close
            out["volume"] = df["Volume"].astype(float)

            # filter date range (end is exclusive)
            start_dt = pd.to_datetime(start)
            if end is not None:
                end_dt = pd.to_datetime(end)
                out = out.loc[(out.index >= start_dt) & (out.index < end_dt)]
            else:
                out = out.loc[out.index >= start_dt]

            out = _normalize_ohlcv(out)

            # Only accept if we have enough history
            if not out.empty:
                return out

        except Exception as e:
            last_err = e
            continue

    # If all candidates fail
    if last_err is not None:
        raise last_err
    return pd.DataFrame()



def download_price_history(
    ticker: str,
    start: str,
    end: Optional[str],
    retries: int = 5,
    backoff_seconds: float = 2.0,
) -> DataDownloadResult:
    """
    Downloads OHLCV with best effort:
      1) yfinance with retry/backoff (handles transient rate limiting)
      2) fallback to Stooq (pandas_datareader)

    Note: 'end' is treated as exclusive bound in this project.
    Pass (end_inclusive + 1 day) from main.py.
    """
    cache_dir = Path("data_cache")
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / f"{ticker}_{start}_{end}.parquet"

    if cache_file.exists():
        df = pd.read_parquet(cache_file)
        df.to_parquet(cache_file)
        return DataDownloadResult(source="cache", df=_normalize_ohlcv(df))
    
    # 1) yfinance with retry/backoff
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            df = _download_yfinance(ticker, start, end)
            if not df.empty:
                df.to_parquet(cache_file)
                return DataDownloadResult(source="yfinance", df=df)
        except Exception as e:
            last_err = e

        # backoff
        sleep_for = backoff_seconds * attempt
        time.sleep(sleep_for)

    # 2) fallback: Stooq
    try:
        df = _download_stooq(ticker, start, end)
        if not df.empty:
            return DataDownloadResult(source="stooq", df=df)
    except Exception as e:
        last_err = e

    # If both failed
    if last_err is not None:
        raise RuntimeError(
            f"Failed to download data for {ticker} from yfinance (retries={retries}) and fallback stooq. "
            f"Last error: {repr(last_err)}"
        )
    raise RuntimeError(f"Failed to download data for {ticker} from yfinance and stooq (no data).")
