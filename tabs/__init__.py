"""页签注册表。加一个新页签 = 新建模块 + 在这里加一行。"""
from __future__ import annotations

from typing import Callable, NamedTuple

from . import backtest, diagnose
from .context import TabContext


class Tab(NamedTuple):
    label: str
    render: Callable[[TabContext], None]


TABS: list[Tab] = [
    Tab("体检", diagnose.render),
    Tab("回测", backtest.render),
]
