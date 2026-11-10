"""页签 B：回测（规则 → 结果 → 参数邻域 → 导出）。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core import ui
from core.engine import STRATEGIES, run_buy_hold, run_strategy

from .context import TabContext


def _trade_table(trades: pd.DataFrame) -> pd.DataFrame:
    if not len(trades):
        return trades
    col = {
        "entry_date": "买入日",
        "exit_date": "卖出日",
        "entry_price": "买入价",
        "exit_price": "卖出价",
        "days": "持有天数",
        "return": "单笔收益",
        "open": "未平仓",
    }
    out = trades.rename(columns=col)
    out["单笔收益"] = (out["单笔收益"] * 100).round(2).astype(str) + "%"
    if "未平仓" in out.columns:
        out["未平仓"] = out["未平仓"].map({True: "是", False: ""})
    return out


def render(ctx: TabContext) -> None:
    close = ctx.close

    with st.container(border=True):
        st.subheader("规则与参数")
        keys = list(STRATEGIES)
        key = st.selectbox(
            "规则类型",
            keys,
            format_func=lambda k: STRATEGIES[k]["label"],
            help="第一版只内置三种；加新规则在 core/engine.py 的 STRATEGIES 里注册即可。",
        )
        spec = STRATEGIES[key]
        ui.note(spec["desc"])

        cols = st.columns(len(spec["params"]) + 1)
        params = {}
        for c, p in zip(cols, spec["params"]):
            params[p["key"]] = c.number_input(
                p["label"],
                min_value=p["min"],
                max_value=p["max"],
                value=p["default"],
                step=p["step"],
                key=f"p_{key}_{p['key']}",
            )
        fee_pct = cols[-1].number_input(
            "往返费率 %", min_value=0.0, max_value=2.0, value=ctx.fee * 100, step=0.02,
            help="买卖各扣一半；默认 0.08%（万2.5佣金+卖出印花税）。未计滑点。",
        )

    if key == "ma_cross" and params["fast"] >= params["slow"]:
        st.error("短均线必须小于长均线。")
        return

    fee = fee_pct / 100
    res = run_strategy(key, close, params, fee)
    bh = run_buy_hold(close)
    m, bm = res.metrics, bh.metrics

    with st.container(border=True):
        st.subheader("结果")
        ui.metric_row([
            ("总收益", ui.pct(m["总收益"]), None),
            ("年化", ui.pct(m["年化"]), None),
            ("最大回撤", ui.pct(m["最大回撤"]), None),
            ("夏普", ui.num(m["夏普"]), None),
            ("交易次数", str(m["交易次数"]), None),
        ])
        ui.metric_row([
            ("买入持有收益", ui.pct(bm["总收益"]), None),
            ("买入持有回撤", ui.pct(bm["最大回撤"]), None),
            ("策略−基准", ui.pct(m["总收益"] - bm["总收益"]), "总收益差"),
            ("超额（风险调整）", ui.num(m["夏普"] - bm["夏普"]), "夏普差"),
            ("持仓时间", f"{m['持仓时间占比'] * 100:.0f}%", None),
        ])
        ui.chart(pd.DataFrame({"策略": res.equity, "买入持有": bh.equity}), height=280)
        st.caption(
            f"成本假设：往返 {fee * 100:.2f}%（买卖各 {fee * 50:.2f}%）；"
            "信号在 T 日收盘确认、T+1 收盘成交；未计滑点与涨跌停。"
        )

    with st.container(border=True):
        st.subheader("交易明细")
        if not len(res.trades):
            st.info("这个区间里没有产生交易。可以放宽参数或换更长区间。")
        else:
            st.caption(
                f"共 {m['交易次数']} 笔 ｜ 胜率 {m['胜率'] * 100:.0f}% ｜ "
                f"盈亏比 {ui.num(m['盈亏比'])} ｜ 平均持有 {m['平均持有天数']:.0f} 天"
            )
            st.dataframe(_trade_table(res.trades), height=240, width="stretch")

    with st.container(border=True):
        st.subheader("参数敏感性")
        st.caption(
            "参数一换结果就大变——下面把当前参数前后各动一档，用同一份数据各跑一次。"
            "如果邻域里结论方向和幅度差很多，说明这个结果更可能是运气。"
        )
        if key != "ma_cross":
            st.info("邻域检验第一版只对双均线开放；其它规则会后续补上。")
        else:
            f0, s0 = int(params["fast"]), int(params["slow"])
            fasts = sorted({max(2, f0 - 5), f0, min(120, f0 + 5)})
            slows = sorted({max(3, s0 - 10), s0, min(250, s0 + 10)})
            rows = []
            for f in fasts:
                for s in slows:
                    if f >= s:
                        continue
                    r = run_strategy("ma_cross", close, {"fast": f, "slow": s}, fee)
                    rows.append({
                        "短均线": f,
                        "长均线": s,
                        "总收益": ui.pct(r.metrics["总收益"]),
                        "最大回撤": ui.pct(r.metrics["最大回撤"]),
                        "交易次数": r.metrics["交易次数"],
                        "": "← 当前" if (f == f0 and s == s0) else "",
                    })
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    c1, c2 = st.columns(2)
    metrics_csv = pd.DataFrame(
        [{"参数": f"{spec['label']} {params}", **{k: round(v, 6) if isinstance(v, float) else v for k, v in m.items()}}]
    )
    c1.download_button(
        "导出指标 CSV",
        metrics_csv.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{ctx.code}_{key}_metrics.csv",
        mime="text/csv",
        width="stretch",
    )
    trades_csv = _trade_table(res.trades)
    c2.download_button(
        "导出交易明细 CSV",
        trades_csv.to_csv(index=False).encode("utf-8-sig") if len(trades_csv) else b"",
        file_name=f"{ctx.code}_{key}_trades.csv",
        mime="text/csv",
        width="stretch",
        disabled=not len(trades_csv),
    )
