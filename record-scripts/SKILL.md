---
name: record-scripts
description: 基于每步复用标识处理脚本录制，并将参数还原前置为录制阶段第一步。只对环境准备阶段已下载到复用资产的步骤执行还原；其他步骤直接录制。
---

# Record Scripts

将用例步骤转换为可执行的分步脚本，并按“先还原复用、失败再重录”的规则推进。  
参数还原属于本 skill 的第一阶段，必须先建立还原命令与产物约定，再处理逐步录制。

## 输入

开始前必须具备：

- `case_id`
- 起始 URL
- `step_reuse_flags`

可选输入（用于复用还原）：

- `./<case_id>/<case_id>_step<N>.template.py`
- `./<case_id>/<case_id>_step<N>.default_params.json`

## 输出

输出到 `./<case_id>/`：

- `<case_id>_step1.py`
- `<case_id>_step2.py`
- ...
- 步骤处理结果汇总（还原复用成功 / 还原失败后重录 / 直接录制）
- 参数还原结果汇总（`success` / `failed` / `partial`）

## 流程

### 1. 参数还原初始化（第一步，必须执行）

在开始逐步骤处理之前，还原复用步骤，再固定还原命令和输出约定。

```bash
python record-scripts/scripts/restore_playwright_script.py \
  -t "./<case_id>/<case_id>_step<N>.template.py" \
  -p "./<case_id>/<case_id>_step<N>.default_params.json" \
  -o "./<case_id>/<case_id>_step<N>.py"
```

要求：

- 还原使用 `record-scripts/scripts/restore_playwright_script.py`，不内联重写还原逻辑。
- 若模板或参数文件不存在，判定为“不可还原”，进入重录流程。
- 还原产物命名固定为 `./<case_id>/<case_id>_step<N>.py`，供后续 `fix-scripts` 直接执行。
- 还原或重录后的最终可执行脚本统一落盘到 `./<case_id>/<case_id>_step<N>.py`。

### 2. 逐步骤执行

对每一个步骤 `N`，按以下规则处理：

1. 如果 `step_reuse_flags[N] = true`：
   - 先执行还原；还原成功后进入下一步骤。
   - 若还原失败（脚本异常、输出文件缺失、关键动作缺失），立即重录该步骤并覆盖 `./<case_id>/<case_id>_stepN.py`。
2. 如果 `step_reuse_flags[N] = false`：
   - 不尝试还原，直接录制该步骤并输出到 `./<case_id>/<case_id>_stepN.py`。

### 3. 重录规则

当步骤需要重录时，运行如下命令：

```bash
python -m playwright codegen --ignore-https-errors [URL] -o "./<case_id>/<case_id>_stepN.py"
```

重录后要求：

- 让用户确认该步骤脚本是否满意。
- 不满意则继续重录当前步骤。
- 满意后再进入下一步骤。

### 4. 完成汇总

所有步骤处理完成后，输出：

- 每个步骤最终脚本路径
- 每个步骤的处理方式（还原复用成功 / 还原失败后重录 / 直接录制）
- 未处理成功的步骤（如有）

## 约束

- 必须按步骤顺序处理，不跳步。
- 还原失败只重录当前步骤，不影响已通过步骤。
- 不修改其他 skill 的输入输出契约。
- 只允许对“环境准备阶段已下载到复用资产”的步骤执行还原，不得对全量步骤强制还原。
- 不在 `record-scripts` 执行参数泛化；泛化统一在 `result-finalizer` 阶段执行。
- 不负责脚本修复、执行验证和结果判定。
