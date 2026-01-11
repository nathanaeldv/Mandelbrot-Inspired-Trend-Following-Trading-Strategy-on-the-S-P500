from __future__ import annotations

import numpy as np
import pandas as pd


def _annualize_return(equity: pd.Series, trading_days: int = 252) -> float:
    if equity.empty:
        return float("nan")
    total = float(equity.iloc[-1] / equity.iloc[0])
    years = len(equity) / trading_days
    if years <= 0:
        return float("nan")
    return total ** (1.0 / years) - 1.0


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return float("nan")
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def compute_kpis(strategy_returns: pd.Series, rf_annual: float = 0.0, trading_days: int = 252) -> dict:
    """
    KPIs on strategy daily returns.
    """
    r = strategy_returns.dropna().astype(float)
    if r.empty:
        return {"error": "no returns"}

    equity = (1.0 + r).cumprod()

    cagr = _annualize_return(equity, trading_days=trading_days)
    vol = float(r.std() * np.sqrt(trading_days))

    rf_daily = (1.0 + rf_annual) ** (1.0 / trading_days) - 1.0
    excess = r - rf_daily
    sharpe = float(excess.mean() / (excess.std() + 1e-12) * np.sqrt(trading_days))

    downside = r[r < 0]
    downside_std = float(downside.std() * np.sqrt(trading_days)) if len(downside) > 1 else float("nan")
    sortino = float(excess.mean() / ((downside.std() + 1e-12)) * np.sqrt(trading_days)) if len(downside) > 1 else float("nan")

    mdd = _max_drawdown(equity)
    calmar = float(cagr / abs(mdd)) if mdd < 0 else float("nan")

    hit_rate = float((r > 0).mean())
    avg_win = float(r[r > 0].mean()) if (r > 0).any() else float("nan")
    avg_loss = float(r[r < 0].mean()) if (r < 0).any() else float("nan")

    # Tail-ish diagnostics
    skew = float(r.skew())
    kurt = float(r.kurtosis())

    return {
        "CAGR": float(cagr),
        "AnnVol": float(vol),
        "Sharpe": float(sharpe),
        "Sortino": float(sortino),
        "MaxDrawdown": float(mdd),
        "Calmar": float(calmar),
        "HitRate": float(hit_rate),
        "AvgDailyWin": float(avg_win),
        "AvgDailyLoss": float(avg_loss),
        "Skew": float(skew),
        "Kurtosis": float(kurt),
        "TotalReturn": float(equity.iloc[-1] - 1.0),
        "NumDays": int(len(r)),
    }
