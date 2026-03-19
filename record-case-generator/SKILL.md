---
name: record-case-generator
description: 将原始测试用例整理为标准化的用例文件，并完成步骤拆解、预期结果扩写、确认与入库准备，输出 [case_id]_AI_create.txt。
---

# Record Case Generator

**把原始测试用例加工成后续录制阶段可直接消费的标准化用例文件**。

## 适用场景

当用户提供的是原始测试用例内容，但当前目录尚未形成可确认的 `[case_id]_AI_create.txt` 时，使用本 skill。

## 需要的输入

至少需要以下信息：

1. 用例名称
2. 用例编码 `case_id`
3. 测试步骤
4. 预期结果

如用户未提供，优先补齐以下信息：

1. 起始 URL
2. 预制条件
3. 环境信息

## 输出目标

输出文件为：

`./<case_id>/<case_id>_AI_create.txt`

文件内容需保持与既有流程一致，至少包含以下结构：

```text
测试ID
[case_id]

测试用例名称
[测试用例名称]

测试步骤
步骤一
[步骤一的具体描述]

预期结果
预期结果一
[预期结果一的具体描述]
```

## 工作流程

### 1. 解析与拆解

1. 分析用户提供的测试用例，提取测试步骤与预期结果。
2. 将连续的细粒度动作合并为逻辑完整的自动化步骤。
3. 合并时保留原始动作顺序，不把步骤过度抽象成业务结论。
4. 预期结果以最终页面状态或关键反馈为主，尽量保留原意。
5. 按既有格式写入 `[case_id]_AI_create.txt`。

### 2. 用户确认

1. 展示拆解后的步骤与预期结果。
2. 询问用户：“拆解的步骤和预期结果是否符合预期？”
3. 若用户提出修改意见，则在同一份文件上修订后重新展示。
4. 直到用户确认“符合预期”为止。

### 3. 预期结果扩写

1. 切换到 skill 目录后，逐条处理每一个预期结果。
2. 对每一个预期结果，先调用历史检索脚本：

```bash
"[python_path]" record-playwright-script/scripts/search_expanded_expected_result.py "[预期结果描述]"
```

3. 解析脚本输出的 JSON 结果：
   - 若 `found: true` 且相似度满足要求，则参考历史扩写记录生成扩写内容。
   - 若未找到合适记录，则询问用户补充页面细节、元素状态、提示信息等信息。
4. 将扩写后的预期结果追加写回 `[case_id]_AI_create.txt`。
5. 将扩写前后的结果对比展示给用户。
6. 继续询问用户：“扩写后的预期结果是否符合预期？”
7. 若用户不认可，则按用户反馈替换扩写结果后继续。

### 4. 预期结果入库

如果当前项目流程需要同步落库，则在确认后读取 `[case_id]_AI_create.txt`，为每个步骤构造 metadata JSON，并调用既有入库脚本：

```bash
"[python_path]" record-playwright-script/scripts/save_expected_result.py '[metadata_json]'
```

metadata 结构保持与既有流程一致，示例如下：

```json
{
  "case_id": "[case_id]",
  "case_name": "[case_id]",
  "step_order": 1,
  "step_description": "[步骤1的描述]",
  "checkpoint": "[原始预期结果]",
  "detailed_checkpoint": "[扩写后的预期结果]",
  "product_line_name": "云核心网产品线",
  "pdu_name": null,
  "product_id": null,
  "version_name": null,
  "feature": null
}
```

## 边界说明

- 不负责 Playwright 脚本录制
- 不负责相似脚本检索
- 不负责后续脚本修复
- 不负责结果验证
- 不自行发明新的脚本名或新的文件契约

## 结束条件

当 `[case_id]_AI_create.txt` 已生成、内容已确认，并且必要的入库动作已完成后，结束本 skill。
