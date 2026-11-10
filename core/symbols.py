"""代码规范化：把各种写法统一成 sh600519 这种带市场前缀的形式，并识别资产类型。"""
from __future__ import annotations

import re
from dataclasses import dataclass

SH_PREFIXES = ("600", "601", "603", "605", "688", "510", "512", "513", "515", "516", "588")
SZ_PREFIXES = ("000", "001", "002", "003", "300", "301", "159")
BJ_PREFIXES = ("920",)
ETF_PREFIXES = ("159", "510", "512", "513", "515", "516", "588")

_MARKETS = ("SH", "SZ", "BJ")
_PATTERNS = (
    re.compile(r"^(SH|SZ|BJ)\.?(\d{6})$"),      # sh600519 / SH.600519
    re.compile(r"^(\d{6})\.(SH|SZ|BJ)$"),        # 600519.SH
    re.compile(r"^(\d{6})$"),                    # 600519
)


@dataclass(frozen=True)
class Symbol:
    code: str        # sh600519
    market: str      # sh / sz / bj
    digits: str      # 600519
    asset: str       # stock / etf

    @property
    def is_etf(self) -> bool:
        return self.asset == "etf"

    @property
    def label(self) -> str:
        return f"{self.code}（{'ETF' if self.is_etf else '个股'}）"


def _guess_market(digits: str) -> str | None:
    if digits.startswith(SH_PREFIXES):
        return "sh"
    if digits.startswith(SZ_PREFIXES):
        return "sz"
    if digits.startswith(BJ_PREFIXES) or digits[0] in ("8", "4"):
        return "bj"
    return None


def _guess_asset(market: str, digits: str) -> str:
    if digits.startswith(ETF_PREFIXES):
        return "etf"
    if market == "sh" and digits.startswith("5"):   # 51x/56x/58x 沪市基金
        return "etf"
    if market == "sz" and digits.startswith(("15", "16")):  # 深市 ETF / LOF
        return "etf"
    return "stock"


def parse(text: str) -> Symbol:
    raw = (text or "").strip().replace(" ", "").upper()
    if not raw:
        raise ValueError("请输入代码，例如 600519、sh600519 或 510300。")

    explicit = None
    digits = None
    for i, pat in enumerate(_PATTERNS):
        m = pat.match(raw)
        if not m:
            continue
        if i == 0:
            explicit, digits = m.group(1).lower(), m.group(2)
        elif i == 1:
            digits, explicit = m.group(1), m.group(2).lower()
        else:
            digits = m.group(1)
        break

    if digits is None:
        raise ValueError(f"看不懂的代码：{text}。支持 600519 / sh600519 / 600519.SH。")

    market = explicit or _guess_market(digits)
    if market is None:
        raise ValueError(f"{digits} 看不出属于哪个市场，请写成 sh600519 这种带前缀的形式。")

    return Symbol(code=f"{market}{digits}", market=market, digits=digits,
                  asset=_guess_asset(market, digits))
