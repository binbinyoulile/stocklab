"""小的展示工具：格式化、指标卡、图表（纵轴按数据自适应，上下留 5%）。"""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

PAD = 0.05


def pct(x: float, digits: int = 1) -> str:
    if x is None or pd.isna(x):
        return "—"
    return f"{x * 100:+.{digits}f}%"


def num(x: float, digits: int = 2) -> str:
    if x is None or pd.isna(x):
        return "—"
    if x == float("inf"):
        return "∞"
    return f"{x:.{digits}f}"


def metric_row(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, (label, value, help_text) in zip(cols, items):
        col.metric(label, value, help=help_text)


def frame_chart(
    df: pd.DataFrame,
    *,
    height: int = 260,
    zero: bool = False,
    pad: float = PAD,
    y_title: str | None = None,
    area: bool = False,
    date_format: str = "%Y-%m",
) -> alt.Chart:
    """折线/面积图：纵轴按数据实际范围放大，并在上下各留 pad（默认 5%）的边距。"""
    long = df.reset_index()
    key = long.columns[0]
    long = long.melt(id_vars=key, var_name="series", value_name="value").dropna()
    if long.empty:
        return alt.Chart(pd.DataFrame({"x": [], "y": []})).mark_line().properties(height=height)

    lo, hi = float(long["value"].min()), float(long["value"].max())
    if zero:
        lo, hi = min(lo, 0.0), max(hi, 0.0)
    span = (hi - lo) or (abs(hi) or 1.0)
    domain = [lo - span * pad, hi + span * pad]

    base = alt.Chart(long).encode(
        x=alt.X(f"{key}:T", title=None,
                axis=alt.Axis(format=date_format, labelAngle=0, tickCount=6)),
        y=alt.Y("value:Q", title=y_title,
                scale=alt.Scale(domain=domain, zero=False)),
        color=alt.Color("series:N", title=None, legend=alt.Legend(orient="bottom")),
        tooltip=[alt.Tooltip(f"{key}:T", title="日期", format="%Y-%m-%d"),
                 alt.Tooltip("series:N", title="系列"),
                 alt.Tooltip("value:Q", title="数值", format=".3f")],
    )
    chart = base.mark_area(opacity=0.45) if area else base.mark_line()
    return chart.properties(height=height)


def show_chart(chart: alt.Chart) -> None:
    st.altair_chart(chart, width="stretch")


def chart(df: pd.DataFrame, **kwargs) -> None:
    show_chart(frame_chart(df, **kwargs))


def note(text: str) -> None:
    st.caption(text)


def caution(text: str) -> None:
    st.markdown(f"**:orange[{text}]**")


def money(x: float) -> str:
    return f"{x:,.0f}"
