from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from pandas.tseries.offsets import BDay

from src.data import download_price_history
from src.backtest import run_backtest, BacktestConfig
from src.metrics import compute_kpis
from src.plotting import plot_equity_curve


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Mandelbrot-inspired Trend Following + Vol Targeting (daily bars, weekly rebalance) with warmup."
    )

    p.add_argument("--ticker", type=str, default="SPY")
    p.add_argument("--start", type=str, default="2015-01-01")
    p.add_argument("--end", type=str, default="2024-12-31")  # inclusive for reporting

    p.add_argument("--ma_fast", type=int, default=40)
    p.add_argument("--ma_slow", type=int, default=160)
    p.add_argument("--vol_window", type=int, default=20)

    p.add_argument("--target_vol", type=float, default=0.12)
    p.add_argument("--max_leverage", type=float, default=1.5)

    p.add_argument("--rebalance", type=str, default="W-FRI")
    p.add_argument("--rebalance_threshold", type=float, default=0.15)

    p.add_argument("--fee_bps", type=float, default=10.0)
    p.add_argument("--slippage_bps", type=float, default=0.0)
    p.add_argument("--rf", type=float, default=0.0)

    p.add_argument("--warmup_bdays", type=int, default=260, help="Business-day warmup downloaded before start")
    p.add_argument("--outdir", type=str, default="outputs")

    return p.parse_args()


def main() -> None:
    args = parse_args()

    start_dt = pd.to_datetime(args.start)
    end_inclusive = pd.to_datetime(args.end)

    # Download warm-up history before start to avoid flat equity due to MA/vol NaNs
    download_start = (start_dt - BDay(args.warmup_bdays)).date().isoformat()

    # Inclusive end (reporting) -> exclusive end (download)
    end_exclusive = (end_inclusive + pd.Timedelta(days=1)).date().isoformat()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # Download ONCE (yfinance with fallback stooq + cache handled in src.data)
    data_res = download_price_history(args.ticker, download_start, end_exclusive)
    prices = data_res.df

    print(
        f"Data source used: {data_res.source} | rows={len(prices)} | "
        f"{prices.index.min().date()} -> {prices.index.max().date()}"
    )

    # Fail fast if dataset doesn't cover requested start (after warmup)
    if prices.index.max() < start_dt:
        raise RuntimeError(
            f"No overlap with requested reporting window. "
            f"Requested start={args.start}, but data ends at {prices.index.max().date()}."
        )

    cfg = BacktestConfig(
        ticker=args.ticker,
        ma_fast=args.ma_fast,
        ma_slow=args.ma_slow,
        vol_window=args.vol_window,
        target_vol=args.target_vol,
        max_leverage=args.max_leverage,
        rebalance=args.rebalance,
        rebalance_threshold=args.rebalance_threshold,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        rf_annual=args.rf,
        trading_days_per_year=252,
    )

    bt_full = run_backtest(prices, cfg)

    # Slice strictly to requested reporting window (inclusive end)
    bt = bt_full.loc[(bt_full.index >= start_dt) & (bt_full.index <= end_inclusive)].copy()
    if bt.empty:
        raise RuntimeError(
            f"Backtest produced no rows in requested window {args.start} -> {args.end}. "
            f"Data coverage: {prices.index.min().date()} -> {prices.index.max().date()}."
        )

    # KPIs (daily frequency)
    kpi_strategy = compute_kpis(bt["strategy_returns"], rf_annual=cfg.rf_annual, trading_days=cfg.trading_days_per_year)
    kpi_buyhold = compute_kpis(bt["ret"], rf_annual=cfg.rf_annual, trading_days=cfg.trading_days_per_year)

    # Persist outputs (report window only)
    bt["equity_strategy_rebased"] = bt["equity_strategy"] / bt["equity_strategy"].iloc[0]
    bt["equity_buyhold_rebased"] = bt["equity_buyhold"] / bt["equity_buyhold"].iloc[0]

    bt.to_csv(outdir / "daily_timeseries.csv", index=True)

    summary = {
        **asdict(cfg),
        "data_source": data_res.source,
        "download_start": download_start,
        "report_start": args.start,
        "report_end": args.end,
        "kpi_strategy": kpi_strategy,
        "kpi_buyhold": kpi_buyhold,
    }
    (outdir / "results_summary.json").write_text(
        pd.Series(summary).to_json(indent=2),
        encoding="utf-8",
    )

    plot_equity_curve(bt, outdir / "equity_curve.png", title=f"{cfg.ticker} - Trend (3-level) + Vol Targeting (Daily)")

    # Print summary
    print("\n=== CONFIG ===")
    for k, v in asdict(cfg).items():
        print(f"{k}: {v}")
    print(f"data_source: {data_res.source}")
    print(f"download_start: {download_start}")
    print(f"report_window: {args.start} -> {args.end}")

    print("\n=== KPI SUMMARY (Strategy) ===")
    for k, v in kpi_strategy.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")

    print("\n=== KPI SUMMARY (Buy&Hold) ===")
    for k, v in kpi_buyhold.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")

    print(f"\nSaved outputs to: {outdir.resolve()}")


if __name__ == "__main__":
    main()
