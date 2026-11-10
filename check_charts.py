"""验收：图表纵轴自适应（5% 边距）+ 两个量级差异极大的标的都能画出图。"""
from datetime import date

import pandas as pd

from core import ui
from core.data import fetch_daily
from core.engine import run_strategy, run_buy_hold


def domain_of(chart) -> tuple[float, float]:
    spec = chart.to_dict()
    enc = spec["encoding"]["y"]["scale"]["domain"]
    return float(enc[0]), float(enc[1])


for raw in ["159530", "600519"]:
    df = fetch_daily(raw, date(2025, 11, 1), date(2026, 11, 8))
    close = df["close"]
    series = pd.DataFrame({
        "收盘": close,
        "SMA20": close.rolling(20).mean(),
        "SMA60": close.rolling(60).mean(),
    })
    ch = ui.frame_chart(series)
    lo, hi = domain_of(ch)
    data_lo, data_hi = float(series.min().min()), float(series.max().max())
    span = data_hi - data_lo
    ok = lo < data_lo and hi > data_hi and abs((data_lo - lo) - span * 0.05) < span * 0.01
    print(
        f"{raw:8s} 价格 {data_lo:.3f}~{data_hi:.3f} 轴 {lo:.3f}~{hi:.3f} "
        f"上下边距 {(data_lo - lo) / span:.3%}/{(hi - data_hi) / span:.3%} {'OK' if ok else 'FAIL'}"
    )

    res = run_strategy("ma_cross", close, {"fast": 10, "slow": 30}, 0.0008)
    bh = run_buy_hold(close)
    eq = ui.frame_chart(pd.DataFrame({"策略": res.equity, "买入持有": bh.equity}))
    elo, ehi = domain_of(eq)
    print(f"         净值轴 {elo:.3f}~{ehi:.3f}（策略末值 {res.equity.iloc[-1]:.3f}）")

    dd = (close / close.cummax() - 1).to_frame("回撤")
    dch = ui.frame_chart(dd, zero=True, pad=0.02, area=True)
    dlo, dhi = domain_of(dch)
    print(f"         回撤轴 {dlo:.3%}~{dhi:.3%}（数据 {dd.min().iloc[0]:.3%}~{dd.max().iloc[0]:.3%}）")
