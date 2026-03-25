---
name: result-finalizer
description: 在测试执行或结果判定完成后，按固定收尾顺序完成结果上报、脚本参数泛化、语料入库、环境释放、上传归档和工作目录清理。用于已拿到用例级结论（success/fail/interrupt）且需要标准化落库、归档与回收资源的场景，尤其适用于存在 `case_id`、`platform_env_id`、结果目录 `./<case_id>` 的自动化执行链路。
---

# Result Finalizer

这个 skill 只负责收尾，不负责录制、参数还原、修复或再次执行步骤脚本。  
必须按固定顺序处理六件事：`结果上报 -> 脚本参数泛化 -> 语料入库 -> 环境释放 -> 上传归档 -> 工作目录清理`。

## Use When

在以下场景触发：

- 已完成用例执行或结果判定，需要对外系统做结束态上报。
- 需要把可复用步骤/证据摘要写入语料库（知识库）。
- 需要释放 `platform_env_id` 对应测试环境，避免资源占用泄漏。
- 需要按规则清理 `./<case_id>` 工作目录的临时文件。

## Inputs

必填：

- `case_id`
- `case_name`
- `case_result`：`success` / `fail` / `interrupt`
- `platform_env_id`
- `workspace_dir`：默认 `./<case_id>`
- `operator`

选填：

- `case_uri`：用于 CIDA 结果上报
- `status_desc`：结束态描述；不传时自动生成摘要
- `steps_for_store`：用于脚本上报的步骤集合（每步含 `step_order`、`step_description`、`checkpoint`、`tool_name`）
- `generalize_output_dir`：泛化输出目录，默认 `./<case_id>/generalized`
- `cleanup_mode`：`safe`（默认）/ `aggressive`
- `cleanup_keep`：清理时保留目录白名单，默认保留 `reports/`、`artifacts/`

## Workflow

严格按以下顺序执行，不得跳步：

1. 结果上报（END）
2. 脚本参数泛化（Phase 1）
3. 语料入库（脚本上报）
4. 环境释放（unlock）
5. 上传归档
6. 工作目录清理

### Step 1: 结果上报（核心里程碑）

先上报用例结束状态。

```bash
python .skills/result-finalizer/scripts/post_case_status.py \
  --case-id "CASE_ID" \
  --op-type "END" \
  --result "RESULT" \
  --desc "DESC"
```

如存在 `case_uri`，再上报 CIDA 结果：

```bash
python .skills/result-finalizer/scripts/post_cida_result.py \
  --case-uri "CASE_URI" \
  --result "RESULT_CODE"
```

要求：

- 上报失败要重试（建议最多 3 次，指数退避）。
- 多次失败后记录为 `report_failed`，但流程继续到后续步骤。

### Step 2: 脚本参数泛化（提取参数）

在语料入库前，先对每个修复后的步骤脚本执行参数泛化。  
统一使用 `result-finalizer/scripts/extract_playwright_params.py`，不自行实现泛化逻辑。

命令模板（推荐使用独立输出目录）：

```bash
python result-finalizer/scripts/extract_playwright_params.py \
  -i "./<case_id>/<case_id>_step<N>.py" \
  -d "./<case_id>/generalized/step_<N>" \
  -o "<case_id>_step<N>.template.py" \
  -p "<case_id>_step<N>.default_params.json"
```

默认模式（不写 `-d`）：

```bash
python result-finalizer/scripts/extract_playwright_params.py \
  -i "./<case_id>/<case_id>_step<N>.py"
```

执行要求：

- 每个待入库步骤都必须先完成一次参数泛化。
- 泛化输入脚本目录与复用脚本下载目录保持一致：统一读取 `./<case_id>/<case_id>_step<N>.py`。
- 泛化失败的步骤不得进入语料入库，需记录失败原因并在最终报告中标注。
- 记录泛化结果：`generalize_status = success|failed|partial`。
- `-d/--out-dir` 不存在时自动创建；在 `-d` 模式下，`-o/-p` 只写文件名。
- 默认不写 `-d` 时：与输入脚本同级创建 `<脚本主名>/`，输出 `converted_<主名>.py` 与 `params_<主名>.json`；若目录已有文件，先备份到 `<主名>_bak/<主名>.<时间戳>/`。
- `-d` 模式会保持目录“本次双文件”整洁：除本次 `-o/-p` 目标外，其他同级文件会在写入前迁移到 `out.bak/` 的同相对路径下（子目录不处理）。
- 若目标同名文件已存在，会先复制备份到 `out.bak/.../<原名>.bak.<时间戳>.<ext>`，再写入新文件。
- 提取完成后默认生成输入脚本同级 `<主名>_json/`：`script.jsonvalue.txt`、`params.jsonvalue.txt`；已有内容先备份到 `<主名>_json_bak/`。可用 `--skip-json-artifacts` 跳过该产物。
- 参数 JSON 使用元数据结构：`{key: {value, sensitive, kind}}`。
- 元数据规则：URL 永不自动标敏感；邮箱/账号/用户名默认不自动标敏感；键名命中密码/令牌/密钥/凭证等安全提示词，或定位链命中 `type=password` 时自动 `sensitive: true`。
- 模板脚本通过 `_params_flat_from_json` 读取每个键的 `value` 字段。
- 模板内联回退参数会将 `sensitive=true` 的 `value` 置空，避免敏感信息随模板泄露；完整值仍以参数 JSON 为准。

### Step 3: 语料入库（使用 `store_steps.py` 上报）

语料入库统一采用“脚本上报”方式，不自定义新入库脚本。  
当用户确认脚本修复无误后，对每个步骤执行一次上报。

脚本上报流程：

1. 收集脚本信息：准备脚本元数据（`case_id`、`case_name`、`step_order`、`step_description`、`checkpoint`、`tool_name`）。
2. 准备脚本内容：确认修复后的脚本文件在正确路径。
3. 收集步骤信息：`step_order`、`step_description`、`checkpoint` 必须与原始步骤描述/检查点保持一致。
4. 执行上报：先复制 `store_steps.py` 到用例工作目录并切换目录，再执行命令。

命令模板（参数内容必须使用双引号）：

```bash
python store_steps.py \
  --case_id "ID123" \
  --case_name "测试用例" \
  --step_order "1" \
  --step_description "步骤描述" \
  --checkpoint "检查点" \
  --tool_name "tool.py"
```

执行要求：

- `tool_name` 只传纯文件名，不传绝对路径；优先传泛化后模板脚本文件名（例如 `CASE_001_step1.template.py`）。
- 每个待入库步骤都要单独执行一次上报命令。
- 上报失败要记录失败步骤并继续后续步骤，最终汇总 `corpus_ingest_status = success|failed|partial`。
- 不要自己编写 `store_steps.py`，只使用项目已提供脚本。

### Step 4: 环境释放

不论前两步成功与否，都必须执行释放。可复用命令模式：

```bash
python ./skills/result-finalizer/scripts/env_manager.py \
  --action unlock \
  --platform_env_id "PLATFORM_ENV_ID"
```

要求：

- 此步骤属于 `finally` 语义，不得省略。
- 释放失败必须显式上报 `env_release_failed`，并给人工介入建议。

### Step 5: 上传归档

在报告与步骤产物都已落盘后，调用上传脚本，并将整个 `./<case_id>` 上传到文件服务器。

命令模板：

```bash
python upload.py ./<case_id>
```

执行要求：

- 上传前确认关键产物已存在（至少包含步骤目录与报告目录）。
- 上传成功后记录 `upload_status = success`，并保存返回的归档标识（如 URL、文件 ID）。
- 上传失败后记录 `upload_status = failed` 与错误信息。
- 上传失败时默认不要执行激进清理，避免证据丢失。

### Step 6: 工作目录清理

在环境释放后执行清理，避免误删关键证据。

- `safe`（默认）：
  - 清理中间临时文件（例如运行缓存、临时下载、临时 trace）。
  - 保留 `reports/` 与最终上报相关产物。
- `aggressive`：
  - 在确认产物已归档/上传后，可清理整个 `workspace_dir`。

清理前必须检查：

- 是否已有归档或上传确认。
- 是否仍需人工复盘当前目录。

## Failure Policy

失败补偿顺序固定：

1. 结果上报失败：记录并重试，超限后标记失败继续。
2. 参数泛化失败：记录并继续，失败步骤跳过入库并在最终报告中逐条列出。
3. 语料入库失败：记录并继续；失败步骤需在最终报告中逐条列出。
4. 环境释放失败：记录并告警，继续后续步骤（若后续动作依赖环境可跳过并说明）。
5. 上传归档失败：记录并告警；默认降级为 `safe` 清理或保留目录等待人工处理。
6. 工作目录清理失败：记录残留路径与处理建议。

## Output

输出分两层：

1. 过程播报：每完成一步立即输出当前状态。
2. 最终收尾报告：至少包含以下字段：

- `case_id`
- `case_result`
- `report_status`
- `generalize_status`
- `corpus_ingest_status`
- `env_release_status`
- `upload_status`
- `cleanup_status`
- `warnings`
- `next_actions`

## Constraints

- 不要重跑步骤脚本，不要修改步骤代码。
- 不要在收尾阶段执行参数还原；还原应在 `record-scripts` 第一阶段完成。
- 不要在环境未释放前做激进清理。
- 不要因为上游失败跳过环境释放。
- 不要跳过参数泛化直接入库原始硬编码脚本。
- 不要在上传归档前删除关键产物目录。
- 产物未归档时，不要删除 `reports/` 等关键证据目录。
- 不要自己写或改造 `store_steps.py`，只按现有脚本能力执行上报。

## Integration

推荐接在以下流程后：

1. `$env-preparation`
2. `$record-scripts`
3. `$fix-scripts`
4. `$checkpoint-debug-reporter`（可选）
5. `$result-finalizer`
