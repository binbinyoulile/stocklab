"""页签之间共享的数据上下文。"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class TabContext:
    code: str
    start: str
    end: str
    df: pd.DataFrame          # 个股/ETF 日线（index=日期，含 close/high/low/volume）
    bench: pd.DataFrame | None
    bench_label: str
    fee: float
    asset: str = "stock"      # stock / etf
    request_start: str = ""   # 用户请求的起始日（用于提示上市不足）

    @property
    def close(self) -> pd.Series:
        return self.df["close"]

    @property
    def has_bench(self) -> bool:
        return self.bench is not None and len(self.bench) > 0
