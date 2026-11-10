"""回测引擎：策略注册表 + 交易模拟 + 指标。

口径与之前的研究脚本一致：信号在 T 日收盘确认，T+1 日收盘成交。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

TRADING_DAYS = 252


# ---------------- 指标 ----------------

def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    delta = s.diff()
    up = delta.clip(lower=0).rolling(n).mean()
    down = (-delta.clip(upper=0)).rolling(n).mean()
    rs = up / down.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def bollinger(s: pd.Series, n: int = 20, k: float = 2.0):
    mid = s.rolling(n).mean()
    sd = s.rolling(n).std(ddof=0)
    return mid + k * sd, mid, mid - k * sd


# ---------------- 策略 ----------------

def _state_signals(entries: pd.Series, exits: pd.Series) -> pd.Series:
    """把「入场条件 / 出场条件」变成 0/1 持仓信号。"""
    sig = np.zeros(len(entries))
    holding = False
    e = entries.fillna(False).to_numpy()
    x = exits.fillna(False).to_numpy()
    for i in range(len(sig)):
        if not holding and e[i]:
            holding = True
        elif holding and x[i]:
            holding = False
        sig[i] = 1.0 if holding else 0.0
    return pd.Series(sig, index=entries.index)


def _ma_cross(close: pd.Series, fast: int, slow: int) -> pd.Series:
    f, s = sma(close, fast), sma(close, slow)
    return _state_signals(f > s, f <= s)


def _rsi_reversion(close: pd.Series, window: int, buy: float, sell: float) -> pd.Series:
    r = rsi(close, window)
    cross_up = (r > buy) & (r.shift(1) <= buy)
    cross_down = (r < sell) & (r.shift(1) >= sell)
    return _state_signals(cross_up, cross_down)


def _bollinger_breakout(close: pd.Series, window: int, k: float) -> pd.Series:
    upper, mid, _ = bollinger(close, window, k)
    return _state_signals(close > upper, close < mid)


STRATEGIES: dict[str, dict] = {
    "ma_cross": {
        "label": "双均线交叉",
        "desc": "短均线上穿长均线买入，下穿卖出",
        "fn": _ma_cross,
        "params": [
            {"key": "fast", "label": "短均线", "min": 2, "max": 120, "default": 10, "step": 1},
            {"key": "slow", "label": "长均线", "min": 3, "max": 250, "default": 30, "step": 1},
        ],
    },
    "rsi": {
        "label": "RSI 超卖买入",
        "desc": "RSI 上穿买入阈值时买入，下穿卖出阈值时卖出",
        "fn": _rsi_reversion,
        "params": [
            {"key": "window", "label": "RSI 窗口", "min": 2, "max": 60, "default": 14, "step": 1},
            {"key": "buy", "label": "买入阈值", "min": 5, "max": 50, "default": 30, "step": 1},
            {"key": "sell", "label": "卖出阈值", "min": 50, "max": 95, "default": 70, "step": 1},
        ],
    },
    "boll": {
        "label": "布林带上轨突破",
        "desc": "收盘上穿上轨买入，跌破中轨卖出",
        "fn": _bollinger_breakout,
        "params": [
            {"key": "window", "label": "窗口", "min": 5, "max": 120, "default": 20, "step": 1},
            {"key": "k", "label": "标准差倍数", "min": 1.0, "max": 3.0, "default": 2.0, "step": 0.1},
        ],
    },
}


# ---------------- 模拟 ----------------

@dataclass
class Result:
    equity: pd.Series
    position: pd.Series
    trades: pd.DataFrame
    metrics: dict = field(default_factory=dict)
    label: str = ""


def drawdown(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def summarize(equity: pd.Series, daily: pd.Series, trades: pd.DataFrame, position: pd.Series) -> dict:
    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1 / 365.25)
    total = float(equity.iloc[-1] - 1)
    cagr = float(equity.iloc[-1] ** (1 / years) - 1) if equity.iloc[-1] > 0 else -1.0
    dd = float(drawdown(equity).min())
    vol = float(daily.std() * np.sqrt(TRADING_DAYS)) if daily.std() else 0.0
    sharpe = float(daily.mean() / daily.std() * np.sqrt(TRADING_DAYS)) if daily.std() else 0.0

    if len(trades):
        wins = trades.loc[trades["return"] > 0, "return"]
        losses = trades.loc[trades["return"] <= 0, "return"]
        win_rate = float(len(wins) / len(trades))
        profit_factor = float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("inf")
        avg_hold = float(trades["days"].mean())
    else:
        win_rate, profit_factor, avg_hold = 0.0, 0.0, 0.0

    return {
        "总收益": total,
        "年化": cagr,
        "最大回撤": dd,
        "夏普": sharpe,
        "年化波动": vol,
        "交易次数": int(len(trades)),
        "胜率": win_rate,
        "盈亏比": profit_factor,
        "平均持有天数": avg_hold,
        "持仓时间占比": float(position.mean()) if len(position) else 0.0,
    }


def run_strategy(
    key: str, close: pd.Series, params: dict, fee: float = 0.0008
) -> Result:
    if key not in STRATEGIES:
        raise ValueError(f"未知策略 {key}")
    spec = STRATEGIES[key]
    signal = spec["fn"](close, **params).fillna(0.0)

    # 信号 T 日确认、T+1 收盘成交 ⇒ 第 i 天的仓位取决于 i-2 的信号
    position = signal.shift(2).fillna(0.0)
    ret = close.pct_change().fillna(0.0)
    gross = position * ret
    cost = fee * position.diff().abs()
    if len(cost):
        cost.iloc[0] = fee * abs(position.iloc[0])
    daily = (gross - cost).fillna(0.0)
    equity = (1 + daily).cumprod()

    trades = _extract_trades(close, position, fee)
    metrics = summarize(equity, daily, trades, position)
    return Result(equity=equity, position=position, trades=trades, metrics=metrics, label=spec["label"])


def _extract_trades(close: pd.Series, position: pd.Series, fee: float) -> pd.DataFrame:
    idx = position.index
    pos = position.to_numpy()
    rows = []
    entry_i = None
    for i in range(len(pos)):
        if pos[i] == 1 and entry_i is None:
            entry_i = i
        elif pos[i] == 0 and entry_i is not None:
            ei, xi = entry_i - 1, i - 1  # 成交在信号次日收盘
            if ei >= 0 and xi > ei:
                entry_px, exit_px = float(close.iloc[ei]), float(close.iloc[xi])
                rows.append({
                    "entry_date": idx[ei].date(),
                    "exit_date": idx[xi].date(),
                    "entry_price": round(entry_px, 2),
                    "exit_price": round(exit_px, 2),
                    "days": xi - ei,
                    "return": exit_px / entry_px - 1 - 2 * fee,
                    "open": False,
                })
            entry_i = None
    if entry_i is not None and entry_i >= 1:
        ei = entry_i - 1
        entry_px, exit_px = float(close.iloc[ei]), float(close.iloc[-1])
        rows.append({
            "entry_date": idx[ei].date(),
            "exit_date": idx[-1].date(),
            "entry_price": round(entry_px, 2),
            "exit_price": round(exit_px, 2),
            "days": len(close) - 1 - ei,
            "return": exit_px / entry_px - 1 - fee,
            "open": True,
        })
    return pd.DataFrame(rows)


def run_buy_hold(close: pd.Series) -> Result:
    equity = close / close.iloc[0]
    daily = close.pct_change().fillna(0.0)
    metrics = summarize(equity, daily, pd.DataFrame(), pd.Series(1.0, index=close.index))
    return Result(equity=equity, position=pd.Series(1.0, index=close.index), trades=pd.DataFrame(), metrics=metrics, label="买入持有")
