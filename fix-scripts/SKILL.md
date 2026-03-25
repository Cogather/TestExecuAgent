---
name: fix-scripts
description: 修复 Playwright 步骤脚本并输出可调试证据。用于先在步骤脚本关键节点注入截图/HTML 留证代码，再通过执行包装脚本统一采集 stdout/stderr/执行元数据，并在循环中仅修复脚本逻辑问题的场景。
---

# Fix Scripts

这个 skill 的核心目标是：**修复步骤脚本**

执行必须通过包装脚本完成，包装脚本只负责统一记录日志；修复时在关键节点直接向步骤脚本写入截图和 HTML 保存代码，便于定位问题。

## 输入

至少需要：

1. `case_id`
2. 待修复脚本 `./<case_id>/<case_id>_stepN.py`
3. `python_path`（可选，不传则用默认解释器）

## 输出

每个步骤输出到 `./<case_id>/step_<N>/`：

- `stdout.log`
- `stderr.log`
- `execution.json`（退出码、耗时、错误摘要）
- `cp*.png`（关键节点截图）
- `cp*.html`（关键节点 DOM 快照）

## 工作流程

### 1. 准备执行包装脚本

```bash
python fix-scripts/scripts/run_step_with_capture.py \
  --case-id "<case_id>" \
  --step "<N>" \
  --script "./<case_id>/<case_id>_stepN.py" \
  --output-dir "./<case_id>" \
  --python-path "<python_path>"
```

### 2. 注入留证代码

在进入修复循环前，先对步骤脚本做一次关键节点留证注入。此步骤是前置步骤，不放在循环内。

每个步骤的留证点必须固定，且**最多 3 个**，不要超出：

1. `cp1_after_page_ready`：页面初次加载完成后（必选）
2. `cp2_after_key_action`：该步骤最关键业务动作完成后（必选）
3. `cp3_on_error`：`except` 异常分支中（可选，仅异常时触发）

约束：

- 不允许再注入第 4 个留证点。
- 一个步骤里存在多个点击/输入时，只保留“最关键动作”作为 `cp2`。
- 循环修复阶段只改业务逻辑，不新增留证点。

推荐写法：

```python
checkpoint_dir = "./<case_id>/step_<N>"
os.makedirs(checkpoint_dir, exist_ok=True)
page.screenshot(path=f"{checkpoint_dir}/cp2_after_key_action.png", full_page=True)
with open(f"{checkpoint_dir}/cp2_after_key_action.html", "w", encoding="utf-8") as f:
    f.write(page.content())
```

### 3. 循环修复（每轮验证，失败触发用户交互）

循环内只修复脚本逻辑问题，不再新增或重构留证注入点。每轮固定顺序：

#### 3.1 Playwright MCP 介入验证

1. 打开目标 URL，确认页面可访问。
2. 基于当前脚本中的关键选择器，确认元素是否存在、是否可交互。
3. 对关键动作（点击、输入、下拉选择、跳转）做最小验证，记录问题点。

#### 3.2 执行包装脚本

1. 使用 `run_step_with_capture.py` 执行步骤脚本。
2. 读取 `stdout.log`、`stderr.log`、`execution.json`。
3. 检查 `./<case_id>/step_<N>/`：
   - 至少存在 `cp1` 与 `cp2` 的 `.png` 留证（异常时允许出现 `cp3`）。
   - `.png` 留证总数不得超过 3，`.html` 留证总数不得超过 3。

#### 3.3 判定本轮结果

本轮通过条件：

- 包装执行退出码为 `0`
- 留证点符合“每步最多 3 个”约束，且包含 `cp1`、`cp2`
- 脚本逻辑断言通过

若通过则结束修复；若不通过，进入 3.4。

#### 3.4 修复脚本

修复以下逻辑问题：

- 选择器不稳定
- 等待时机不正确
- 弹窗/下载/跳转处理缺失
- 断言不合理或缺失

#### 3.5 三轮失败后的交互升级（不可跳过当前步骤）

若连续 3 轮仍失败，不允许跳过当前步骤，必须先与用户交互补充现场信息，再继续修复当前步骤。

交互要求（至少覆盖以下问题）：

1. 当前页面实际停留在哪个 URL 或页面标题？
2. 界面上最后一个成功动作是什么？
3. 卡住时看到的元素/弹窗/报错文本是什么？
4. 预期下一步应出现什么，但实际没有出现什么？

拿到用户反馈后：

- 更新当前步骤脚本并再次执行包装脚本验证。
- 继续“验证 -> 修复 -> 验证”循环，直到当前步骤可用。
- 若仍无法恢复，明确输出阻塞原因并等待用户进一步信息；**不得标记当前步骤为跳过**。

### 4. 修复完成标准

- MCP 关键动作验证通过
- 包装执行退出码为 `0`
- 关键断言通过
- 留证文件存在且可读（位于 `./<case_id>/step_<N>/`）
- 每步留证点不超过 3 个（`cp1`、`cp2`、`cp3`）
- 当前步骤已验证可用后，才能进入下一步骤

## 约束

- 不允许因修复轮次达到上限而跳过当前步骤。
- 不允许在当前步骤未验证可用时推进到下一步骤。
- 三轮失败后必须先向用户询问“卡在哪里、界面出现了什么问题”，再继续修复。

## 脚本资源

- `scripts/run_step_with_capture.py`：执行包装器，统一采集执行日志与元数据。
