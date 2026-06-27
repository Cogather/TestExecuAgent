---
name: env-preparation
description: 在用例执行前完成可运行环境准备。用于需要按固定顺序完成工作目录创建、复用脚本下载、目标环境占用的场景。
---

# 环境准备

按固定顺序准备前置条件，遇到阻断性错误立即停止。

## 输入参数

开始执行前必须提供：

- `case_id`：本次执行唯一标识。
- `step_reuse_flags`：与测试步骤一一对应的 `true/false` 复用标识。
- `step_orders`：由 `step_reuse_flags` 中值为 `true` 的步骤序号组成，作为第二步脚本参数。
- `platform_env_id`：需要占用的平台环境 ID。
- `operator`：执行人与环境占用记录中的操作者标识。

可选参数：

- `lock_reason`：环境锁定原因，默认 `测试agent占用`。
- `expect_unlock_time`：预期解锁时间。
- `ssh_config`（`case_type` 为 `mml` / `hybrid` 时提供）：包含 `host`、`port`、`username`、`auth_method`。

## 执行流程

严格按顺序执行以下三步。

### 第一步：创建工作目录

创建并校验以下目录：

- `workspace_dir = ./<case_id>`

满足幂等要求：

- 目录已存在时直接复用。
- 不自动删除已有文件。

### 第二步：下载复用脚本

调用脚本：

```bash
python get_reuse_scripts.py --case_id <case_id> --step <step_orders> --output ./<case_id>
```

通过条件：

- 退出码为 `0`。
- 输出目录 `./<case_id>` 中生成了复用步骤脚本。
- 复用脚本落盘路径需遵循统一约定：`./<case_id>/<case_id>_step<N>.py`（仅 `step_reuse_flags=true` 的步骤）。

如果失败，立即停止并返回错误，不进入第三步。

### 第三步：占用环境

如果 `platform_env_id` 可用，调用既有环境管理脚本执行锁定：

```bash
python .opencode/skills/fix-playwright-scripts/scripts/env_manager.py \
    --action lock \
    --platform_env_id <platform_env_id> \
    --user <operator> \
    --lock_reason "<lock_reason>"
```

参数说明：
- `--action lock`：执行环境锁定。
- `--platform_env_id`：平台环境 ID，来自本次调用输入。
- `--user`：当前操作者标识。
- `--lock_reason`：锁定原因。

锁定成功后，只保留运行时上下文，不把 `platform_env_id` 或 `locked` 写入 `agent-memory.yaml`。  
若锁定失败，记录失败状态和错误信息，由上层编排决定是否继续。

### 第四步（可选）：SSH 连通性预检

若 `ssh_config` 已提供，在环境准备完成后执行 SSH 连通性验证：

```bash
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes \
  -p <ssh_config.port> <ssh_config.username>@<ssh_config.host> echo ok
```

通过条件：
- 退出码为 `0`。
- stdout 包含 `ok`。

若预检失败，记录失败状态和错误信息，由上层编排决定是否继续。不要将 `ssh_config` 中的密码/密钥写入日志或 `agent-memory.yaml`。

## 输出契约

返回精简汇总：

- `workspace_dir`
- `reuse_scripts_output`（默认 `./<case_id>`）
- `reusable_step_orders`（成功下载到复用脚本的步骤序号集合）
- `environment_lock_status`（`locked` 或 `failed`）
- `ssh_precheck_status`（若提供了 `ssh_config`：`reachable` 或 `failed`）
- `details`（错误信息或关键日志）

## 脚本说明

- `get_reuse_scripts.py`：第二步复用脚本获取命令
- `env_manager.py`：第三步环境占用脚本

你不需要在本 skill 中实现上述脚本，只负责按命令调用。
