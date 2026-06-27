---
name: checkpoint-debug-reporter
description: 解析并诊断 `fix-scripts` 或 `terminal-executor` 产出的步骤执行结果，按”每步骤检查点”逐项核验并输出结构化测试报告。支持两种证据类型：Playwright DOM截图留证 和 命令 stdout/stderr 文本证据。用于步骤脚本执行后需要基于日志、下载文件、页面留证或命令输出等多源证据判断检查点是否达成。
---

# Checkpoint Debug Reporter

聚焦于执行后诊断，不负责录制脚本或修复脚本本身。  
仅通过阅读现有输出文件完成检查点核验与报告编写，不新增任何执行脚本。

## Workflow

按以下顺序执行：

1. 校验输入路径，定位目标 `case_id` 的 `step_*` 目录。
2. 逐步骤解析执行结果：
   - 识别步骤类型：检查 `execution.json` 中的 `command_type` 字段。
     - 存在 `command_type`（`local` / `ssh`）→ 命令执行步骤（来自 `terminal-executor`）
     - 不存在 `command_type` → Playwright 浏览器步骤（来自 `fix-scripts`）
   - 读取 `execution.json` 获取退出码、超时标记、耗时、错误摘要。
   - 读取 `stdout.log`/`stderr.log` 抽取尾部日志用于诊断。
3. 逐步骤检查检查点：
   - 获取该步骤应验证的检查点列表（来自用例步骤定义或原始检查点文本）。
   - 为每个检查点建立证据链，按步骤类型选择证据源：

   **Playwright 浏览器步骤：**
   - `stdout.log` / `stderr.log`
   - `execution.json`
   - `downloads/` 下文件（存在性、文件名、文件内容）
   - `step_<N>/*.png|*.html`（截图、HTML 快照等）

   **命令执行步骤（local/ssh）：**
   - `execution.json`（exit_code 为 0 表示执行成功）
   - `stdout.log`（与 `expected_output` 做文本比对：包含匹配 / 正则匹配 / 结构匹配）
   - `stderr.log`（非空时作为失败证据，但需排除 warning 级别信息）
   - `execution.log`（审计日志，用于判断超时/重试情况）

   - 对每个检查点输出结论：`verified` / `failed` / `unverifiable`。
4. 形成步骤状态（`PASS` / `WARN` / `FAIL`）并汇总总体状态。
5. 输出测试报告：
   - `summary`：结构化文本（JSON 风格）结果，供编排系统消费。
   - `report`：可读 Markdown 报告，供人工排查和归档（含“检查点-证据”明细）。
   - 报告默认输出：`./<case_id>/flow_validation_report.md`。

## Input Contract

至少提供：

- `case_dir`：目标用例目录，例如 `./WRAP_CASE_001`

可选参数：

- `--steps`：仅分析指定步骤，格式 `1,2` 或 `step_1,step_2`
- `checkpoint_source`：检查点来源（如 `./<case_id>/<case_id>_AI_create.txt` 或上游传入结构化步骤）
- `strict_checkpoint`：关键检查点无法验证或验证失败时直接判 `FAIL`（默认建议开启）
- `--tail-lines`：日志尾部保留行数，默认 `20`
- `report_output`：报告输出目标路径（可选，默认 `./<case_id>/flow_validation_report.md`）

## Decision Rules

步骤级判定（按步骤类型）：

**Playwright 浏览器步骤：**
- `FAIL`：`execution.json` 缺失，或执行退出码非 `0`，或执行超时。
- `PASS`：执行成功，且该步骤所有关键检查点均 `verified`。
- `FAIL`：执行成功但任一关键检查点 `failed`。
- `WARN`：执行成功、无关键检查点 `failed`，但存在 `unverifiable`（证据不足或证据冲突）。

**命令执行步骤（local/ssh）：**
- `FAIL`：`execution.json` 缺失，或 exit_code 非 `0`，或执行超时。
- `PASS`：exit_code 为 `0`，且所有关键检查点 `verified`。
- `FAIL`：exit_code 为 `0` 但 `stdout.log` 与 `expected_output` 匹配失败（若提供了 `expected_output`）。
- `WARN`：exit_code 为 `0`，但 `stderr.log` 含非 warning 级错误信息，或 `expected_output` 未提供导致部分检查点 `unverifiable`。
- `FAIL`：若为 SSH 连接超时/认证失败等基础设施错误，直接判 `FAIL` 并标记 `infra_error`。

说明：

- 不使用”截图数量达标”作为判定依据。
- 截图/HTML 仅作为证据载体之一，必须结合日志、下载文件和执行元数据综合判断。
- 命令执行步骤不使用截图/HTML 留证（`terminal-executor` 不产生此类产物），只使用 stdout/stderr + execution.json。

总体判定：

- 任一步骤 `FAIL`，总体 `FAIL`。
- 无 `FAIL` 但存在 `WARN`，总体 `WARN`。
- 全部 `PASS`，总体 `PASS`。

## Output Contract

输出两份内容（由模型直接生成，不依赖脚本）：

- `summary`：总体状态、步骤明细、计数汇总、失败原因列表
- `report`：面向人工的排查报告（含关键日志尾部与检查点证据明细）
- 报告中每个步骤的每个检查点必须包含：
  - 检查点文字描述
  - 检查结论（`verified|failed|unverifiable`）
  - Playwright 步骤：至少一张对应截图路径（`./<case_id>/step_<N>/cp*.png`）
  - 命令执行步骤：`stdout.log` 匹配片段或 `stderr.log` 错误摘要

推荐报告结构：

1. `Overview`：`case_id`、步骤总数、`PASS/WARN/FAIL` 计数、总体状态  
2. `Step Details`：每个步骤的执行结论、检查点逐项结论、关键证据（日志/文件/快照）与失败原因  
3. `Action Items`：重试建议、人工介入点、优先级

## Constraints

- 不要新增、修改、执行任何解析脚本。
- 不要改动步骤脚本，只消费已有执行产物。
- 不要使用”截图数量是否达标”作为主判断逻辑。
- 命令执行步骤不期望截图/HTML 产物；不要因为没有截图而降级检查点判定。
- 报告中必须显式区分”脚本执行失败””检查点验证失败””证据不足无法验证”三类问题。
- 缺少关键文件（如 `execution.json`）时，直接将对应步骤判为 `FAIL` 并记录原因。
