"""全局常量：数据限制、路径、默认值。"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = APP_DIR / ".cache" / "quotes"

# 服务器（Streamlit Cloud）跑 UTC，这里固定用北京时间，避免晚上差一天
CN_TZ = timezone(timedelta(hours=8))


def today_cn():
    return datetime.now(CN_TZ).date()

# ashareapi 免费档约束（2026-11-08 实测）
MAX_ROWS = 250          # 匿名单次上限；超过会静默截断为最近 250 根
CALL_GAP_SEC = 12.0     # 5 次/分钟
MAX_RANGE_DAYS = 330    # 每个分片约 250 个交易日

DATA_START = "2021-11-01"   # 前复权价格转正起点
DEFAULT_FEE = 0.0008        # 往返 0.08%（买卖各 0.04%）
CACHE_TTL_SEC = 6 * 3600

BENCHMARKS = {
    "沪深300": "sh000300",
    "上证指数": "sh000001",
}

BANNER = (
    "支持 A 股个股与 ETF · 日线 · 前复权 · 免费数据源（单次 250 根、5 次/分钟）  \n"
    "前复权为减法口径，2021-11 之前价格为负，不可用于回测  \n"
    "结果仅供研究，不构成投资建议"
)
