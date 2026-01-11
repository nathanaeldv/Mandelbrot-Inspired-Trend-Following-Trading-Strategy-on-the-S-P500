from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from .strategy import realized_vol_annualized, vol_target_weights, trend_signal_3level


@dataclass(frozen=True)
class BacktestConfig:
    ticker: str = "SPY"
    ma_fast: int = 40
    ma_slow: int = 160
    vol_window: int = 20
    target_vol: float = 0.12
    max_leverage: float = 1.5
    rebalance: str = "W-FRI"            # update weights only on Fridays
    rebalance_threshold: float = 0.15   # only if weight change large enough
    fee_bps: float = 10.0
    slippage_bps: float = 0.0
    rf_annual: float = 0.0
    trading_days_per_year: int = 252    # DAILY


def _apply_rebalance_with_threshold_daily(
    target_w: pd.Series,
    freq: str,
    threshold: float,
) -> pd.Series:
    """
    Daily series -> executed weights that only update on rebalance dates (e.g. W-FRI)
    AND only if relative change is >= threshold. Between rebalances, weight is held.
    """
    if freq == "D":
        rebalance_mask = pd.Series(True, index=target_w.index)
    else:
        rebalance_dates = target_w.resample(freq).last().index
        rebalance_mask = pd.Series(target_w.index.isin(rebalance_dates), index=target_w.index)

    executed = pd.Series(np.nan, index=target_w.index, dtype=float)
    last_w = 0.0

    for dt, w in target_w.items():
        if not np.isfinite(w):
            executed.loc[dt] = last_w
            continue

        if bool(rebalance_mask.loc[dt]):
            denom = max(abs(last_w), 1e-6)
            rel_change = abs(w - last_w) / denom
            if rel_change >= threshold:
                last_w = float(w)

        executed.loc[dt] = last_w

    return executed


def run_backtest(prices: pd.DataFrame, cfg: BacktestConfig) -> pd.DataFrame:
    """
    Daily backtest:
      - returns computed on adj_close (includes dividends if source provides it)
      - 3-level long-only signal to avoid too much cash
      - vol targeting based on realized vol of daily returns (annualized sqrt(252))
      - weekly rebalancing + threshold to limit turnover
    """
    df = prices.copy()

    # Daily returns (use adj_close to include dividends when available)
    df["ret"] = df["adj_close"].pct_change()

    # 3-level long-only signal on close
    df["signal"] = trend_signal_3level(df["close"], cfg.ma_fast, cfg.ma_slow)

    # Realized vol annualized
    df["vol_ann"] = realized_vol_annualized(df["ret"], cfg.vol_window, trading_days=cfg.trading_days_per_year)

    # Target weights
    df["w_target"] = vol_target_weights(
        signal=df["signal"],
        vol_ann=df["vol_ann"],
        target_vol=cfg.target_vol,
        max_leverage=cfg.max_leverage,
    )

    # Executed weights with weekly rebalance + threshold
    df["w_exec"] = _apply_rebalance_with_threshold_daily(
        target_w=df["w_target"],
        freq=cfg.rebalance,
        threshold=cfg.rebalance_threshold,
    )

    # No look-ahead: apply weight from previous day
    df["w_lag"] = df["w_exec"].shift(1).fillna(0.0)

    # Turnover proxy
    df["turnover"] = (df["w_exec"].fillna(0.0) - df["w_exec"].fillna(0.0).shift(1).fillna(0.0)).abs()

    # Costs
    cost_rate = (cfg.fee_bps + cfg.slippage_bps) / 10000.0
    df["costs"] = cost_rate * df["turnover"]

    # Strategy returns
    df["strategy_returns_gross"] = df["w_lag"] * df["ret"]
    df["strategy_returns"] = df["strategy_returns_gross"] - df["costs"]

    # Equity curves
    df["equity_buyhold"] = (1.0 + df["ret"].fillna(0.0)).cumprod()
    df["equity_strategy"] = (1.0 + df["strategy_returns"].fillna(0.0)).cumprod()

    df = df.dropna(subset=["ret"], how="any")
    return df
