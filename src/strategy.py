from __future__ import annotations

import numpy as np
import pandas as pd


def moving_average(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def realized_vol_annualized(returns: pd.Series, window: int, trading_days: int = 252) -> pd.Series:
    """
    Realized volatility: rolling std of daily returns, annualized by sqrt(252).
    """
    vol_daily = returns.rolling(window=window, min_periods=window).std()
    return vol_daily * np.sqrt(trading_days)


def trend_signal(prices: pd.Series, ma_fast: int, ma_slow: int) -> pd.Series:
    """
    Multi-scale trend signal:
      +1 if price > MA_fast > MA_slow
      -1 if price < MA_fast < MA_slow
       0 otherwise
    """
    fast = moving_average(prices, ma_fast)
    slow = moving_average(prices, ma_slow)

    sig = pd.Series(0.0, index=prices.index)
    sig[(prices > fast) & (fast > slow)] = 1.0
    sig[(prices < fast) & (fast < slow)] = -1.0
    return sig


def vol_target_weights(
    signal: pd.Series,
    vol_ann: pd.Series,
    target_vol: float,
    max_leverage: float,
) -> pd.Series:
    """
    Weight = signal * min(max_leverage, target_vol / vol_ann)
    Weight is in [-max_leverage, +max_leverage].
    """
    raw = target_vol / vol_ann.replace(0.0, np.nan)
    scale = raw.clip(lower=0.0, upper=max_leverage)
    w = signal * scale
    return w

def trend_signal_3level(prices: pd.Series, ma_fast: int, ma_slow: int) -> pd.Series:
    """
    3-level long-only signal (Mandelbrot-compatible, less time in cash):
      1.0  if price > MA_fast > MA_slow
      0.5  if price > MA_slow but not in full alignment
      0.0  otherwise

    (You can extend symmetrically for short later.)
    """
    fast = moving_average(prices, ma_fast)
    slow = moving_average(prices, ma_slow)

    sig = pd.Series(0.0, index=prices.index)
    sig[(prices > slow)] = 0.5
    sig[(prices > fast) & (fast > slow)] = 1.0
    sig = sig.fillna(0.0)
    return sig

