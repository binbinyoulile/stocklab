"""数据层：ashareapi 免费档日线，分片 + 限速 + 本地缓存。"""
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd
import requests

from .config import CACHE_DIR, CACHE_TTL_SEC, CALL_GAP_SEC, MAX_RANGE_DAYS
from .symbols import parse

API = "https://api.ashareapi.com/v1/kline"
_last_call = 0.0


class DataError(RuntimeError):
    """给用户看的错误，不是 traceback。"""


def normalize_code(raw: str) -> str:
    """把 600519 / sh600519 / 600519.SH 统一成 sh600519。"""
    try:
        return parse(raw).code
    except ValueError as exc:
        raise DataError(str(exc)) from exc


def _chunks(start: date, end: date) -> Iterable[tuple[date, date]]:
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=MAX_RANGE_DAYS), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def _cache_path(code: str, s: date, e: date) -> Path:
    return CACHE_DIR / f"{code}_{s:%Y%m%d}_{e:%Y%m%d}.json"


def _read_cache(path: Path, force: bool) -> list[dict] | None:
    if force or not path.exists():
        return None
    if time.time() - path.stat().st_mtime > CACHE_TTL_SEC:
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _throttle() -> None:
    global _last_call
    wait = CALL_GAP_SEC - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.time()


def _fetch_chunk(code: str, s: date, e: date) -> list[dict]:
    params = {
        "code": code,
        "period": "day",
        "start": s.isoformat(),
        "end": e.isoformat(),
        "count": 250,
    }
    for attempt in range(3):
        _throttle()
        try:
            r = requests.get(API, params=params, timeout=30)
        except requests.RequestException as exc:
            raise DataError(f"网络请求失败：{exc}") from exc
        if r.status_code == 429:
            if attempt == 2:
                raise DataError("触发免费档限流（5 次/分钟），请等一分钟再试。")
            time.sleep(65)
            continue
        if r.status_code != 200:
            raise DataError(f"数据源返回 HTTP {r.status_code}。")
        payload = r.json()
        return payload.get("data") or []
    return []


def fetch_daily(
    code: str,
    start: date,
    end: date,
    *,
    force: bool = False,
    progress: Callable[[int, int, str], None] | None = None,
) -> pd.DataFrame:
    """取日线（前复权），自动分片、限速、缓存。返回按日期升序的 DataFrame。"""
    if end <= start:
        raise DataError("结束日期必须晚于开始日期。")
    code = normalize_code(code)
    windows = list(_chunks(start, end))
    rows: dict[str, dict] = {}
    for i, (cs, ce) in enumerate(windows, 1):
        if progress:
            progress(i, len(windows), f"{cs:%Y-%m-%d} ~ {ce:%Y-%m-%d}")
        path = _cache_path(code, cs, ce)
        cached = _read_cache(path, force)
        if cached is None:
            cached = _fetch_chunk(code, cs, ce)
            if cached:
                try:  # 云端文件系统可能是只读的，缓存失败不影响取数
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(cached, ensure_ascii=False), encoding="utf-8")
                except OSError:
                    pass
        for row in cached:
            rows[row["date"]] = row

    if not rows:
        raise DataError(
            f"没取到 {code} 的数据。可能原因：代码不存在、该区间停牌，或超出数据源覆盖范围。"
        )

    df = pd.DataFrame(sorted(rows.values(), key=lambda r: r["date"]))
    df["date"] = pd.to_datetime(df["date"])
    for col in ("open", "high", "low", "last", "volume", "amount"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.rename(columns={"last": "close"}).set_index("date").sort_index()
    df = df[~df.index.duplicated(keep="last")]

    bad = df[df["close"] <= 0]
    if len(bad) > 0:
        raise DataError(
            f"该区间有 {len(bad)} 根前复权价格为负（最早 {bad.index[0]:%Y-%m-%d}），"
            "负价格算不了收益率。请把开始日期调到 2021-11-01 之后。"
        )
    if len(df) < 30:
        raise DataError(f"只有 {len(df)} 根日线，样本太短，至少要 30 根。")
    return df


def last_updated(code: str) -> datetime | None:
    files = sorted(CACHE_DIR.glob(f"{normalize_code(code)}_*.json"), key=lambda p: p.stat().st_mtime)
    return datetime.fromtimestamp(files[-1].stat().st_mtime) if files else None


def clear_cache() -> int:
    n = 0
    for p in CACHE_DIR.glob("*.json"):
        p.unlink()
        n += 1
    return n
