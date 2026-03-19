---
name: fix-playwright-ops
description: 负责 fix 阶段两次运行时操作：第一次环境锁定，第二次修复结果登记与环境释放。
---

# Fix Playwright Ops

这个 skill 只负责 fix 阶段的运行时操作，而且会在一次完整流程中被调用两次：

1. 第一次调用：进入 fix 阶段之前，执行环境锁定。
2. 第二次调用：`fix-playwright-output-manager` 完成后，执行修复结果登记与环境释放。

Python 解释器发现和用例根目录创建不属于本 skill 的职责。
它不负责脚本修复，也不负责脚本执行与输出收集。

## 适用场景

- 第一次调用：当流程即将进入 fix 阶段，但还没有锁定环境时。
- 第二次调用：当 fix 阶段已经结束，需要登记修复结果并释放环境时。

## 需要的输入

第一次调用至少需要以下信息：

1. `case_id`
2. `platform_env_id`
3. 可选的 `user`
4. 可选的 `expect_unlock_time`

第二次调用至少需要以下信息：

1. `case_id`
2. 修复后的脚本元数据
3. 可选的 `platform_env_id`
4. 可选的 `user`

## 工作流程

### 第一次调用：环境锁定

1. 确认本次调用发生在 fix 阶段开始前。
2. 如果 `platform_env_id` 可用，调用既有环境管理脚本执行锁定：

```bash
python .opencode/skills/fix-playwright-scripts/scripts/env_manager.py \
    --action lock \
    --platform_env_id <平台环境ID> \
    --user <用户名> \
    --lock_reason "测试agent占用" \
    --expect_unlock_time "2024-01-03 10:00:00"
```

3. 参数说明：
   - `--action lock`：执行环境锁定。
   - `--platform_env_id`：平台环境 ID，来自本次调用输入。
   - `--user`：当前操作者或用户名，可选，不传则按上层约定处理。
   - `--lock_reason`：锁定原因，默认可使用“测试agent占用”。
   - `--expect_unlock_time`：预计释放时间，可由编排层或调用方填写。
4. 锁定成功后，只保留运行时上下文，不把 `platform_env_id` 或 `locked` 写入 `agent-memory.yaml`。
5. 若锁定失败，记录失败状态和错误信息，由上层编排决定是否继续。
6. 这次调用不做修复结果登记，也不做环境释放。

### 第二次调用：修复结果登记与环境释放

1. 确认本次调用发生在 `fix-playwright-output-manager` 结束之后。
2. 如果本次调用携带修复后的脚本元数据，则按步骤逐条调用既有上报脚本完成登记：

```bash
python store_steps.py --case_id "ID123" --case_name "测试用例" --step_order 1 --step_description "步骤描述" --checkpoint "检查点" --tool_name "tool.py"
```

3. 若有多个步骤元数据，按 `step_order` 逐条重复上报，保持字段含义与既有流程一致，不自行改写。
4. 若本次流程之前已经完成环境锁定，则调用既有环境管理脚本执行释放：

```bash
python .opencode/skills/fix-playwright-scripts/scripts/env_manager.py \
    --action unlock \
    --platform_env_id <平台环境ID>
```

5. 参数说明：
   - `--action unlock`：执行环境释放。
   - `--platform_env_id`：平台环境 ID，必须与锁定时一致。
6. 如果本次流程没有完成环境锁定，则跳过释放动作。
7. 若释放失败，记录失败状态和错误信息，由上层编排决定是否继续。
8. 这次调用不再执行环境锁定。

## 主要脚本契约

本 skill 只使用既有脚本，不引入新的脚本名：

```bash
python .opencode/skills/fix-playwright-scripts/scripts/env_manager.py --action lock --platform_env_id <平台环境ID> --user <用户名>
python .opencode/skills/fix-playwright-scripts/scripts/env_manager.py --action unlock --platform_env_id <平台环境ID>
python store_steps.py --case_id "ID123" --case_name "测试用例" --step_order 1 --step_description "步骤描述" --checkpoint "检查点" --tool_name "tool.py"
```

## 边界说明

- 不负责脚本修复
- 不负责脚本执行与输出收集
- 不负责验证判定
- 不改写测试步骤或预期结果
- 不负责 Python 解释器发现
- 不负责用例根目录创建
- 不负责决定何时调用第一次或第二次，本身只执行对应阶段的动作

## 结束条件

第一次调用在环境锁定完成后结束。第二次调用在修复结果登记和环境释放完成后结束。
