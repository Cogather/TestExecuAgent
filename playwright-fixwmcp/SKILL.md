---
name: playwright-fixwmcp
description: 用于修复失败的 Python Playwright 脚本。只要用户提供脚本报错、定位器失效、UI 流程脆弱、回归脚本不稳定等场景，就应优先使用本 skill。核心方法是“先本地复现定位坏点，再用 browser_run_code 批量穿过稳定段，在坏点切到细粒度 MCP 修复，然后循环推进到下一个坏点”。
---

# Playwright Fix with MCP

## 目标

在不改变业务流程意图的前提下，快速修复失败的 Python Playwright 脚本：

- 稳定段快速通过
- 坏点精准修复
- 每轮都有可验证结果

## 适用信号（触发条件）

出现以下任一情况，就使用本 skill：

- 用户给出 Playwright Python 脚本并说“跑不通/报错/不稳定”
- 报错与定位器相关（元素找不到、strict mode、元素不可交互）
- 流程在弹窗、iframe、重定向、异步加载处容易失败
- 用户要求“修脚本 + 保持流程 + 给出改动与验证说明”

## 输入

- 必需：失败脚本路径或脚本内容
- 可选：traceback、截图、trace、console/network 日志、目标 URL、账号与前置条件

缺失信息时，先说明缺口并请求最小必要信息；不要在未知前置上盲修。

## 执行协议（固定循环）

1. **复现当前失败**
   - 先运行原始脚本，记录第一处真实失败点。
   - 失败点必须落到具体动作/断言（例如“点击提交后等待 toast 超时”）。

2. **分段**
   - `stable_segment`：坏点之前可稳定重复的步骤。
   - `failing_step`：当前真正失败的动作或断言。

3. **批量推进稳定段**
   - 使用 `browser_run_code` 一次执行 `stable_segment`。
   - 目的：低成本到达坏点，而不是在稳定区反复细调。

4. **坏点细粒度诊断与修复**
   - 组合使用以下工具确认页面真实状态并修复：
     - `browser_snapshot`
     - `browser_wait_for`
     - `browser_click`
     - `browser_type`
     - `browser_fill_form`
     - `browser_select_option`
     - `browser_evaluate`
     - `browser_console_messages`
     - `browser_network_requests`
     - `browser_take_screenshot`
   - 只做最小必要改动，不改业务意图。

5. **局部验证**
   - 先验证当前坏点已通过，再继续推进。

6. **继续推进或进入下一轮**
   - 若后续稳定，回到 `browser_run_code` 批量推进。
   - 若出现新坏点，回到步骤 2，重复同一循环。

7. **收尾验证**
   - 至少完成一次全流程验证。
   - 若仍有阻塞，明确列出阻塞条件与剩余风险。

## 切换策略（关键）

### 用 `browser_run_code` 的条件

- 当前区段动作重复且稳定
- 页面意图明确
- 不需要实时观察 DOM/网络才能决策

### 必须切到细粒度 MCP 的条件

- 临近或进入失败点
- 存在弹窗、iframe、重定向、遮挡、加载竞态
- 定位器命中不唯一或与页面状态不一致
- 需要依据 snapshot/console/network 决策下一步

## 硬性约束

- 不把“可疑失败步骤”藏进大段批量执行。
- 不在状态未确认时连续盲点。
- 不为了通过而改坏业务流程。
- 不做与当前坏点无关的大规模重构。

## 修改原则

- 优先修改定位器稳定性（语义化、唯一性、可等待性）。
- 优先修复时序问题（等待条件与断言时机）。
- 每次改动尽量小，便于回归与定位副作用。

## 完成标准

满足以下条件才算完成：

- 初始坏点已修复
- 无新增阻断性失败
- 全流程至少 1 次通过，或已明确记录外部阻塞

## 附录 A：MCP 使用卡片（执行时快速参考）

### 什么时候用 `browser_run_code`

- 当前路径清晰
- 前置动作稳定
- 目标是快速推进到当前坏点前

典型场景：登录、进入列表页、搜索对象、打开详情页、进入稳定编辑页。

### 什么时候切到细粒度 MCP

- 已接近当前坏点
- 页面意图不清楚
- 弹窗/抽屉/iframe 可能变化
- 需要重新看元素 refs
- 需要 console/network/截图证据

常用工具：
- `browser_snapshot`
- `browser_click`
- `browser_type`
- `browser_fill_form`
- `browser_wait_for`
- `browser_evaluate`
- `browser_console_messages`
- `browser_network_requests`
- `browser_take_screenshot`

### 核心规则

- 稳定区段批量推进
- 当前坏点单独精查
- 修完后若后续稳定，回到 `browser_run_code`
- 后续再坏，进入下一轮

## 附录 B：修复检查清单

### 修复前

- 先运行 Python 脚本
- 记录当前坏点
- 判断是否其实是更早一步状态漂移

### 修复时

- 先划分 `stable_segment` 和 `failing_step`
- 用 `browser_run_code` 跑 `stable_segment`
- 用细粒度 MCP 修 `failing_step`
- 需要时检查 URL、title、console、network、截图

### 修复后

- 继续批量推进后续稳定区段
- 在下一个关键边界或新坏点停下
- 如果出现新坏点，重复同样编排

### 最后验证

- 先验证最近修复点
- 再验证更长区段
- 条件允许时验证全流程
- 明确说明未验证部分

## 输出格式（必须）

按以下结构输出：

### 总结

- 本轮修复目标与结果

### 当前坏点

- 失败位置
- 失败现象
- 根因判断

### 本轮批量重放

- `stable_segment` 覆盖范围
- 使用 `browser_run_code` 的原因

### 细粒度发现

- 关键 snapshot/console/network 观察
- 决策依据

### 脚本修改

- 变更点（尽量给出精确补丁或关键片段）
- 每个变更解决的问题

### 验证情况

- 局部验证结果
- 全流程验证结果

### 剩余风险

- 未解决项
- 外部依赖或前置条件
