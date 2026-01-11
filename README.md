# Mandelbrot-Inspired-Trend-Following-Trading-Strategy-on-the-S-P500
A systematic trend-following strategy on the S&amp;P 500 inspired by Mandelbrot, combining multi-scale moving averages with volatility-targeted position sizing. The focus is on risk control, drawdown reduction, and regime-aware exposure, implemented and backtested end-to-end in Python

1. Project Objective

This project implements and analyzes a systematic trading strategy inspired by the work of Benoît Mandelbrot, applied to the S&P 500 ETF (SPY).
The objective is not to maximize short-term absolute returns, but to design a robust exposure framework that:
- accounts for non-Gaussian return distributions,
- adapts to changing volatility regimes,
- prioritizes risk control and drawdown management,
- reflects design principles commonly used on macro, CTA, and systematic trading desks.
The strategy is fully implemented in Python, backtested end-to-end, and documented with transparent assumptions.


2. Theoretical Background
2.1 Limits of the Gaussian Framework
Empirical market data exhibits:
- fat tails,
- volatility clustering,
- regime shifts.

These stylized facts, emphasized by Benoît Mandelbrot, challenge classical assumptions such as:
- independent and identically distributed returns,
- constant variance,
- purely mean-variance optimization.
As a result, this project adopts a risk-first approach, where exposure is adjusted dynamically based on market volatility, not solely on directional forecasts.


3. Strategy Description
3.1 Trading Universe

- Asset: SPY (S&P 500 ETF)
- Data frequency: Daily
- Reporting window: 2023-01-01 → 2024-12-31
- Data source: Stooq (price returns; dividends not included)


3.2 Directional Signal: Multi-Scale Trend Following
Trend identification relies on two moving averages:
- Fast moving average: 40 days
- Slow moving average: 160 days

This 1:4 ratio (similar to the classic 50/200) provides a balance between responsiveness and noise reduction, while being better suited to limited sample sizes.

Three-Level Long-Only Signal
Instead of a binary in/out signal, exposure is graduated:

Condition	Signal
Price > MA40 > MA160	               +1.0
Price > MA160 (partial alignment)	   +0.5
Otherwise	                            0.0

This design:
- avoids excessive time spent in cash,
- reduces unnecessary turnover,
- captures persistent upward trends without over-reacting to short-term noise.


3.3 Position Sizing: Volatility Targeting
Position size is dynamically adjusted using realized volatility:
- Realized volatility: rolling standard deviation over 20 days
- Annualization: √252
- Target volatility: 12%
- Maximum leverage: 1.5x

Conceptually:
Weight = Signal × min(Max Leverage, Target Volatility / Realized Volatility)

This mechanism:
- reduces exposure during high-volatility regimes,
- increases exposure when markets are stable,
- aims to maintain a consistent risk profile over time.


3.4 Rebalancing and Transaction Costs
- Signal computation: daily
- Execution / rebalancing: weekly (Friday)
- Rebalancing threshold: 15% relative change in target weight
- Transaction costs: 2 bps per unit of turnover
- Slippage: 0 bps
The combination of weekly rebalancing and a threshold rule significantly reduces unnecessary trading and reflects realistic operational constraints.


4. Backtesting Methodology
4.1 Warm-Up Period
Additional historical data is downloaded prior to the reporting window to:
- stabilize moving averages,
- avoid artificially flat equity curves caused by indicator initialization.
All performance metrics and plots are computed strictly within the reporting window.


4.2 Benchmark
- Buy & Hold SPY (price return)
- Same date range
- Same daily frequency (252 trading days/year)

Both equity curves are rebased to 1.0 at the start of the reporting period for direct visual comparison.


5. Empirical Results (2023–2024)
5.1 Final Parameters
- MA fast / slow: 40 / 160
- Volatility window: 20
- Target volatility: 12%
- Max leverage: 1.5
- Transaction costs: 2 bps
- Rebalancing: weekly


5.2 Strategy Performance
- CAGR: 14.5%
- Annualized volatility: 11.2%
- Sharpe ratio: 1.26
- Sortino ratio: 1.58
- Maximum drawdown: −7.3%
- Calmar ratio: 1.98
- Hit rate: 53.8%
- Total return: 30.9%

5.3 Buy & Hold SPY Performance
- CAGR: 25.9%
- Annualized volatility: 12.8%
- Sharpe ratio: 1.85
- Maximum drawdown: −10.0%
- Total return: 57.6%
<img width="1024" height="768" alt="equity_curve" src="https://github.com/user-attachments/assets/b371fb5d-2fb6-4069-a8a1-572e02c63247" />


6. Interpretation of Results
6.1 Relative Performance
Over a strongly bullish period (2023–2024), the strategy underperforms Buy & Hold in absolute return, which is expected by construction.
However, it achieves:
- lower volatility,
- significantly reduced drawdowns,
- more stable risk exposure.
This behavior is fully consistent with the strategy’s design philosophy.


6.2 Risk-Adjusted Profile
The strategy exhibits:
- smoother equity growth,
- controlled downside risk,
- implicit convexity with respect to volatility shocks.
It is not designed to outperform during pure bull markets, but rather to maximize risk-adjusted growth across full market cycles.


7. Limitations and Extensions
Current limitations
- Stooq data → price return only (no dividends)
- Single-asset universe
- Relatively short evaluation period

Natural extensions
- Multi-asset portfolios (equities, bonds, commodities)
- Cross-asset volatility allocation
- Long/short asymmetry
- Stress testing over crisis periods (2008, 2020)


8. Conclusion

This project demonstrates an institutionally-aligned approach to systematic trading, focused on:
- regime awareness
- volatility-driven risk control
- structural robustness rather than opportunistic optimization

The framework is directly extensible to multi-asset or institutional-grade strategies and reflects design principles commonly used in CTA and macro systematic portfolios.

