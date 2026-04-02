---
name: playwright-fixwmcp
description: 用于修复失败的 Python Playwright 脚本。只要用户出现脚本报错、定位器失效、UI 流程脆弱、回归脚本不稳定等情况，就应优先使用本 skill。注意 Python 脚本运行实例与 MCP 浏览器实例不是同一个：第一步只通过本地报错定位坏点代码行，第二步做分割，第三步才由 MCP 接手复现与修复。执行时必须显式写出每一步使用的工具、调用顺序与调用目的。
---

# Playwright Fix with MCP

## 目标

在不改变业务流程意图的前提下，快速修复失败脚本

## 关键前提

- Python 脚本运行实例 与 MCP 浏览器实例相互独立，不共享运行时状态。
- 因此第一步只能通过本地运行报错（traceback、失败行号、失败调用）定位坏点。
- MCP 只能从第三步开始接手：先重建稳定段，再在坏点处精查修复。

## 触发条件

出现以下任一情况就使用本 skill：

- 用户给出 Playwright Python 脚本并说“跑不通/报错/不稳定”
- 定位器相关失败（找不到元素、strict mode、不可交互）
- 流程在弹窗/iframe/重定向/异步加载处脆弱
- 用户要求“修脚本 + 保持流程 + 给出验证结论”

## 输入

- 必需：脚本路径或脚本内容
- 可选：traceback、截图、trace、console/network 日志、目标 URL、账号与前置条件

信息不足时先补齐最小必要信息，不要盲修。

---

## 执行协议（每步都要写工具与调用）

> 强制要求：每个步骤输出都用以下格式：
>
> - `步骤`：
> - `使用工具`：
> - `调用方式`：

### 步骤 1：本地复现并定位坏点代码行

- 使用工具：
  - 本地 Python 执行（运行原始脚本）
- 调用方式（示例）：
  - 本地运行脚本，仅依据 traceback 定位第一处失败
  - 记录：失败文件、失败行号、失败函数调用、异常类型、异常信息
- 预期结果：确定“当前坏点代码行”和“失败语义”（例如 timeout / locator not found / strict mode）

### 步骤 2：基于报错结果拆分 stable_segment 与 failing_step

- 使用工具：
  - 不调用 MCP 工具（这是分析步骤）
- 调用方式：
  - 根据步骤 1 的失败行号和调用栈切分：
    - `stable_segment` = 坏点前稳定步骤
    - `failing_step` = 当前失败动作/断言
- 预期结果：得到可批量推进边界与精查目标（供 MCP 在下一步接手）

### 步骤 3：MCP 接手，批量推进 stable_segment

- 使用工具：
  - `browser_run_code`
- 调用方式（模板）：
  - 由 MCP 浏览器实例从起点重建流程
  - 把 `stable_segment` 对应操作写入一段可执行代码，一次推进到坏点前
- 调用示例（伪代码表达）：
  - `browser_run_code(code="执行登录 -> 列表页 -> 搜索 -> 打开详情页")`
- 预期结果：MCP 实例到达坏点附近，准备进入细粒度修复

### 步骤 4：在 failing_step 切细粒度工具修复

按以下顺序调用（必要时循环）：

1. 页面状态确认
   - 工具：`browser_snapshot`
   - 调用目的：确认当前可见元素、refs、页面结构

2. 等待条件确认
   - 工具：`browser_wait_for`
   - 调用目的：等待正确状态而非盲点

3. 交互修复
   - 工具：`browser_click` / `browser_type` / `browser_fill_form` / `browser_select_option`
   - 调用目的：修复失败动作（点击、输入、表单、下拉）

4. 根因补证
   - 工具：`browser_evaluate` / `browser_console_messages` / `browser_network_requests` / `browser_take_screenshot`
   - 调用目的：验证 DOM 状态、控制台错误、请求异常、视觉证据

- 调用方式（示例链路）：
  - `browser_snapshot` -> `browser_wait_for` -> `browser_click` -> `browser_evaluate` -> `browser_console_messages`

### 步骤 5：局部验证当前修复点

- 使用工具：
  - `browser_run_code`（仅执行坏点前后最小区段）
  - 必要时 `browser_snapshot` / `browser_take_screenshot`
- 调用方式：
  - 最小回放验证“当前坏点是否已通过”
- 预期结果：确认本次改动有效且未引入明显副作用

### 步骤 6：继续推进 / 进入下一轮

- 使用工具：
  - 稳定时：`browser_run_code`
  - 新坏点时：回到步骤 4 的细粒度工具链
- 调用方式：
  - “稳定段批量推进，坏点精查修复”反复循环

### 步骤 7：收尾验证

- 使用工具：
  - `browser_run_code`（全流程）
  - 必要时 `browser_console_messages` / `browser_network_requests`
- 调用方式：
  - 至少完成一次全流程验证
- 预期结果：无阻断失败；若有阻塞，明确列出外部原因

---

## 工具调用速查表（显式）

- `browser_run_code`
  - 用途：稳定区段批量推进
  - 禁止：把可疑失败步骤打包进去

- `browser_snapshot`
  - 用途：坏点处看 refs 与页面结构

- `browser_wait_for`
  - 用途：等待关键状态（元素可见/可交互/文本出现）

- `browser_click` / `browser_type` / `browser_fill_form` / `browser_select_option`
  - 用途：执行具体交互修复

- `browser_evaluate`
  - 用途：读取 DOM 状态、属性、运行时条件

- `browser_console_messages` / `browser_network_requests`
  - 用途：在 MCP 接手后，查 JS 报错与请求异常（不是 Python 原始实例报错）

- `browser_take_screenshot`
  - 用途：留视觉证据与回归对比

---

## 切换规则（必须遵守）

### 允许用 `browser_run_code`

- 路径清晰
- 动作重复且稳定
- 不需要实时观察 DOM/网络来决策

### 必须切细粒度工具

- 临近或进入坏点
- 弹窗/iframe/重定向/遮挡/竞态
- 定位器歧义或状态不一致
- 需要证据（snapshot/console/network/screenshot）

---

## 完成标准

- 初始坏点已修复
- 无新增阻断性失败
- 至少 1 次全流程通过，或清楚记录外部阻塞

---

## 输出格式（必须）

### 总结
- 本轮修复目标与结论

### 当前坏点
- 失败位置
- 失败现象
- 根因判断

### 分步工具调用记录
- 步骤 1（本地）：工具、调用方式、结果（必须包含失败文件+行号+异常）
- 步骤 2（分析）：切分依据与分段结果
- 步骤 3（MCP 接手）：工具、调用方式、结果
- ...

### 脚本修改
- 变更点（精确补丁或关键片段）
- 每个变更解决的问题

### 验证情况
- 局部验证结果
- 全流程验证结果

### 剩余风险
- 未解决项
- 外部依赖与前置条件
