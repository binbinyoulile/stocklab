"""验收：代码规范化 + 个股/ETF 路由取数。"""
from datetime import date

from core.data import fetch_daily
from core.symbols import parse

print("== 规范化（不取数） ==")
for raw in ["600519", "sh600519", "600519.SH", "000001", "159530", "510300", "sz159530", "300750", "688981", "920001"]:
    try:
        s = parse(raw)
        print(f"{raw:12s} → {s.code:10s} {s.asset}")
    except ValueError as exc:
        print(f"{raw:12s} → 拒绝：{exc}")

print("\n== 取数（2026-06-01 ~ 2026-11-08） ==")
for raw in ["159530", "510300", "600519", "000001"]:
    s = parse(raw)
    df = fetch_daily(raw, date(2026, 6, 1), date(2026, 11, 8))
    print(
        f"{raw:8s} → {s.code:9s} {s.asset:5s} rows={len(df):3d} "
        f"{df.index[0].date()} ~ {df.index[-1].date()} close={df.close.iloc[-1]:.3f}"
    )
