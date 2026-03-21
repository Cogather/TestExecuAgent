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
- `reports/checkpoints/*.png`（关键节点截图）
- `reports/checkpoints/*.html`（关键节点 DOM 快照）

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

在以下节点写入截图与 HTML 保存代码：

- 页面初次加载后
- 登录提交前后
- 关键点击前后
- 页面跳转完成后
- 最终断言前
- `except` 异常分支中

推荐写法：

```python
checkpoint_dir = "./<case_id>/step_<N>"
os.makedirs(checkpoint_dir, exist_ok=True)
page.screenshot(path=f"{checkpoint_dir}/after-login-submit.png", full_page=True)
with open(f"{checkpoint_dir}/after-login-submit.html", "w", encoding="utf-8") as f:
    f.write(page.content())
```

### 3. 循环修复（最多 3 轮）

循环内只修复脚本逻辑问题，不再新增或重构留证注入点。每轮固定顺序：

#### 3.1 Playwright MCP 介入验证

1. 打开目标 URL，确认页面可访问。
2. 基于当前脚本中的关键选择器，确认元素是否存在、是否可交互。
3. 对关键动作（点击、输入、下拉选择、跳转）做最小验证，记录问题点。

#### 3.2 执行包装脚本

1. 使用 `run_step_with_capture.py` 执行步骤脚本。
2. 读取 `stdout.log`、`stderr.log`、`execution.json`。
3. 检查 `./<case_id>/step_<N>/reports/checkpoints` 下是否已有留证文件（至少一张 `.png`，建议同时存在 `.html`）。

#### 3.3 判定本轮结果

本轮通过条件：

- 包装执行退出码为 `0`
- 存在关键节点截图文件
- 脚本逻辑断言通过

若通过则结束修复；若不通过，进入 3.4。

#### 3.4 修复脚本

修复以下逻辑问题：

- 选择器不稳定
- 等待时机不正确
- 弹窗/下载/跳转处理缺失
- 断言不合理或缺失

连续 3 轮仍失败时，停止并输出失败原因与建议人工介入点。

### 4. 修复完成标准

- MCP 关键动作验证通过
- 包装执行退出码为 `0`
- 关键断言通过
- 关键节点留证文件存在且可读（位于 `./<case_id>/step_<N>/reports/checkpoints`）

## 脚本资源

- `scripts/run_step_with_capture.py`：执行包装器，统一采集执行日志与元数据。
