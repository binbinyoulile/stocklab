# StockLab · A 股研究台

个人用的研究界面：**体检**（趋势/回撤/波动/相对基准）+ **回测**（规则 → 指标 → 参数邻域 → 导出）。

## 启动

```powershell
cd D:\桌面\DSproject\量化\stocklab
python -m streamlit run app.py
```

浏览器打开 http://localhost:8501 。

## 支持的代码

输入 6 位数字即可，前缀自动补；也接受 `sh600519`、`600519.SH`。

| 前缀 | 市场 |
|---|---|
| 600 / 601 / 603 / 605 / 688、510 / 512 / 513 / 515 / 516 / 588 | 上海 |
| 000 / 001 / 002 / 003 / 300 / 301、159 | 深圳 |
| 920、8 开头、4 开头 | 北京 |

159 / 51x / 56x / 58x 自动识别为 ETF，其余按个股处理；ETF 走同一个 K 线接口（免费档已覆盖，无需 AkShare）。

## 硬限制（写在页面顶部，别忽略）

- A 股个股与 ETF、日线、前复权
- 免费数据源：单次最多 **250 根**、**5 次/分钟**，超过 250 根会**静默截断成最近 250 根**
- 前复权是减法口径，2021-11 之前价格为负，回测不可用
- 回测口径：信号 T 日收盘确认、**T+1 收盘成交**；只计手续费，**未计滑点与涨跌停**

## 目录结构

```
app.py                 入口：顶部输入条 + 页签
core/config.py         常量（限制、路径、默认费率）
core/data.py           ashareapi 取数：分片、限速、缓存（.cache/quotes）
core/engine.py         策略注册表 + 交易模拟 + 指标
core/ui.py             格式化与图表小工具
tabs/__init__.py       页签注册表 TABS
tabs/context.py        页签之间共享的 TabContext
tabs/diagnose.py       页签 A：体检
tabs/backtest.py       页签 B：回测
```

## 加一个新页签（选股 / 提醒）

1. 新建 `tabs/screen.py`，写 `def render(ctx: TabContext) -> None: ...`
2. 在 `tabs/__init__.py` 的 `TABS` 里加一行 `Tab("选股", screen.render)`

页签只依赖 `TabContext`（代码、区间、日线、基准、费率），不用改 `app.py`。

## 加一个新策略

在 `core/engine.py` 的 `STRATEGIES` 里注册：`label / desc / fn / params`，
`fn(close, **params)` 返回 0/1 持仓信号序列即可，UI 会自动生成参数控件。

## 自检

```powershell
python smoke.py     # 数据层 + 引擎
python test_app.py  # Streamlit 全脚本渲染（AppTest）
```

## 免责

仅供研究，不构成投资建议。
