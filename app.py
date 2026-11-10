"""StockLab · A 股研究台（Streamlit 入口）。

页签是注册制的：加一个新页签只需要在 tabs/ 下新建模块并往 tabs/__init__.py 的 TABS 里加一行。
"""
from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from core import config, data, ui
from core.data import DataError
from core.symbols import parse
from tabs import TABS
from tabs.context import TabContext

st.set_page_config(page_title="StockLab · 研究台", page_icon="📈", layout="wide")

st.title("StockLab · A 股研究台")
st.warning(config.BANNER)

RANGES = {"近 1 年": 365, "近 3 年": 1095, "全区间（2021-11 起）": None}

with st.container(border=True):
    c1, c2, c3, c4 = st.columns([2, 2.2, 2, 1.2])
    code_raw = c1.text_input(
        "股票 / ETF 代码",
        value="600519",
        help="自动补前缀：600519 / sh600519 / 600519.SH 都行；ETF 直接输 159530、510300。",
    )
    bench_label = c2.selectbox("基准", list(config.BENCHMARKS), index=0)
    range_label = c3.radio("区间", list(RANGES), index=0, horizontal=True)
    load = c4.button("加载数据", type="primary", width="stretch")

end = config.today_cn()
start = date.fromisoformat(config.DATA_START) if RANGES[range_label] is None else end - timedelta(days=RANGES[range_label])

with st.expander("数据与缓存", expanded=False):
    ui.note(
        f"免费档：单次最多 250 根、5 次/分钟，超过 250 根会**静默截断成最近 250 根**；"
        f"所以长区间会自动切成多个请求（每片约 {config.MAX_RANGE_DAYS} 天，间隔 {config.CALL_GAP_SEC:.0f} 秒）。"
    )
    ui.note(f"缓存目录：`{config.CACHE_DIR}`（{config.CACHE_TTL_SEC // 3600} 小时过期）")
    if st.button("清空缓存", key="clear_cache"):
        n = data.clear_cache()
        st.success(f"已删除 {n} 个缓存分片。")


def load_data() -> None:
    bar = st.progress(0.0, text="准备中…")

    def on_progress(i: int, total: int, label: str) -> None:
        bar.progress(i / (total + 1), text=f"{sym.code} {i}/{total}：{label}")

    sym = parse(code_raw)
    df = data.fetch_daily(code_raw, start, end, progress=on_progress)
    bench = None
    try:
        bar.progress(len(df) and 0.9, text=f"基准 {bench_label}…")
        bench = data.fetch_daily(config.BENCHMARKS[bench_label], start, end)
    except DataError as exc:
        st.warning(f"基准没取到（{exc}），相对强弱将跳过。")
    bar.progress(1.0, text="完成")
    bar.empty()

    st.session_state["ctx"] = TabContext(
        code=sym.code,
        start=df.index[0].date().isoformat(),
        end=df.index[-1].date().isoformat(),
        df=df,
        bench=bench,
        bench_label=bench_label,
        fee=config.DEFAULT_FEE,
        asset=sym.asset,
        request_start=start.isoformat(),
    )


if load:
    st.session_state.pop("ctx", None)
    try:
        load_data()
    except DataError as exc:
        st.error(str(exc))
    except Exception as exc:  # 兜底：不让页面炸成 traceback
        st.error(f"加载失败：{exc}")

ctx: TabContext | None = st.session_state.get("ctx")

if ctx is None:
    st.info("填好代码、选好区间，点「加载数据」开始。第一次拉全区间大约需要 1 分钟（6 次请求）。")
else:
    if ctx.request_start:
        try:
            req = date.fromisoformat(ctx.request_start)
            act = date.fromisoformat(ctx.start)
            if (act - req).days > 7:
                st.info(
                    f"该标的上市（或可用数据）不足，实际区间从 {ctx.start} 开始，"
                    f"比请求的 {ctx.request_start} 晚了 {(act - req).days} 天——不是数据丢了。"
                )
        except ValueError:
            pass
    ui.note(
        f"当前：**{ctx.code}**（{'ETF' if ctx.asset == 'etf' else '个股'}）｜ "
        f"{ctx.start} ~ {ctx.end} ｜ {len(ctx.df)} 根日线 ｜ "
        f"基准 {ctx.bench_label if ctx.has_bench else '（未取到）'}"
    )
    tabs = st.tabs([t.label for t in TABS])
    for tab, spec in zip(tabs, TABS):
        with tab:
            spec.render(ctx)
