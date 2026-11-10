"""页签 A：体检（趋势 / 回撤 / 波动 / 相对基准）。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import ui
from core.engine import drawdown, sma

from .context import TabContext

SQRT252 = 252 ** 0.5


def render(ctx: TabContext) -> None:
    close = ctx.close
    s20, s60 = sma(close, 20), sma(close, 60)
    last = float(close.iloc[-1])
    a, b = float(s20.iloc[-1]), float(s60.iloc[-1])

    if last > a > b:
        trend, why = "多头排列", f"收盘 {last:.2f} > SMA20 {a:.2f} > SMA60 {b:.2f}"
    elif last < a < b:
        trend, why = "空头排列", f"收盘 {last:.2f} < SMA20 {a:.2f} < SMA60 {b:.2f}"
    else:
        trend, why = "震荡", f"价格与两条均线交错（收盘 {last:.2f}，SMA20 {a:.2f}，SMA60 {b:.2f}）"

    dd = drawdown(close)
    mdd_i = dd.idxmin()
    peak_i = close.loc[:mdd_i].idxmax()
    dd_days = int((mdd_i - peak_i).days)
    ret = close.pct_change().dropna()
    vol = float(ret.std() * SQRT252)
    vol20 = float(ret.tail(20).std() * SQRT252)
    roll_vol = ret.rolling(20).std() * SQRT252
    rank = float((roll_vol.dropna() < vol20).mean())

    with st.container(border=True):
        st.subheader("趋势状态")
        ui.metric_row([
            ("状态", trend, "收盘价与 SMA20 / SMA60 的排列"),
            ("最新收盘", f"{last:.2f}", None),
            ("SMA20", f"{a:.2f}", None),
            ("SMA60", f"{b:.2f}", None),
        ])
        ui.note(why)
        ui.chart(pd.DataFrame({"收盘": close, "SMA20": s20, "SMA60": s60}), height=240)

    with st.container(border=True):
        st.subheader("回撤")
        ui.metric_row([
            ("当前回撤", ui.pct(float(dd.iloc[-1])), "距区间最高点"),
            ("区间最大回撤", ui.pct(float(dd.min())), "峰到谷"),
            ("最大回撤区间", f"{peak_i:%Y-%m-%d} → {mdd_i:%Y-%m-%d}", f"{dd_days} 个自然日"),
            ("距前高", f"{int((close.index[-1] - peak_i).days)} 天", "最后一次新高的时间"),
        ])
        ui.chart(dd.to_frame("回撤"), height=180, zero=True, pad=0.02, area=True)

    with st.container(border=True):
        st.subheader("波动")
        ui.metric_row([
            ("年化波动", ui.pct(vol), "日收益标准差 × √252"),
            ("近 20 日波动", ui.pct(vol20), "短期波动"),
            ("历史分位", f"{rank * 100:.0f}%", "近20日波动在过去的分位（越低越安静）"),
            ("最大单日涨跌", f"{ui.pct(float(ret.max()))} / {ui.pct(float(ret.min()))}", None),
        ])
        ui.chart(roll_vol.dropna().to_frame("20日滚动年化波动"), height=180, zero=True, pad=0.02)

    with st.container(border=True):
        st.subheader(f"相对基准（{ctx.bench_label}）")
        if not ctx.has_bench:
            st.info("基准数据没取到，这一块跳过。可以换一个基准再试。")
            st.divider()
            st.markdown(
                f"**一句话**：趋势{trend}；当前回撤 {ui.pct(float(dd.iloc[-1]))}（区间最大 {ui.pct(float(dd.min()))}）；"
                f"年化波动 {ui.pct(vol)}；基准缺数据，相对强弱未计算。"
            )
            return
        bclose = ctx.bench["close"].reindex(close.index).ffill().bfill()
        stock_n = close / close.iloc[0]
        bench_n = bclose / bclose.iloc[0]
        excess = stock_n / bench_n - 1
        r20 = float(stock_n.iloc[-1] / stock_n.iloc[-21] - bench_n.iloc[-1] / bench_n.iloc[-21])
        r60 = float(stock_n.iloc[-1] / stock_n.iloc[-61] - bench_n.iloc[-1] / bench_n.iloc[-61])
        corr = float(ret.corr(bclose.pct_change().reindex(ret.index)))
        ui.metric_row([
            ("区间超额", ui.pct(float(excess.iloc[-1])), "个股累计 − 基准累计"),
            ("近 20 日相对强弱", ui.pct(r20), "正=跑赢"),
            ("近 60 日相对强弱", ui.pct(r60), "正=跑赢"),
            ("与基准相关性", f"{corr:.2f}", None),
        ])
        ui.chart(pd.DataFrame({"个股": stock_n, "基准": bench_n}), height=200)

    st.divider()
    st.markdown(
        f"**一句话**：趋势{trend}；当前回撤 {ui.pct(float(dd.iloc[-1]))}（区间最大 {ui.pct(dd.min())}）；"
        f"年化波动 {ui.pct(vol)}；近 60 日相对基准 {ui.pct(r60)}。"
    )
