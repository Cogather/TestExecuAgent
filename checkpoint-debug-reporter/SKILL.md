---
name: checkpoint-debug-reporter
description: 解析并诊断 `fix-scripts` 产出的步骤执行结果，检查检查点留证完整性，并输出结构化测试报告。用于步骤脚本执行后需要快速定位失败原因、判断留证覆盖、沉淀可读报告（Markdown/JSON）的场景，尤其适用于 `./<case_id>/step_<N>/execution.json`、`stdout.log`、`stderr.log`、`reports/checkpoints/*` 已生成时。
---

# Checkpoint Debug Reporter

聚焦于执行后诊断，不负责录制脚本或修复脚本本身。  
仅通过阅读现有输出文件完成检查点核验与报告编写，不新增任何执行脚本。

## Workflow

按以下顺序执行：

1. 校验输入路径，定位目标 `case_id` 的 `step_*` 目录。
2. 逐步骤解析执行结果：
   - 读取 `execution.json` 获取退出码、超时标记、耗时、错误摘要。
   - 读取 `stdout.log`/`stderr.log` 抽取尾部日志用于诊断。
3. 逐步骤检查检查点：
   - 统计 `reports/checkpoints` 下 `.png` 和 `.html` 文件。
   - 对照阈值判断留证是否达标。
4. 形成步骤状态（`PASS` / `WARN` / `FAIL`）并汇总总体状态。
5. 输出测试报告：
   - `summary`：结构化文本（JSON 风格）结果，供编排系统消费。
   - `report`：可读 Markdown 报告，供人工排查和归档。

## Input Contract

至少提供：

- `case_dir`：目标用例目录，例如 `./WRAP_CASE_001`

可选参数：

- `--steps`：仅分析指定步骤，格式 `1,2` 或 `step_1,step_2`
- `--min-png`：每步最少截图数量，默认 `1`
- `--require-html`：要求每步至少有一个 `.html` 快照
- `--strict-checkpoint`：检查点不达标时直接判 `FAIL`（默认不启用，判 `WARN`）
- `--tail-lines`：日志尾部保留行数，默认 `20`
- `report_output`：报告输出目标路径（可选）

## Decision Rules

步骤级判定：

- `FAIL`：`execution.json` 缺失，或执行退出码非 `0`，或执行超时。
- `WARN`：执行成功但检查点覆盖不达标（如截图数量不足），且未启用 `--strict-checkpoint`。
- `FAIL`：执行成功但检查点覆盖不达标，且启用 `--strict-checkpoint`。
- `PASS`：执行成功且检查点覆盖达标。

总体判定：

- 任一步骤 `FAIL`，总体 `FAIL`。
- 无 `FAIL` 但存在 `WARN`，总体 `WARN`。
- 全部 `PASS`，总体 `PASS`。

## Output Contract

输出两份内容（由模型直接生成，不依赖脚本）：

- `summary`：总体状态、步骤明细、计数汇总、失败原因列表
- `report`：面向人工的排查报告（含关键日志尾部与留证统计）

推荐报告结构：

1. `Overview`：`case_id`、步骤总数、`PASS/WARN/FAIL` 计数、总体状态  
2. `Step Details`：每个步骤的执行结论、检查点统计、失败原因、关键日志摘录  
3. `Action Items`：重试建议、人工介入点、优先级

## Integration Notes

推荐在以下链路中使用本 skill：

1. 使用 `$env-preparation` 完成环境与目录准备。
2. 使用 `$record-scripts` 生成或复用步骤脚本。
3. 使用 `$fix-scripts` 执行并修复步骤脚本，产出执行证据。
4. 使用 `$checkpoint-debug-reporter` 生成诊断报告并给出结论。

## Constraints

- 不要新增、修改、执行任何解析脚本。
- 不要改动步骤脚本，只消费已有执行产物。
- 报告中必须显式区分“脚本执行失败”和“检查点留证不足”两类问题。
- 缺少关键文件（如 `execution.json`）时，直接将对应步骤判为 `FAIL` 并记录原因。
