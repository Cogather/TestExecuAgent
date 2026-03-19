# 脚本归属记录

本文档用于记录当前仓库中涉及的脚本文件，以及它们按新 skill 拆分后应该归属到哪个 skill。

说明：

- 这里只记录“归属关系”，不移动文件，不改脚本名，不新增脚本实现。
- `record-playwright-script` 仅保留为兼容入口，不再承担具体脚本归属。
- 归属判断以“单个 skill 只负责一类职责”为原则，优先保持现有脚本调用方式不变。

## 一、生成测试用例内容的脚本

| 脚本文件 | 应归属的 skill | 说明 |
| --- | --- | --- |
| `record-playwright-script/scripts/search_expanded_expected_result.py` | `record-case-generator` | 用于检索历史扩写记录，服务于预期结果扩写。 |
| `record-playwright-script/scripts/save_expected_result.py` | `record-case-generator` | 用于将确认后的预期结果入库，仍属于用例生成阶段。 |

## 二、录制步骤脚本的脚本

| 脚本文件 | 应归属的 skill | 说明 |
| --- | --- | --- |
| `record-playwright-script/scripts/search_similar_steps.py` | `record-step-recorder` | 用于检索相似步骤，决定复用还是重新录制。 |
| `python -m playwright codegen --ignore-https-errors [URL] -o "[case_id]/[case_id]_stepN.py"` | `record-step-recorder` | 这是录制命令，不是独立脚本文件，但属于步骤录制阶段。 |

## 三、脚本修复与回放相关的脚本

| 脚本文件 | 应归属的 skill | 说明 |
| --- | --- | --- |
| `scripts/fetch_case_steps.py` | `fix-playwright-repairer` | 用于拉取或刷新当前用例的步骤上下文，服务于脚本修复诊断。 |
| `.opencode/skills/fix-playwright-scripts/scripts/env_manager.py` | `fix-playwright-ops` | 用于环境占用与释放，属于 fix 阶段前后的运行时操作。 |
| `scripts/step_output_manager.py` | `fix-playwright-output-manager` | 用于收集步骤输出、日志和报告，属于脚本修复后的执行管理。 |
| `scripts/store_steps.py` | `fix-playwright-ops` | 用于修复完成后的脚本结果上报。 |

## 四、结果验证相关的脚本

| 脚本文件 | 应归属的 skill | 说明 |
| --- | --- | --- |
| `web-test-validator-result/scripts/env_manager.py` | `web-test-validator` | 验证前后的环境占用与释放脚本。 |
| `web-test-validator-result/scripts/post_case_status.py` | `web-test-validator` | 用于上报用例 START / END 状态。 |
| `web-test-validator-result/scripts/post_cida_result.py` | `web-test-validator` | 用于上报 CIDA 测试结果。 |

## 五、脚本参数化与还原相关的脚本

| 脚本文件 | 应归属的 skill | 说明 |
| --- | --- | --- |
| `playwright-script-generalizer/scripts/extract_playwright_params.py` | `playwright-script-generalizer` | 将 Playwright 脚本提取为模板与默认参数。 |
| `playwright-script-generalizer/scripts/restore_playwright_script.py` | `playwright-script-generalizer` | 将模板和参数还原为可执行脚本。 |

## 六、当前建议的 skill 边界

| skill | 负责的脚本类别 |
| --- | --- |
| `record-case-generator` | 用例拆解、预期结果扩写、预期结果入库相关脚本 |
| `record-step-recorder` | 相似步骤检索、步骤录制、脚本落盘相关脚本 |
| `fix-playwright-repairer` | 步骤上下文补齐、脚本修复、MCP 验证、断言补充、静态优化相关脚本 |
| `fix-playwright-output-manager` | 脚本执行、输出收集、报告生成相关脚本 |
| `fix-playwright-ops` | 环境锁定/释放、修复结果上报相关脚本 |
| `fix-playwright-scripts` | 仅作为历史兼容入口，不承载新脚本归属 |
| `bootstrap` | Python 解释器发现、根目录创建等上层编排动作 |
| `web-test-validator` | 验证判定、状态上报、结果回传相关脚本 |
| `playwright-script-generalizer` | Playwright 脚本参数提取与还原相关脚本 |
| `record-playwright-script` | 仅作为历史兼容入口，不承载新脚本归属 |

## 七、使用原则

1. 新脚本优先放入职责最单一的 skill。
2. 已有脚本如果仍被旧流程引用，可以暂时保留原路径，但归属文档以新 skill 为准。
3. 如果一个脚本同时出现在多个阶段，优先按照“谁真正消费它”来归属。
4. 不为兼容入口单独新增脚本目录，避免职责再次混叠。

## 八、长期记忆文件

| 文件 | 归属 | 说明 |
| --- | --- | --- |
| `agent-memory.yaml` | `bootstrap` | 作为长期记忆文件，保存 Python 路径、依赖检查结果和工作区上下文，不保存 `environment.platform_env_id` 或 `environment.locked`。 |
