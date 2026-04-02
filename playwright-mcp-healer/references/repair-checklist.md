# 修复卡片

## 修复前

- 先运行 Python 脚本
- 记录当前坏点
- 判断是否其实是更早一步状态漂移

## 修复时

- 先划分 `stable_segment` 和 `failing_step`
- 用 `browser_run_code` 跑 `stable_segment`
- 用细粒度 MCP 修 `failing_step`
- 需要时检查 URL、title、console、network、截图

## 修复后

- 继续批量推进后续稳定区段
- 在下一个关键边界或新坏点停下
- 如果出现新坏点，重复同样编排

## 最后验证

- 先验证最近修复点
- 再验证更长区段
- 条件允许时验证全流程
- 明确说明未验证部分
