---
name: record-step-recorder
description: 基于已确认的用例文件，为每个步骤检索相似脚本、决定复用或录制，并输出 [case_id]_stepN.py。
---

# Record Step Recorder

这个 skill 只负责一件事：**把已确认的标准化用例文件转换为逐步 Playwright 脚本**。

它只消费已经确认过的 `[case_id]_AI_create.txt`，不参与测试用例拆解、预期结果扩写或入库。
使用前需要具备起始 URL、Python 解释器路径和用例根目录，本 skill 不负责这些上下文的准备。

## 适用场景

当用例文件已经确认完成，并且当前工作目录需要生成每个步骤对应的 Playwright 脚本时，使用本 skill。

## 需要的输入

必须具备以下信息：

1. `case_id`
2. 起始 URL
3. 已确认的 `[case_id]_AI_create.txt`

## 输出目标

输出文件保持既有命名规则：

```text
./<case_id>/<case_id>_step1.py
./<case_id>/<case_id>_step2.py
./<case_id>/<case_id>_step3.py
```

如步骤数量更多，则继续按 `stepN` 命名并保存到同一目录下。

## 工作流程

### 1. 读取并确认输入

1. 读取 `[case_id]_AI_create.txt`，解析其中的步骤描述。
2. 确认起始 URL 可用。

### 2. 按步骤顺序处理

对每一个步骤 `N`，按顺序执行以下逻辑：

#### 2.1 检索相似步骤

先切换到 skill 目录，然后调用既有检索脚本：

```bash
"[python_path]" record-playwright-script/scripts/search_similar_steps.py "[步骤描述]"
```

脚本输出为 JSON 格式，通常包含 `step_description` 与 `step_content`。

#### 2.2 评估是否复用

1. 如果检索结果有效且可复用，则向用户展示相似步骤与脚本内容。
2. 询问用户是否直接复用。
3. 若用户确认复用，则将被复用脚本保存为：

```text
./<case_id>/<case_id>_stepN.py
```

4. 若用户不复用，或未检索到可用结果，则进入录制流程。

#### 2.3 启动录制

当需要重新录制时，按照既有方式启动 Playwright codegen：

```bash
"[python_path]" -m playwright codegen --ignore-https-errors [URL] -o "[当前工作目录]/[case_id]/[case_id]_step[N].py"
```

启动前应明确告知用户当前正在录制第 `N` 步，并提示本次录制的步骤描述。

#### 2.4 等待用户完成录制

1. 等待用户在浏览器中完成操作。
2. 等待用户关闭浏览器。
3. 录制结束后询问用户：“第 [N] 步录制完成，是否满意？”
4. 如果用户不满意，则重新进入录制流程。
5. 如果用户满意，则进入下一步骤。

### 3. 处理依赖前置状态的步骤

如果后续步骤依赖前一步的登录态或页面状态，则在新打开的浏览器中重新补齐必要前置操作，不要假设状态会自动继承。

### 4. 完成汇总

所有步骤脚本生成后，汇总输出文件清单，确认以下内容已落盘：

- `[case_id]_AI_create.txt`
- `[case_id]_step1.py`
- `[case_id]_step2.py`
- `[case_id]_step3.py`
- 以及所有其他步骤脚本

## 边界说明

- 不负责测试用例拆解
- 不负责预期结果扩写
- 不负责预期结果入库
- 不负责脚本修复
- 不负责执行验证
- 不自行新增脚本或改写既有脚本契约

## 结束条件

当所有步骤脚本都已生成并保存到 `[case_id]` 目录后，结束本 skill。
