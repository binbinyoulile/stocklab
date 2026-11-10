"""冒烟测试：数据层 + 回测引擎（不依赖 Streamlit）。"""
from datetime import date

from core.data import fetch_daily
from core.engine import run_buy_hold, run_strategy

df = fetch_daily("sh600519", date(2025, 11, 1), date(2026, 11, 1))
print("rows", len(df), df.index[0].date(), "→", df.index[-1].date())
print("close min/max", round(df.close.min(), 2), round(df.close.max(), 2))

bh = run_buy_hold(df.close)
print("buy&hold", {k: round(v, 4) if isinstance(v, float) else v for k, v in bh.metrics.items()})

for fast, slow in [(5, 20), (10, 60), (20, 60)]:
    r = run_strategy("ma_cross", df.close, {"fast": fast, "slow": slow}, 0.0008)
    m = r.metrics
    print(
        f"MA {fast}/{slow} ret={m['总收益']:.3%} cagr={m['年化']:.3%} "
        f"dd={m['最大回撤']:.3%} sharpe={m['夏普']:.2f} trades={m['交易次数']} "
        f"win={m['胜率']:.0%} pf={m['盈亏比']:.2f}"
    )

r = run_strategy("rsi", df.close, {"window": 14, "buy": 30, "sell": 70}, 0.0008)
print("RSI trades", r.metrics["交易次数"], "ret", f"{r.metrics['总收益']:.2%}")
if len(r.trades):
    print(r.trades.head(3).to_string(index=False))
