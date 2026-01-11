from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


def plot_equity_curve(bt: pd.DataFrame, path: Path, title: str) -> None:
    """
    Plot strategy equity vs buy&hold, both rebased to 1.0 at the first date of bt.
    Expects columns: 'equity_strategy', 'equity_buyhold'.
    """
    if bt.empty:
        raise ValueError("Backtest dataframe is empty; cannot plot.")

    eq_s = bt["equity_strategy"].astype(float).copy()
    eq_b = bt["equity_buyhold"].astype(float).copy()

    # Rebase to 1.0 at start of displayed window
    eq_s = eq_s / float(eq_s.iloc[0])
    eq_b = eq_b / float(eq_b.iloc[0])

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(bt.index, eq_s, label="Strategy (rebased)")
    ax.plot(bt.index, eq_b, label="Buy&Hold (rebased)")
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity (base 1.0)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
