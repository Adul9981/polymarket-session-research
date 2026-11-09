# 基础资料库

存放交易者拆解的原始数据与账号资料。**只增不改**：原始 JSON 落盘后不覆盖，
补充数据另存新文件；分析结论不要写进原始数据，写进 cases/ 或知识库。

## 目录

```text
data/
  e46m3/
    profile.json           # 账号档案：用户名、地址、关联地址、合约地址
    conversions.json       # 近 5,000 条 CONVERSION（2026-08-01 ~ 08-12）
    merges.json            # 近 3,000 条 MERGE
    jeddah_activity.json   # 吉达 8/12 温度组活动（TRADE/CONVERT/MERGE）
    jeddah_trades.json     # 吉达组全部成交
    jeddah_prices.json     # 吉达组 11 档 1 分钟价格
    chain_decode.json      # 5 笔转换交易的链上解码结果
    positions.json         # 当前持仓（500 条）
    stats.json             # 汇总统计（类别/金额/时段）
```

## 数据来源与快照时间

```text
来源：Polymarket Data API / Gamma API / CLOB / Polygon RPC（publicnode）
快照时间：2026-08-12（北京时间）
口径：conversions/merges 为最近窗口分页拉取；价格粒度 1 分钟
```

## 新增数据约定

```text
文件名：<目标>_<内容>_<日期>.json（如 e46m3_trades_2026-08-12.json）
落盘前先查重：同内容已有文件则不重复保存
金额字段保留原始 1e6 整数或标注小数位，避免精度损失
```
