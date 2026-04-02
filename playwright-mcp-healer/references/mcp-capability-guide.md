# MCP 使用卡片

## 什么时候用 `browser_run_code`

- 当前路径清晰
- 前置动作稳定
- 目标是快速推进到当前坏点前

典型场景：
- 登录
- 进入列表页
- 搜索对象
- 打开详情页
- 进入稳定编辑页

## 什么时候切到细粒度 MCP

- 已经接近当前坏点
- 页面意图不清楚
- 弹窗、抽屉、iframe 可能变化
- 需要重新看元素 refs
- 需要看 console、network、截图证据

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

## 核心规则

- 稳定区段批量推进
- 当前坏点单独精查
- 修完后如果后续重新稳定，再回到 `browser_run_code`
- 如果后续又坏，再进入下一轮
