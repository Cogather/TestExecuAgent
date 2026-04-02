---
name: playwright-mcp-healer
description: 结合本地脚本执行与 Playwright MCP 来修复失败的 Python Playwright 脚本。适用于收到 Playwright Python 脚本、报错栈、脆弱 UI 流程或定位器失效时：先运行脚本定位当前坏点，再用 Playwright MCP 的 `browser_run_code` 批量重放稳定区段，用细粒度 MCP 修复当前坏点，并循环推进到下一个坏点。
---

# Playwright MCP 修复器

先定位当前坏点，再把 MCP 用在最有价值的地方：稳定区段批量推进，坏点单独精查，后续继续按同样模式循环。

## 输入

- Playwright `.py` 脚本
- 可选的 traceback、截图、trace、日志
- 可选的 URL、流程说明、登录说明

## 核心编排

1. 运行原始 Python 脚本，定位当前坏点。
2. 划分两段：
   - `stable_segment`：当前坏点之前可批量重放的稳定动作
   - `failing_step`：当前真正失败的动作或断言
3. 用 Playwright MCP `browser_run_code` 一次执行 `stable_segment`。
4. 到达当前坏点后，改用细粒度 MCP 工具检查和修复：
   - `browser_snapshot`
   - `browser_click`
   - `browser_type`
   - `browser_fill_form`
   - `browser_select_option`
   - `browser_wait_for`
   - `browser_evaluate`
   - `browser_console_messages`
   - `browser_network_requests`
   - `browser_take_screenshot`
5. 修复当前坏点后，继续用 `browser_run_code` 推进其后的稳定区段。
6. 如果后续又遇到新的坏点，重复以上编排。
7. 当不再出现新的坏点时，再做局部验证和全流程验证。

## 切换规则

- 稳定、清晰、重复性高的动作：用 `browser_run_code`
- 接近坏点、页面意图不清、弹窗或 iframe 变化、需要看 refs：改用细粒度 MCP
- 修完一个坏点后，如果后续重新稳定：回到 `browser_run_code`

## 约束

- 不要追求固定三次工具调用。
- 不要把未知风险打包进一个过大的 `browser_run_code`。
- 不要把真正可疑的失败步骤藏进批量执行里。
- 目标是用尽可能少的调用穿过稳定区段，并在每个真正有风险的点停下。

## 输出

- 修复后的 Python 脚本或精确补丁
- 简洁报告：
  - `总结`
  - `当前坏点`
  - `本轮批量重放`
  - `细粒度发现`
  - `脚本修改`
  - `验证情况`
  - `剩余风险`
