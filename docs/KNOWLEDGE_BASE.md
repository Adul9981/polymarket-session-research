# 基础知识库：交易者拆解

最后更新：2026-08-20

本库保存拆解交易者所需的全部基础：概念、数学规则、账号档案、数据源、链上解码方法与关键发现。
内容随拆解持续补充；新增条目先查这里有没有归属。

## 0. 通俗版：这套玩法到底在做什么（先读这个）

### 打个比方：11 个盒子，只有一个是真的

"明天吉达最高温几度"拆成 11 个盒子（31°C 以下、32、33……41°C 以上），只有一个盒子是真的。
每个盒子有两种票：

```text
YES 票：猜"就是这个温度"。猜对一张变 $1，猜错变 $0。
NO 票：猜"不是这个温度"。不是它一张变 $1，是它变 $0。
票价 = 市场觉得的可能性。
```

### 三条"规则白纸黑字"（平台规定，不是猜的）

```text
规则 1：11 张 YES 全买齐 = 一定拿 $1（不管哪个盒子赢，只有一张中奖）
规则 2：NO(35) 和"其余 10 个 YES"是同一件事的两种写法 -> Convert 免费互换
规则 3：同一个盒子的 YES+NO 一对 = $1（任何时候 Merge）
```

### 漏洞在哪：市场把价格标错了

规则 1 说整套 YES 只值 $1，市场却把 11 张 YES 标成 $1.06 -> YES 贵了，NO 便宜了
（NO = 1 − YES，YES 多 0.06，NO 整体就少 0.06）。

### 他的 4 步（对应"买 NO -> 转 YES -> 合并 -> 赚差价"）

```text
第 1 步 买便宜的 NO：整套 NO 按规则必拿 $10，市场只卖 $9.94，他专挑 NO 买
第 2 步 Convert：把 NO 交给机器，换成"现金 + 其他盒子的 YES"（公平交换，不赚不亏）
第 3 步 Merge：新到手的 YES 和仓库里以前囤的 NO 配对，一对变 $1
第 4 步 利润：每轮 ≈ 份额 × (Σp − 1)，吉达组约 5~6% 的份额；
          机器只在整个组合明显标错价时才出手，一天跑几百轮
```

### 一句话

```text
Convert 是公平的"变形术"；真正的钱来自市场价格错误：
整套 YES 标成 $1.06 却只值 $1，他就去买被标便宜的 NO，
再让 Convert 把规则保证的钱提前变成现金。
```

图形化讲解（三案例：天气/足球/棒球，含链上账目图与 Σp 图）：
reports/convert_mechanism_explainer_2026-08-12.html

## 1. 核心概念

### 负风险多选项市场（neg-risk group）

一组互斥且穷尽的结果（如 11 个温度档、20+ 个足球比分、30 支冠军候选、60 支世界杯球队），
每个结果是一个二选一市场（"温度是否=36°C" / "某队是否夺冠"），共享一个负风险组 ID
（negRiskMarketID）。数学约束：恰好一个结果发生。

### 四类 token 操作（链上原语）

| 操作 | 含义 | 等价关系 |
| --- | --- | --- |
| SPLIT | 1 USDC 拆成全套 YES（每个结果各 1 份） | 全套 YES = $1 |
| MERGE | YES+NO 一对合并 | YES+NO = $1（任何时候） |
| REDEEM | 结算后赢的方向 1:1 赎回 | 赢家 YES = $1 |
| CONVERSION | 组合等价置换 | NO(i) ≡ 除 i 外全部 YES |

### 完整集定价 Σp

同一时刻把所有结果的 YES 价格相加，记为 Σp。理论上恒等于 $1：

```text
Σp > 1  -> 全套 NO 被低估（买 NO 组合 -> Convert 兑现）
Σp < 1  -> 全套 YES 被低估（买 YES 完整集 -> 持有/Merge 兑现）
Σp = 1  -> 无结构套利空间
```

长尾市场（比分、温度、冷门未来盘）流动性薄、价格更新慢，Σp 长期偏离 $1，这是机器套利的主战场。

## 2. 数学规则（已用链上账目验证）

### Convert 的赔付等价

把结果集合 S 的 NO 组合（n 个腿，每腿 X 份）转换为补集 S^c 的 YES（m 个腿，每腿 X 份）+ 现金 C：

```text
C = (n - 1) × X
任意结果下：转换前 = 转换后
```

验证案例（吉达 8/12，n=7，m=4，X=3.913335，C=23.48）：

```text
温度落在 31-34°C：转换前 7X=27.39 = 转换后 1X + 6X = 27.39 ✓
温度落在 35°C 以上：转换前 6X=23.48 = 转换后 0 + 6X = 23.48 ✓
```

结论：Convert 函数本身公平，不是漏洞；利润来自市场定价不一致（Σp≠1）与返佣叠加。

### Convert 的单轮毛利

```text
毛利 ≈ X × (Σp − 1)（Σp>1 方向，未计摩擦）
吉达组实测：Σp = 1.0475~1.0640 -> 单轮毛利约 X 的 4.7%~6.4%
```

## 3. 目标账号档案

原始 JSON：data/e46m3/profile.json；原始数据：data/e46m3/*.json。

| 项 | 值 |
| --- | --- |
| 用户名 | e46m3 |
| 昵称 | Grown-Fence |
| 主页 | https://polymarket.com/zh/@e46m3 |
| 代理钱包 | 0x4f1d5ae26fc31472966e951af3183308736d8de2 |
| 交易过市场数 | 29,174 |
| 角色判断 | 自动化完整集套利 + 做市返佣机器人（推断） |

### 关注账号：fkigedgjdgwbg（2026-08-15 加入）

原始数据：data/fkigedgjdgwbg/*.json（README 见该目录）。

### 关注账号：PEYZ-BIGGEST-FAN（2026-08-26 加入，电竞 LoL 深水系统型）

原始数据：data/mapread-kt-bro-2026-08-26/（mapread 接口抓取，见 README）。

| 项 | 值 |
| --- | --- |
| 用户名 | PEYZ-BIGGEST-FAN |
| 代理钱包 | 0xdaef2be2a19ad331737d06545f85615b094554e9 |
| mapread 入池 | 2026-08-09（LoL 段，180 天滚动考核） |
| 180 天画像 | 现金流 PnL $101,947 / ROI 8.2% / 胜率 56.2% / 285 仓 / 单仓中位 $3,114 |
| 我方标签 | A_深水机器; B_全剧本; F_活跃双向; H_暗窗大额（GX vs VIT 拆解建立） |

特征要点：

```text
1. GX vs VIT G2（2026-08-14）：暗窗 $1,273、估盈 $6,253；全剧本（G1 VIT / G2 GX / 整场 VIT）。
2. 跨场赢家 Top15（2026-08-16）：T1G+DRXB 两场合计 pnl $53,555。
3. KT vs BRO G4（2026-08-26）：52 笔 $17,120，0.66→0.50 下跌途中摊成本，KT 胜结算 99.95c，
   估算 +$12,692；全系列打平（G1/G3 亏损）——行为画像跨场延续，单场非全知。
4. 与我方名单交集：zb8、MissingJoy 同池，G4 同向买 KT（分别 $13,400 / $6,417）。
```

| 项 | 值 |
| --- | --- |
| 用户名 | fkigedgjdgwbg |
| 昵称 | Misty-Request |
| 主页 | https://polymarket.com/zh/@fkigedgjdgwbg |
| 代理钱包 | 0x52ecea7b3159f09db589e4f4ee64872fd0bba6f3 |
| 主地址（EOA） | 0x9c0f2b174ae2c88f73d75f79c3a0542b276e8d42 |
| 注册时间 | 2025-07-16 |
| 累计交易 | 3,139 笔；单笔最大赢利 $81,676 |
| 角色判断 | 电竞（LoL）重仓"信息差"玩家：历史 8 个最大赢利全部是 LoL 中低赔率押注 |

特征要点：

```text
1. 8/14 EDG vs LGD：LGD 盘口 20 分钟 0.57->0.99，随后该地址 $277,608 追买
   （0.95~0.999），同形态（价格打到位后跟买）全天重复 5 场，合计 $532K。
2. 历史最大赢利含 0.02 买 Karmine Corp 赢 $73,614、0.39 买 Nongshim Red Force
   赢 $137,920 等，符合"赛前知道结果"画像（待用户确认具体假赛场次）。
3. 持仓全部已归零（赢家早兑换、输家从不平仓），与 e46m3 的托管形态完全不同：
   这是个人激进账户，不是做市/套利机器人。
4. 拉盘源初步排查（Game1 07:00-07:50 UTC）：买单 96 万份 vs 卖单 16 万份；
   主力是 0xe16e8a3c...（$138.5K，单笔 $111K）等大额钱包，本文地址 07:44
   起才跟进（窗口内 $30.7K），不是发起者；详见 data/fkigedgjdgwbg/README.md。
```

### 对照样本：cf609d（2026-08-15 加入，反面教材）

原始数据：data/cf609d/*.json（README 见该目录）。

| 项 | 值 |
| --- | --- |
| 用户名 | 0xcf609d...-1771809916847（自动生成名） |
| 代理钱包 | 0xcf609d3256f0f37f0595e5dc64012fa3a8fea6f5 |
| 注册时间 | 2026-02-22 |
| 累计成交 | 39,984 笔；净盈亏约 **-$497,372** |
| 画像 | 高换手"只买不卖"玩家：BUY $21.1M vs SELL $2.3M（9:1），买价集中 0.4~0.75，从不止损 |

为什么亏（对照价值）：输家持仓一路持有到归零（737 条几乎全 0），大额输家
Valorant FUT -$133.9K、加拿大 -$90.5K 等压过赢家（最大 +$216K）。
对比 e46m3（做市返佣+套利）与 fkigedgjdgwbg（信息差跟买），这是一个
"持续向市场输血"的典型失败画像，用于反证：**只看买入多≠有钱赚**。

关联地址（证据：链上解码/持仓接口）：

```text
转换对手方/金库地址  0xa5ef39c3d3e10d0b270233af41cac69796b12966
Safe 交易签署方（观察）0xf105cd06... / 0x68d46014... / 0x256b1b01... / 0xbefc8a81... / 0x72b263c4...
```

关键合约（Polygon）：

```text
NegRiskAdapter        0xada2005600dec949baf300f4c6120000bdb6eaab
NegRisk 辅助/交易所   0xd91e80cf2e7be2e162c6513ced06f1dd0da35296
CTF Exchange V2（官方撮合+托管）0xe111180000d2663c0091e4f400237545b87b996b
条件代币 CTF          0x4d97dcd97ec945f40cf65f87097ace5ea0476045
USDC.e                0x2791bca1f2de4661ed88a30c99a7a9449aa84174
pUSD（Polymarket 内部）0xc011a7e12a19f7b1f670d46f03b03f3342e82dfb
负风险抵押 token      0x3a3bd7bb9528e159577f7c2e685cc81a765002e2
```

注意：CTF Exchange V2（0xe111...96b）是官方合约不是交易者。其 profile 页
显示的是所有用户仓位的托管汇总：持仓均价几乎全部 0.5（完整集托管形态）、
traded=0、盈亏≈0、市值 $59K 是托管余额；链上分析看到该地址的资金流动
需按 proxy wallet 拆回具体用户（对应 e46m3 的代理钱包 0x4f1d...8de2）。

### 关注账号：djdjdjekekek（2026-08-20 加入，账户级崩盘案例）

原始数据：data/djdjdjekekek/*.json（README 见该目录）。

| 项 | 值 |
| --- | --- |
| 用户名 | djdjdjekekek |
| 昵称 | Webbed-Myth |
| 主页 | https://polymarket.com/zh/@djdjdjekekek |
| 代理钱包 | 0x6d20c35f65d9899b6d6b74f8466e824580f9a165 |
| 活跃期 | 2026-06-19 ~ 08-15（50 个交易日） |
| 成交 | 23,118 笔（买 22,518 / 卖 600），294 个事件 |
| 峰值累计盈利 | +$2,365,161（2026-08-12 05:18 UTC） |
| 期末净盈亏 | -$724,630（2026-08-20 快照，含费口径） |
| 角色判断 | 高波动个人重仓玩家（推断）：大赛热门共识盘 + 部分深水翻盘；只买不卖、无止损、赛项漂移 |

特征要点（接口数据，2026-08-20 全量拆解）：

```text
1. 盈利期 alpha 集中在高价格共识盘：世界杯晋级 +$842K、MLB 红袜两日 +$1.06M、
   Dota2 1win 季后赛两场 +$1.5M、JDG +$79K；退出统一为"赢定后 ~1.0 卖出/赎回"。
2. 风险结构全程未变：卖出仅占 2.6%（600/23,118），亏损仓位从不止损；
   单笔买入中位 $22、关键场次单笔 $20-40 万。
3. 崩盘（8/12-8/15）：四天 -$2,615,469；24 个仓位（CS2 EWC BO1/Dota2 TI/MLB）
   初始 $3.52M 全部归零；8/12 单日 -$1.44M 后 8/13 仍买入 $1.44M（追损）。
4. 类别账：CS2 -$1.87M 是最大失血项；LoL/MLB/网球/其他全部为正。
5. 与 e46m3（套利机器）零重叠：无 CONVERSION/SPLIT/MERGE；
   与 cf609d（只买不卖无 edge）同构，差异仅在是否有 alpha。
6. 社区流传"启动资金约 7 万美元"：待链上 USDC 流入验证（未证实）。
7. 策略统计（2026-08-20 深拆，事件加权口径）：
   - 盈利引擎 = 0.2-0.4 强队价值买入：85 事件/27 胜，ROI +12.9%（+$968K）；
     ≥0.8 高共识 89% 胜率但 ROI -7.9%（假确定性）；0.6-0.8 类热门 -11.2%；
     <0.2 深水 -83.6%（9 输 8）。
   - 赛项分域：同一 0.2-0.4 模式 MLB/网球/其他为正、CS2/Dota2 为负；
     CS2 全周期 -$1.87M（ROI -45%）、BO1 单场 -$1.71M。
   - 盈利集中度：TOP10 事件占盈利 43.8%，TOP30 占 78.1% -> 少数重仓场次驱动。
   - 退出：有退出资产持仓时长中位 1.3h；227 个资产无退出（归零）；从不主动止损。
   - 对应策略登记：STRATEGY_LIBRARY.md S-F5（L0 观察）。
```

### 关注账号：0x82882d761b0d7f18b2cc286117d10cd8a15a5519（2026-09-07 加入，马斯克市场专项跟踪）

原始数据：data/0x82882d761b0d7f18b2cc286117d10cd8a15a5519/
（README + 链上自检原始 JSON，只增不改）。

| 项 | 值 |
| --- | --- |
| 地址 | 0x82882d761b0d7f18b2cc286117d10cd8a15a5519 |
| 类型 | 合约地址（Polymarket 代理钱包形态，链上 eth_getCode 实测） |
| 专注领域 | Polymarket 马斯克相关市场（用户口述） |
| 用户观察 | 收益区间平滑，推断系统化纪律打法（软证据，待成交数据验证） |
| 链上快照 | pUSD $5,650.65 / USDC.e $0（2026-09-07，eth_call 实测） |
| data-api | 2026-09-07 当前网络到 data-api/gamma 连接超时，首份成交快照待补 |
| 跟踪类型 | 长期跟踪（首快照 -> 每周增量 -> 每月账户级复盘） |

工具：tools/account_snapshot.py（2026-09-07 新增：positions/activity/trades
快照 + Polygon 链上自检，按地址落盘 data/<address>/）。

```text
待办：
1. data-api（或 V2 等价接口）可达后补拉全量成交/活动/持仓，做首份画像；
2. 验证"马斯克市场专项 + 平滑收益"是否成立（接口数据，勿以口述下结论）；
3. 纳入每周盯梢名单（与 esports 名单分开：mapread 池不覆盖马斯克市场）。
```

## 4. 数据源与取数规则

### 接口

#### mapread.gg（2026-08-26 登记，电竞 smart money 实时看板）

```text
定位：按游戏段维护"180 天已结算市场表现"筛选的顶级钱包池（LoL 93 / CS2 92 /
  Dota2 58 / Valorant 31），实时展示这些钱包最近 4H 在各市场的买卖（资金流）。
公开 JSON 接口（无鉴权，2026-08-26 验证可调）：
  GET /api/v1a/market-flow?segment_id={lol|cs2|dota2|valorant}&surface=board
      # 看板：市场信号、方向净流、钱包数、免费/锁定标记（带 ETag 增量）
  GET /api/v1a/market-flow/wallet-activity?condition_id={id}&segment_id={seg}
      # 市场钱包级逐笔：完整地址、side、金额、份额、价格、时间、tx hash、eligibility
  GET /api/v1a/market-flow/wallet-profiles?condition_id={id}&segment_id={seg}
      # 该市场钱包 180 天画像：现金流 PnL、ROI、胜率、仓位数、中位买入
底层数据源：Polymarket Goldsky subgraph（wallet_live_order_fills），与 forensics
  链上成交同源，可交叉验证。
边界：不显示用户名（身份需我方台账反查）；无钱包搜索/历史查询（仅 4H + 最近结束）；
  看板免费样例 1 条，其余行 Pro 锁定（接口返回 unlocked_free_samples /
  locked_current_like_rows 标记）。
工具封装（2026-08-27）：tools/mapread_wallet_tracker.py（board / market / watch，
  内置我方名单盯梢；原始 JSON 落盘 docs/forensics/data/mapread/，只增不改）。
交叉验证结论：我方 GX vs VIT / 跨场赢家名单中的 PEYZ-BIGGEST-FAN、zb8、MissingJoy
  均在 LoL 池中，行为画像跨场延续；单系列估算可打平/亏损（KT vs BRO 2026-08-26），
  说明"聪明钱"靠分散盈利，单场不可复制。
原始数据：docs/forensics/data/mapread-kt-bro-2026-08-26/
```

| 用途 | 接口 | 关键参数 |
| --- | --- | --- |
| 用户成交 | https://data-api.polymarket.com/trades | user + market/eventId；takerOnly=false 才含做市成交；start=1 拉全量；offset 上限 10000/窗 |
| 用户活动 | https://data-api.polymarket.com/activity | type=CONVERSION,SPLIT,MERGE,REDEEM,REWARD...；offset 上限 5000/窗；start/end 分窗 |
| 当前持仓 | https://data-api.polymarket.com/positions | user；含 redeemable/mergeable/negativeRisk |
| 市场结构 | https://gamma-api.polymarket.com/events | slug/事件；clobTokenIds/outcomes 是 JSON 字符串需解析 |
| 价格历史 | https://clob.polymarket.com/prices-history | market=token id；interval=1d&fidelity=1 得 1 分钟粒度 |
| 链上解码 | https://polygon-bor-rpc.publicnode.com | JSON-RPC；必须带浏览器 User-Agent |

### 已踩的坑

```text
1. gamma 的 clobTokenIds/outcomes 是 JSON 字符串，先 json.loads。
2. /trades 默认只给 taker 成交，必须 takerOnly=false。
3. /activity 默认窗口约 3 年，拉全量需 start=1 或 start/end 分窗 + offset。
4. 公共接口 SSL 抖动频繁，必须内置重试（3-6 次退避）。
5. publicnode RPC 拒绝 urllib 默认 UA，需伪装浏览器 UA。
6. 转换活动行的 conditionId 是负风险组 ID（negRiskMarketID），不是单个市场 conditionId。
7. 金额字段注意 6 位小数（usdcSize/size 原始值为 1e6 整数）。
8. 标记价 ≠ 可成交价：Σp 判断必须用订单簿 ask（按目标数量加权的真实成本），
   不能只用 prices-history / 标记价；Convert 兑付是平台固定公式，风险只在买入端；
   价差需覆盖手续费/燃气并留安全垫（如 ask 成本 < 兑付 − 2% 才出手）。
9. data-api 无 /profile、/user 接口（404）；账户画像用 /activity 推断：
   最早活动时间、频率、类型分布。/activity 分页 limit 上限 500/页、offset 上限 5000/窗。
10. /trades 的 offset+limit 有隐性上限（实测约 7000~11000 行不等），全量需按
    start/end 时间窗分片，不能只靠 offset 翻到底。
11. /prices-history：interval=1m 时 fidelity 最低为 10（即 10 分钟粒度）；
    要 1 分钟粒度用 interval=1d&fidelity=1 + startTs/endTs 限定窗口。
12. 电竞单局市场的 "closedTime/umaEndDate" 可能是结算确认时间而非赛点：
    以分钟级价格拉到 0/1 的时刻还原真实定局时间（GX vs VIT G2：18:23 定局 vs 22:26 收盘）。
```

### 涨跌盘（Up/Down）数据源与判定规则（2026-08-18 记录）

来源：用户提供的推文（@runes_leo，X 链接无法直接读取）→ 追到其开源仓库
runesleo/polymarket-toolkit（`pm updown` 命令 + docs/crypto-updown-price-source.md），
再交叉验证两篇技术文章（dev.to：reconstructing the price to beat；Chainlink TWAP 策略文）。

核心结论：

```text
1. 涨跌盘只由一个数字决定："参考价 / 要打败的价"（price to beat / strike /
   openPrice）。收盘参考价 > 开盘参考价 = Up 赢，反之 Down 赢。
2. Gamma API 没有稳定公开的 priceToBeat 字段，必须自己重建；来源随周期不同：
   - 5m / 15m / 4h：周期开盘时 Chainlink 推送的价（data stream）
   - 1h：Binance 1 小时 K 线 OPEN（开盘价）
   - 1d：Binance 1 分钟 K 线在开盘点的 CLOSE（必须等 close_time 到，不能提前读）
3. 边界对齐：5m/15m/1h 按 UTC 整点；4h 按美东时间（00/04/08/12/16/20，注意
   夏令时）；1d 从美东中午 12:00 开始，跨夏令时日是 23/25 小时而非 24 小时。
4. 重大规则变更（2026-08-07 起）：全部加密涨跌盘改为 Chainlink TWAP 结算：
   - 5m 用 30 秒 TWAP；15m / 4h 用 60 秒 TWAP
   - 旧的"盯最后一笔价 / 预言机滞后狙击"打法失效；新边际在
     "实时 TWAP 隐含概率 vs 订单簿定价偏差"
   - 8 月官方注入 $1M 做市奖励池（做市收益上升、逆选择下降）
5. 常见坑：数据源延迟（指数更新慢于信号源）、用错窗口（5m/15m slug 差一个桶）、
   把 CLOB 中间价当官方参考价（mid ≠ 结算预言机）、Gamma 缓存过期（开窗前要重拉）。
```

可复用的数据源/工具清单：

```text
- runesleo/polymarket-toolkit（GitHub）：pm updown <slug> 输出事件字段 +
  resolutionSource；另有 pm profile / cashflow / markout / mix / redeem / lb 等
  只读工具与 Claude/Cursor skills（MCP 10 个只读工具）。
- poly-strike-scraper（npm）：轻量解析 5m/15m/4h 涨跌盘的 exact strike（openPrice）。
- polymarket_price_to_beat（Python 包，dev.to bluewhale-quant-lab）：按周期
  重建参考价，含 DST 边界与 1m candle 未收盘保护。
- krish301/polymarket-raw-5m（HuggingFace）：连续采集全部 5m 涨跌盘逐笔成交
  + 订单簿快照，适合离线回测。
- 官方 RTDS WebSocket relay（2026-08-04 上线，免凭证）流式推 Chainlink TWAP，
  文档：docs.polymarket.com/market-data/chainlink-twap。
```

对本项目 BTC 5m 拆解的意义：我们抓到的"崩盘型"大赢家发生在 2026-08-17，
已处于 TWAP 结算时代，说明低价买 Down 的收益来自"实时 TWAP 已明显低于开盘价"
的信息差，而不是旧的单点价格狙击。后续验证应把窗口 openPrice、窗口内 TWAP
轨迹与成交时间对齐（见 data/btc5m-2026-08-17/README.md）。

## 5. 链上解码方法

1. 从 /activity 取 CONVERSION 行，拿 transactionHash。
2. RPC eth_getTransactionReceipt；交易 to = 用户 Safe 代理，selector 0x6a761202。
3. 关注 CTF（0x4d97...）的 ERC1155 TransferBatch（topic0 0x4a39dc06...）：

```text
data 布局（abi.encode(ids, values)）：
  word0 = ids 偏移（字节）-> 按 32 字节换算下标
  word1 = values 偏移
  ids[off] 起为长度 + id 列表；values 同理
```

4. token id -> 市场/方向：用 gamma 该事件的 clobTokenIds 反向映射（token0=Yes，token1=No，
   顺序对应 outcomePrices）。
5. 资金流：解码 ERC20 Transfer（topic0 0xddf252ad...），关注 USDC.e / pUSD / 负风险抵押 token。
6. 关键事件地址：

```text
NegRiskAdapter 事件（0xada2...）：0x1b8b64a5dd5755bb86（组 ID + 金额）
辅助合约事件（0xd91e...）：0xb03d19dddbc72a87e7
```

## 6. 关键发现记录（截至 2026-08-12）

```text
1. e46m3 近 12 天 5,000 次 CONVERSION，合计 $157,272，中位 $0.70 -> 24×7 自动化机器。
2. 每次吉达组 Convert 时点 Σp = 1.0475~1.0640（>1）-> 完整集套利方向确认。
3. 循环节奏：买 NO 组合 -> Convert（现金+补集 YES）-> Merge 配对 -> 再循环，单轮约 30 秒。
4. 返佣叠加：近 100 笔 MAKER/TAKER_REBATE+REWARD 合计 $2,546。
5. 市场偏好：天气温度档 39%、选举/政治 16%、体育未来盘（MLB 冠军 116 次）、
   足球比分盘 48 次（单笔最大 $1,500）；MLB 冠军盘多为尘埃级（中位 $0.02）。
6. 持仓形态：多组"每个选项各 X 份 YES、均价 0.5"= 完整集做市留下的库存。
7. 高优先级待验证：足球比分盘单场 Σp 序列（下一场 Villarreal C vs Levante UD）。
8. ✅ 足球比分盘已初步验证（Villarreal vs Levante 08-05）：12 次 Convert 时点
   Σp = 1.021~1.069（>1）；链上解码：4 个平局比分 NO（0-0/1-1/2-2/3-3）
   -> 13 个非平局比分 YES + $74.95；结算 1-0 后赎回 $112.18。
   完整数据：data/e46m3/e46m3_villarreal_exact_2026-08-12.json。
9. ✅ 棒球冠军盘初步验证（MLB 2026）：取数快照 Σp ≈ 1.032（>1）；
   链上解码：22 队 NO -> 9 队 YES + $522.19；但 116 次转换中位仅 $0.02，
   大部分是尘埃清理，可复制性低于天气/比分盘。
   完整数据：data/e46m3/e46m3_mlb_champion_2026-08-12.json。
10. ✅ 假赛嫌疑场地址分析（GX vs VIT G2，2026-08-14）：赢家侧 425 个买家，
    深水 ≤0.15 买入共 $8.5k/86k 份/145 人；大额买家全部是"系统性深水抄底机器"
    （近 10 天每天几十场买 ≤0.15 大劣势方），即"高手"成立；未发现一次性组织者账户。
    全剧本型（VIT G1 + GX G2 + VIT 整场）账户存在但均有其他深水记录；
    cf609d32 历史深水频率最低（9 笔），待链上溯源。盘后 0.999 流 $161k 与知情下注无关。
    报告：reports/g2_winner_address_analysis_2026-08-15.html；
    案例卡：cases/2026-08-15_lol-gx-vit-game2-address/README.md；
    原始数据：data/lol-gx-vit-2026-08-14/。
11. 深水抄底机器人簇（外部印证 S1 低价反转）：多个账户以"每天几十场、每场几百股、
    买 ≤0.15 大劣势方"为常态（fkigedgjdgwbg 537 次/$49k/35 事件；
    f201a19b 692 次/$42k/50 事件；Albedo00 4,138 次/$219k/235 事件）；
    另有尘埃机器人簇（E10/E11/E12ESpo*、asdf*/bbd/zxcursed 等随机名小号，
    单笔几美元、同时买双方、一天数千笔），金额可忽略。
12. ✅ "全剧本（有去有回）"检验方法论（GX vs VIT G2 追加轮）：同一 BO3 三腿
    （G1 赢家 + G2 赢家 + 整场赢家）全买中的账户数量并不异常——GX-VIT 22 个
    vs 同日对照组 AL-JDG 74 个；赛前三腿全买 2 个 vs 1 个（同一账户 antec；
    注：早期稿误算对照组开赛时间为 13:15 曾得 20 个，按 11:15 重算为 1 个，已修正）；
    独立基线富集 12x vs 19x。
    两场大量相同地址（antec / 0x9e3ed7b6 / suntori / Jimmyman132 / cryptolava），
    说明"全剧本"是电竞盘口玩家的常规打法。检验必须带同日对照组，
    且每腿要按"定局前买入"过滤（盘后 0.99 买不算知情）。
    对照组数据：data/control-al-jdg-2026-08-14/。
13. ✅ e46m3 近期重心迁移（2026-08-09~17 复盘）：9 天 5,211 笔买入 $76K、
    仅 4 笔卖出；113 次 Convert + 203 次 Merge。主战场从天气转向
    **选举/政治多选项组**（巴西总统、美国州长/初选、赞比亚、俄罗斯议会、
    拉脱维亚、台湾地方选举、Clacton），辅以天气（巴黎/香港/武汉/纽约）、
    "哪家公司/排名"组（最佳 AI 模型、最大公司、Spotify）、转会组
    （Enzo/Rodri/Alvarez）、电竞未来盘（Dota2 TI 2026、CS2 EWC）、
    足球比分盘（Brentford 2-0 Eintracht）、MLB、Fed 利率。机制不变：
    买 NO 组合/完整集 -> Convert -> Merge。
    结构优势复核：标记 Σp 2~3% 偏离的组（拉脱维亚 1.0325、最佳 AI 1.029、
    巴西 1.0235、Alaska 1.0225、Fed 1.02、MLB 0.9725）经订单簿精筛全部
    fail，live Σp 回到 1 附近 -> 标记价虚高，可执行边缘间歇出现、
    需高频扫描抓窗口。完整数据：data/e46m3/e46m3_trades_2026-08-09_17.json、
    e46m3_activity_2026-08-17.json。
```
