---
name: web-test-validator-result
version: v2 (结果判定模式)
description: 复核基于 Python Playwright 的 Web 用例步骤集。从本地用例目录读取执行结果，直接进行结果判定，不再回放脚本。其他能力保持一致，包括上报逻辑、判定逻辑和输出格式
---

# Web Test Validator

## Purpose

这个 skill 用来**验证测试用例的每一步骤的结果判定**。

它的核心职责有九件事：

1. 在测试开始前占用测试环境
2. 在用例判定开始前上报用例执行状态（START）
3. 从本地 `/<case_id>` 目录读取已执行的步骤结果文件
4. 解析每个步骤的执行产物：
    - stdout / stderr
    - exit code
    - 页面 HTML / DOM 快照
    - 下载文件
    - 截图或 trace
    - 其他日志文件
5. 判断每个 step 的执行状态（execution_status）
6. 判断每个 step 的验证状态（validation_status）
7. 在用例判定结束后上报用例执行状态（END）
8. 在用例判定结束后上报 CIDA 测试结果
9. 在测试结束后释放测试环境
10. 输出中文检查报告
默认输出分为两层：

1. **过程播报**：每个 step 判定后立刻输出当前 step 的状态、验证结论、关键 evidence 和是否继续。
2. **最终报告**：所有 step 完成后，再输出整案中文检查报告。

不要把原始日志或 JSON 字段堆砌当作主输出。

## Use When

在这些情况下使用：

- 用户提供 `case_id`，想复核该用例的执行结果
- 用例的每个步骤已经执行完成，执行产物保存在本地 `/<case_id>` 目录下
- 每个步骤的执行结果文件（stdout、stderr、exit_code、截图等）已经准备好
- 想要快速进行结果判定，不需要再次回放执行脚本

## Inputs

默认输入模型是：**用户提供 `case_id`，skill 直接读取本地 `/<case_id>` 目录下的执行结果，按步骤进行判定**。

其中：

1. 必填：`case_id`
2. 必填：`case_uri`，用例URI，用于上报CIDA测试结果。
    - 格式示例：`04130uudcn5o4q87`
    - 如果用户提供，则在 Step 14 中上报 CIDA 结果
    - 如果用户未提供，应在执行开始前询问用户，或跳过 Step 14 并记录警告
3. 必填：`platform_env_id`，平台环境ID，用于环境占用和释放。
    - 格式示例：`test-env-001`
    - 用于 Step 2 占用环境和 Step 15 释放环境
    - 必须确保该环境ID存在且可访问
4. `results_dir`，本地执行结果存储目录，默认为 `./<case_id>`
    - 该目录包含每个 step 的执行结果文件（由 fix-playwright-scripts 的 StepOutputManager 生成）
    - 目录结构示例：
      ```
      <case_id>/
        step_001/
          stdout.log
          stderr.log
          execution.json
          downloads/
            (下载的文件)
          reports/
            (截图、trace 等报告文件)
        step_002/
          stdout.log
          stderr.log
          execution.json
          downloads/
          reports/
        ...
        reports/
          overall_report.md
      ```
5. 选填：环境信息，用于辅助理解执行结果，例如：
    - 预期的 URL / 域名 / 租户地址
    - 预期的下拉选项值、枚举值
    - 登录账号、组织、产品线等环境参数
6. 选填：`operator`，操作人员工号，用于上报用例执行状态时记录操作者信息。如未提供，可在执行开始前询问用户或使用默认值。
7. 选填：`lock_reason`，环境锁定原因，默认为"测试agent占用"。
8. 选填：`expect_unlock_time`，期望环境解锁时间，默认为两天后。
## Step File Structure

每个步骤的结果目录（由 fix-playwright-scripts 的 StepOutputManager 生成）通常包含以下文件：

### 必需文件：

1. `stdout.log`：标准输出（完整内容）
2. `stderr.log`：标准错误输出
3. `execution.json`：执行日志（JSON 格式），包含：
   - `exit_code`：退出码（0 表示成功，非 0 表示失败）
   - `start_time`：开始时间戳
   - `end_time`：结束时间戳
   - `duration`：执行时长（秒）
   - `error_message`：错误信息（如果有）
   - 其他执行元数据

### 可选子目录（根据具体步骤而定）：

1. `downloads/`：下载的文件目录
   - 包含脚本执行过程中下载的文件
   - 用于验证文件上传/下载功能

2. `reports/`：报告文件目录
   - `screenshot.png`：页面截图
   - `page_snapshot.html`：页面 DOM 快照
   - `trace.zip`：Playwright trace 文件
   - 其他测试报告或日志文件

### 步骤信息推断：

skill 应从目录结构（如 `step_001`、`step_002`）和文件名推断步骤顺序和信息。

## Result Determination

结果判定必须分成两层，而且每个 step 都要单独判。

### 1. step 执行结果

基于读取到的 `execution.json`、`stdout.log`、`stderr.log` 进行判断：

**从 execution.json 解析退出码**：
- 读取 `execution.json` 中的 `exit_code` 字段
- 如果 `execution.json` 不存在或格式错误，应标记为输入不完整

- `execution_status = passed`
  条件：该 step 对应的 `execution.json` 中 `exit_code` 为 `0`，`stderr.log` 为空或只包含非阻断性警告，`stdout.log` 包含关键动作完成的证据。

- `execution_status = failed`
  条件：`execution.json` 中 `exit_code` 非 `0`、`stderr.log` 包含未捕获异常、关键动作未完成、或必需的执行产物文件缺失。

### 2. step 验证结果

基于读取到的页面快照、下载文件、截图等执行产物进行判断：

- `validation_status = passed`
  条件：该 step 所有关键结果验证检查点都通过。

- `validation_status = failed`
  条件：step 执行成功，但一个或多个关键结果验证检查点明确不通过，且失败足以否定该 step 目标。

- `validation_status = partial`
  条件：step 主流程通过，但存在次要结果验证检查点失败、证据不一致、或部分检查点无法强证实。

- `validation_status = skipped_due_to_execution_failure`
  条件：该 step 执行失败（`execution_status = failed`），导致后续结果验证无法继续判断。

详细的判定规则见：

- `references/result-rubric.md`
- `references/validation-scenarios.md`

## Workflow

### 整体流程概览

```
环境占用 → 上报START → 读取本地结果 → 逐step判定 → 上报END → 上报CIDA → 环境释放 → 最终报告
```

### 详细执行步骤（严格遵循，不得跳过）

#### 第一阶段：开始上报（第 1-3 步）

1. 收集 `case_id`、`results_dir`、`case_uri` 和用户补充的环境信息。

2. **【环境占用】占用测试环境**：调用环境管理脚本占用测试环境。
     ```bash
     python3 web-test-validator-result/scripts/env_manager.py --action lock --platform_env_id "PLATFORM_ENV_ID" --user "USER"
     ```
     ⚠️ **此步骤必须在开始测试前完成，确保测试环境可用。**
     - `<PLATFORM_ENV_ID>`：平台环境ID（必填，需从用户提供或配置中获取）
     - `<USER>`：用户标识（必填，用于记录占用者信息）
     - 可选参数：`--lock_reason`（锁定原因，默认为"测试agent占用"）
     - 可选参数：`--expect_unlock_time`（期望解锁时间，默认为两天后）
     - **如果占用失败，应终止整个流程并记录错误。**

3. **【核心里程碑】上报用例开始执行状态**：调用状态上报脚本。
     ```bash
     python3 web-test-validator-result/scripts/post_case_status.py --case-id "CASE_ID" --op-type "START" --operator "xxx"
     ```
     ⚠️ **此步骤不可跳过，必须看到"状态上报成功"的响应才能继续。**
     - `<OPERATOR>`：操作人员工号（如用户提供则使用，否则使用默认值或询问用户）
     - **如果上报失败，应终止整个流程并记录错误。**
#### 第二阶段：读取本地结果（第 4-7 步）

4. **【必须完成】检查 results_dir 目录是否存在且可访问**：
    - 确认目录路径正确
    - 确认所有必需的结果文件存在（stdout.log、stderr.log、execution.json）
    - ⚠️ **如果目录不存在或关键文件缺失，不得继续执行。**

5. **【必须完成】扫描并识别所有步骤目录**：
    - 按目录名排序识别 step 顺序（如 step_001、step_002）
    - 从目录结构推断步骤信息

6. 对每个 step 确认字段用途：操作描述、预期结果、执行产物文件。

7. 如果用户提供了环境信息，用于辅助理解执行结果和判定。

#### 第三阶段：逐 step 判定（第 8-11 步，每 step 循环判定）

⚠️ **特别说明：以下 8-11 步必须对每个 step 按顺序完整执行一遍，完成一个 step 的 8→9→10→11 后，再处理下一个 step。**

8. **完整读取执行产物**：从该 step 的结果目录读取以下信息：
    - `stdout.log`：标准输出（完整内容）
    - `stderr.log`：标准错误输出
    - `execution.json`：执行日志（包含退出码、时间戳等）
    - `downloads/` 子目录：下载的文件（如果有）
    - `reports/` 子目录：截图、trace 等报告文件（如果有）

    ⚠️ **没有完整读取这些文件之前，不得进入下一步判断。**

9. **必须判断该 step 的 `execution_status`**：基于步骤 8 读取的 `execution.json` 中的退出码和输出，判断脚本执行是否成功。
    - **`execution_status = passed`**：`execution.json` 中 `exit_code` 为 0，无阻断性异常，关键动作已真实发生。
    - **`execution_status = failed`**：`execution.json` 中 `exit_code` 非 0、未捕获异常、关键动作未完成或关键产物缺失。

    ⚠️ **必须给出明确的 passed/failed 结论，不能模棱两可。**

10. **必须判断该 step 的 `validation_status`**：基于读取到的执行产物，判断是否符合预期。
    - **`validation_status = passed`**：该 step 所有关键结果验证检查点都通过。
    - **`validation_status = failed`**：step 执行成功，但一个或多个关键检查点明确不通过。
    - **`validation_status = partial`**：主流程通过，但存在次要检查点失败。
    - **`validation_status = skipped_due_to_execution_failure`**：执行失败导致无法验证。

    ⚠️ **必须基于实际观察到的界面、文件、业务结果进行判断。**

11. **【必须完成）】即时播报当前 step 结果**：在当前 step 的 8→9→10 全部判断完成后，**立即在对话中输出**阶段性结果：
     - step 名称或编号
     - `execution_status`
     - `validation_status`
     - 关键 evidence：直接列最关键的值、URL、元素状态、文件名、文件大小、文本命中情况等
     - 简短判断依据
     - 下一步动作：继续判定下一个 step

     ⚠️ **必须完成此播报后，才能进入下一个 step 的判定。**
     ⚠️ **禁止把所有 step 都判定完后才一次性告知，必须每完成一个 step 就输出一次。**

#### 第四阶段：汇总与上报（第 12-15 步）

12. 所有 step 判定完成后，汇总 case 级执行结论和验证结论。

13. **【核心里程碑】上报用例结束执行状态**：根据整案判定结果调用状态上报脚本：
     ```bash
     python3 web-test-validator-result/scripts/post_case_status.py --case-id "CASE_ID" --op-type "END" --result "RESULT" --desc "DESC"
     ```
     - `<RESULT>`：
       - `success`：全部步骤通过
       - `fail`：存在关键步骤失败
       - `interrupt`：异常中断
     - `<DESC>`：判定结果描述，包含通过/失败的步骤数量、关键错误信息等

     ⚠️ **此步骤不可跳过，必须看到"状态上报成功"的响应。**

14. **【核心里程碑】上报 CIDA 测试结果**：根据整案判定结果调用 CIDA 结果上报脚本：
     ```bash
     python3 web-test-validator-result/scripts/post_cida_result.py --case-uri "CASE_URI" --result "RESULT"
     ```
     - `<CASE_URI>`：用例URI（必填，由用户提供）
     - `<RESULT>`：执行结果代码（必填）
       - `0`：Passed（全部步骤通过）
       - `1`：Failed（存在关键步骤失败）
       - `2`：Investigated（待调查）
       - `3`：Unavailable（不可用）
       - `4`：Blocked（被阻塞）

     ⚠️ **此步骤不可跳过，必须看到"CIDA结果上报成功"的响应。**
     ⚠️ **如果用户未提供 case_uri，应询问用户或跳过此步骤并记录警告。**

15. **【环境释放】释放测试环境**：调用环境管理脚本释放测试环境。
     ```bash
     python3 web-test-validator-result/scripts/env_manager.py --action unlock --platform_env_id "PLATFORM_ENV_ID"
     ```
     ⚠️ **此步骤必须在测试完成后执行，确保环境被正确释放。**
     - `<PLATFORM_ENV_ID>`：平台环境ID（必填，使用与Step 2相同的环境ID）
     - **如果释放失败，应记录错误但不影响其他流程。**

16. 输出中文检查报告，主视图按 step 展开，最后给整案汇总。
### 关键约束总结（必须遵守）

| 约束类型               | 说明                                                         | 违反后果                                           |
| ---------------------- | ------------------------------------------------------------ | -------------------------------------------------- |
| 不得跳过状态上报       | Step 3（START）、Step 13（END）和 Step 14（CIDA）是核心里程碑 | 流程不完整，无法追踪判定状态和测试结果             |
| 必须完成环境占用       | Step 2 必须在测试开始前成功执行                              | 环境资源可能冲突，测试结果不可靠                   |
| 必须完成环境释放       | Step 15 必须在测试结束后执行                                 | 环境资源无法释放，可能影响其他用户                 |
| 必须完整读取结果文件   | stdout.log、stderr.log、execution.json 必须完整收集          | 无法准确判断 execution_status 和 validation_status |
| 必须逐 即 step时播报   | 完成 8→9→10→11 后立即输出，再处理下一个 step                 | 违反"过程播报"要求，用户无法实时感知进度           |
| 必须按顺序执行         | 环境占用 → 上报START → 读取结果 → 循环判定step → 上报END → 上报CIDA → 环境释放 → 报告 | 流程混乱，步骤依赖关系破坏                         |
| 结果目录必须完整       | results_dir 必须存在且包含必需文件                           | 无法进行判定，应标记为输入不完整                   |
| 缺少 case_uri 时需处理 | Step 14 需要 case_uri 参数，未提供时应询问或跳过并记录警告   | 无法上报 CIDA 结果，影响测试结果追踪               |
| 必须处理子目录         | downloads/ 和 reports/ 子目录必须被扫描和验证                | 无法完整验证文件上传下载和截图等执行产物           |

## Result Determination

结果判定必须分成两层，而且每个 step 都要单独判。

### 1. step 执行结果

基于本地读取到的 `execution.json`、`stdout.log`、`stderr.log` 进行判断：

**从 execution.json 解析退出码**：
- 读取 `execution.json` 中的 `exit_code` 字段
- 如果 `execution.json` 不存在或格式错误，应标记为输入不完整

- `execution_status = passed`
  条件：该 step 对应的 `execution.json` 中 `exit_code` 为 `0`，`stderr.log` 为空或只包含非阻断性警告，且关键界面动作已经真正发生。

- `execution_status = failed`
  条件：`execution.json` 中 `exit_code` 非 `0`、`stderr.log` 包含未捕获异常、关键动作未完成、step 结果目录缺失、关键执行产物文件缺失。

执行结果判断的重点不是"有没有报错"这么简单，而是下面这些动作有没有真的发生：

- 输入框是否真的填入了预期值（从 stdout 或页面快照判断）
- 按钮是否真的被点击，并引发了预期界面变化（从 stdout 或截图判断）
- 下拉框是否真的选中了目标值
- 页面是否真的发生跳转（从 stdout 或页面快照的 URL 判断）
- 上传或下载动作是否真的触发（从文件存在性判断）
- 某一步依赖的关键元素是否真的进入预期状态

不要把"脚本自己 print 说成功了"当作执行通过的主依据，要基于实际的执行产物来判断。

### 2. step 验证结果

基于本地读取到的页面快照、下载文件、截图等执行产物进行判断：

- `validation_status = passed`
  条件：该 step 所有关键结果验证检查点都通过。

- `validation_status = failed`
  条件：step 执行成功，但一个或多个关键结果验证检查点明确不通过，且失败足以否定该 step 目标。

- `validation_status = partial`
  条件：step 主流程通过，但存在次要结果验证检查点失败、证据不一致、或部分检查点无法强证实。

- `validation_status = skipped_due_to_execution_failure`
  条件：该 step 执行失败，导致后续结果验证无法继续判断。

### 3. case 汇总结果

- 任一步 `execution_status = failed`，默认 case 执行结论记为执行失败
- 全部 step 执行通过且全部验证通过，case 验证结论记为验证通过
- 存在关键 step 验证失败，case 验证结论记为验证失败
- 主流程 step 通过，但存在次要 step 失败、跳过或证据不足，case 验证结论记为部分通过

更细的判定规则见：

- `references/result-rubric.md`
- `references/validation-scenarios.md`

## Evidence Rules

- 某个 step 的 `execution.json` 中 `exit_code` 为 0，不代表该 step 通过。
- 优先使用本地执行产物来重建证据链。
- `stdout.log`、`stderr.log`、`execution.json`、页面快照、下载文件都可以作为判断依据。
- 对执行结果，要优先看"动作是否真的完成"。
- 对输入动作，优先从 `stdout.log` 或页面快照看输入框的实际 value。
- 对点击动作，优先从 `stdout.log` 或截图看按钮状态变化、目标元素出现、弹窗出现、URL 变化、列表变化。
- 对下拉选择动作，优先从 `stdout.log` 或页面快照看 selected value 或 selected label。
- 对跳转动作，优先从 `stdout.log` 或页面快照看 URL、标题、页面主元素是否切换。
- 对上传下载动作，既要从 `stdout.log` 看动作触发，也要从 `downloads/` 子目录看产物是否真的存在。
- 对结果验证，优先分成三类：
  - 界面是否有预期变动（从 `reports/page_snapshot.html` 判断）
  - 文件是否上传/下载成功（从 `downloads/` 子目录文件存在性判断）
  - 下载报告内容是否符合预期（从 `downloads/` 子目录文件内容判断）
- 对文件内容，优先给出实际命中的文本片段。
- 如果证据字段和字段语义不一致，也要单独指出。
- 如果结果目录缺失关键文件（stdout.log、stderr.log、execution.json）或无法解析出清晰步骤，也要单独列为异常。
- skill 应从目录结构（如 step_001、step_002）推断步骤信息。

## Output

默认输出必须分成两段：**step 即时播报** 和 **最终汇总报告**。

### 1. Step 即时播报

每完成一个 step 的判定，都要先在对话中直接输出当前 step 的判定结果，再继续下一个 step。不要把所有 step 都判定完后才一次性告知。

即时播报至少应包含：

- 当前 step 编号和简短概述
- 脚本执行结论：通过 / 失败
- 结果验证结论：通过 / 失败 / 部分通过 / 因执行失败跳过
- 关键 evidence：直接列最关键的值、URL、元素状态、文件名、文件大小、文本命中情况等
- 简短判断依据
- 下一步动作：继续判定下一个 step

推荐格式如下：

```markdown
## 当前进度：Step 1

- 步骤概述：登录并进入商品列表页
- 脚本执行结论：通过
- 结果验证结论：通过
- 关键 evidence：
  - 退出：码`0`（从 execution.json）
  - 当前 URL：`https://www.saucedemo.com/inventory.html`
  - 商品列表区域可见：`true`（从 reports/page_snapshot.html 判断）
- 判断依据：脚本执行成功（execution.json 中 exit_code=0），且页面快照显示已进入 inventory 列表页
- 下一步：继续判定 Step 2
```

如果 step 执行失败，也要立刻输出失败原因和已拿到的证据；不要等到最终汇总时才说明。

### 2. 最终汇总报告

所有 step 判定完成后，再输出中文检查报告，采用**逐步骤主报告 + 用例汇总**结构：

```markdown
# Web 测试判定报告（结果判定模式）

## 用例概述
- 用例名称：<简短概述>
- case_id：<case_id>
- results_dir：<results_dir>
- step 数量：<总 step 数>
- 判定模式：<结果判定模式>
- step 解析结果：<成功 / 部分成功 / 失败>
- 执行结论：<执行通过 / 执行失败>
- 验证结论：<验证通过 / 验证失败 / 部分通过>

## 逐步骤检查结果

### Step 1：<步骤概述>
- 结果目录：<step_001/>

#### 一、脚本执行检查

1. <从 stdout.log、stderr.log、execution.json 判断的执行检查点>
   检查结果：通过
   判断依据：<最直接的事实>

#### 二、结果验证

1. <从 reports/page_snapshot.html、downloads/、reports/screenshot.png 等判断的结果验证检查点>
   检查结果：失败
   判断依据：<实际观察到的结果>
   差异说明：<预期与实际的差异>

### Step 2：<步骤概述>
- 结果目录：<step_002/>

#### 一、脚本执行检查

1. <该 step 的执行检查点>
   检查结果：通过
   判断依据：<最直接的事实>

#### 二、结果验证

1. <该 step 的结果验证检查点>
   检查结果：通过
   判断依据：<实际观察到的结果>

## 汇总差异与异常

- Step 2 结果目录缺失 execution.json，已标记为输入不完整
- Step 3 的 stderr.log 包含未捕获异常，已标记为执行失败
- Step 4 的 downloads/ 目录为空，但预期应有下载文件
- 存在未映射结果目录 `extra_step/`
```

要求：

- 每个 step 判定完成后，都要先做一次即时播报，再进入下一个 step
- 先输出 case 级概述，再按 step 逐项展开
- 每个 step 里必须先输出"脚本执行检查"，再输出"结果验证"
- 检查项顺序尽量与该 step 的描述顺序一致
- 默认主报告要包含 step 级结论和 case 级结论
- 少用抽象字段名，多用自然语言
- 默认不要把 JSON 当主报告
- 只有用户明确要求时，才附带结构化结果

## References

只在需要时读取这些文件：

- `references/result-rubric.md`
  用于标准化判断 `execution_status` 和 `validation_status`，并区分"脚本执行检查"和"结果验证"。
- `references/validation-scenarios.md`
  用于指导不同结果验证场景下应如何校验、如何判成功/失败。