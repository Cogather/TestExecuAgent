---
name: terminal-executor
description: 在测试流程中执行本地 Shell 命令或 SSH 远程命令。用于 MML/API 类型用例步骤，通过 MCP Server 完成本地脚本执行和远程网元设备命令下发，采集 stdout/stderr/exit_code 作为执行证据。也用于 Web 测试流程中需要穿插运行本地脚本或远程检查的场景。
---

# Terminal Executor

负责执行命令行步骤并产出结构化执行证据，不负责脚本录制、参数泛化或结果判定。

## 定位

本 Skill 是 MML/API 类型测试用例的**步骤执行引擎**，对应 Web 类型用例中 `fix-scripts` 的角色。产出格式与 `fix-scripts` 保持一致，确保下游 `checkpoint-debug-reporter` 可统一消费。

## 输入

必填：

- `case_id`：用例唯一标识
- `workspace_dir`：工作目录，默认 `./<case_id>`
- `steps`：步骤列表，每项包含：
  - `step_order`：步骤序号
  - `command_type`：`local` | `ssh`
  - `command`：命令字符串
  - `expected_output`（可选）：预期输出，用于初步比对
  - `timeout_ms`（可选）：单步超时，默认 120000

按需传入（SSH 步骤时必填）：

- `ssh_config`：
  - `host`：目标 IP/域名
  - `port`：SSH 端口，默认 22
  - `username`：登录用户名
  - `auth_method`：`password` | `key`
  - `password`（当 auth_method=password，通过环境变量传入）
  - `key_path`（当 auth_method=key）

## 输出

每个步骤输出到 `./<case_id>/step_<N>/`：

- `stdout.log`：标准输出全文
- `stderr.log`：标准错误全文
- `execution.json`：`{step_order, exit_code, duration_ms, command, command_type, error_summary}`
- `execution.log`：完整执行元数据（时间戳、MCP 工具名、重试次数）

## 工作流程

### 阶段一：步骤解析与安全检查

1. 遍历所有步骤，按 `command_type` 分组（`local` / `ssh`）。
2. 检查命令白名单：每个 `command` 的第一词（basename）必须在 `terminal-executor/config/allowed-commands.yaml` 白名单内。
3. 检查危险命令黑名单：`command` 字符串不得命中 `terminal-executor/config/dangerous-commands.yaml` 中的任何模式。
4. 若任一步骤未通过安全检查，立即中止并标记 `blocked`，输出被拦截的命令文本（已脱敏）。
5. SSH 步骤：执行连通性预检 — 通过 `shell-local` MCP 运行 `ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no <host> echo ok` 确认可达。

### 阶段二：逐步执行

对每个步骤 N，通过对应 MCP Server 执行命令：

#### local 步骤

使用 `shell-local` MCP 的 `execute_shell` 工具（`mcp__shell-local__execute_shell`）：

- `command`：命令字符串
- `workdir`：`./<case_id>`
- `timeout`：`timeout_ms / 1000` 秒

#### ssh 步骤

使用 `ssh-remote` MCP 的 `exec` 工具（`mcp__ssh-remote__exec`）：

- `command`：命令字符串
- `host`：`ssh_config.host`
- `username`：`ssh_config.username`
- `password`：`ssh_config.password`（仅 `auth_method=password` 时）
- `key_path`：`ssh_config.key_path`（仅 `auth_method=key` 时）
- `timeout`：`timeout_ms`（毫秒）

若步骤需要特权执行，使用 `ssh-remote` MCP 的 `sudo-exec` 工具（`mcp__ssh-remote__sudo-exec`）。

### 阶段三：输出采集与落盘

每个步骤执行完成后：

1. 将 stdout/stderr 写入 `./<case_id>/step_<N>/stdout.log` 和 `stderr.log`。
2. 生成 `execution.json`：
   ```json
   {
     "step_order": 1,
     "exit_code": 0,
     "duration_ms": 1234,
     "command": "mml show version",
     "command_type": "ssh",
     "error_summary": ""
   }
   ```
3. 追加 `execution.log`：记录时间戳、调用工具名、命令（已脱敏）、exit_code、耗时。

### 阶段四：失败处理

1. exit_code != 0 时，记录失败原因到 `execution.json` 的 `error_summary`，将 stdout/stderr 全文写入日志。
2. **SSH 命令不自动重试**（MML 命令是状态变更操作，幂等性不确定）。
3. **本地脚本重试最多 1 次**（仅对脚本文件路径，非交互命令）。
4. 若为连接超时/认证失败等基础设施错误，标记为 `blocked` 并中断流程。

### 阶段五：完成汇总

输出：

- `steps_executed`：已执行步骤数
- `steps_passed`：exit_code=0 的步骤数
- `steps_failed`：exit_code!=0 的步骤数
- `step_details`：每条步骤的 exit_code + 耗时 + 错误摘要

## MCP 工具映射

| 步骤类型 | MCP Server | 工具名 | 用途 |
|---|---|---|---|
| local | `shell-local` | `mcp__shell-local__execute_shell` | 运行本地命令/脚本 |
| ssh | `ssh-remote` | `mcp__ssh-remote__exec` | 执行远程命令 |
| ssh (sudo) | `ssh-remote` | `mcp__ssh-remote__sudo-exec` | 特权命令 |
| 预检查 | `shell-local` | `mcp__shell-local__execute_shell` | SSH 连通性测试 |

## 约束

- 不在本 Skill 中做结果判定，仅采集并结构化执行证据。
- 不修改其他 Skill 的输入输出契约。
- 命令中的敏感信息（密码、Token、密钥）不得写入任何日志文件。写入前扫描 stderr.log 中的敏感模式并替换为 `[REDACTED]`。
- 超时后必须明确记录 `timeout` 状态，不得静默丢弃。
- SSH 连接在执行完所有 ssh 步骤后由 MCP Server 自动管理释放。
- 输出产物格式必须与 `fix-scripts` 的 `execution.json` + `stdout.log` + `stderr.log` 保持一致，确保下游兼容。

## 安全规则

### 命令白名单

`local` 步骤只允许执行 `terminal-executor/config/allowed-commands.yaml` 中声明的命令（按 basename 匹配）。

### 危险命令黑名单

以下模式命中任一条直接拒绝并标记 `blocked`：

- `rm -rf /` / `rm -rf /*`
- `shutdown` / `reboot` / `halt` / `poweroff`
- `mkfs` / `dd if=`
- `chmod 777 /` / `chown -R`
- `:(){ :|:& };:`（fork bomb）
- `> /dev/sda` / `> /dev/sd*`
- `iptables -F` / `iptables -X`
- `curl ... | sh` / `wget ... | bash`

详细黑名单参见 `terminal-executor/config/dangerous-commands.yaml`。

### 输出脱敏

`stderr.log` 写入前扫描是否包含以下敏感模式，命中则替换为 `[REDACTED]`：

- `password=` / `passwd=` / `secret=`
- 私钥头尾标记：`-----BEGIN.*PRIVATE KEY-----` / `-----BEGIN RSA PRIVATE KEY-----`
- JWT Token：`eyJ.*\..*\..*`
- IP 地址（默认不脱敏，除非上下文要求）
