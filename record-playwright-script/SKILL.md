---
name: record-playwright-script
description: 将测试用例拆解为多个步骤，并依次启动 Playwright codegen 为每个步骤录制单独的脚本。
---

# 录制分步 Playwright 脚本

此 skill 帮助用户将一个测试用例拆解为多个步骤，并依次启动 Playwright codegen 为每个步骤录制单独的脚本。

## 何时使用

此 skill 用于高效生成测试用例的 Web 自动化脚本。它通过智能拆解和复用机制，简化了脚本录制过程：

1.  **智能拆解**：将复杂的测试用例拆解为逻辑独立的自动化步骤。
2.  **检索复用**：自动检索已有相似脚本，支持直接复用，避免重复录制。
3.  **分步录制**：对未复用的步骤，依次启动 Playwright Codegen 引导录制。

当用户想要将手动测试用例转化为自动化脚本，且希望**复用已有资产**或**生成结构化分步脚本**时，请使用此 skill。

## 路径说明

- **Skill目录路径**：当前skill所在的目录，根据具体环境不同而不同（例如：`C:\Users\用户名\.codemate\skills` 或 `D:\projects\.codemate\skills`）
- **脚本路径**：所有辅助脚本都位于 `record-playwright-script/scripts/` 子目录下
- **使用方式**：在执行脚本时，先切换到skill目录，然后使用相对路径 `record-playwright-script/scripts/脚本名.py`

## 流程步骤

1.  **确定基础信息**：
    - **URL**：从用例中提取起始 URL。如果未提供，询问用户。
    - **用例 ID**（case_id）：如果测试用例没有则询问用户用例ID，用于创建目录区分不同测试用例的脚本。
    - **Python 解释器路径**：运行 `where python` (Windows) 或 `which python` (Mac/Linux) 查找。
    - **脚本保存规则**：
        - **目录结构**：在当前工作目录下创建 `<case_id>` 子目录（如：`./test_case_001/`）
        - **文件命名**：每个步骤的脚本文件名为 `<case_id>_step[N].py`（如：`test_case_001_step1.py`）
        - **完整路径**：`[当前工作目录]/[case_id]/[case_id]_step[N].py`

2.  **解析与拆解**：
    - 分析用户提供的测试用例，提取**测试步骤**及对应的**预期结果**。
    - **逻辑合并**：将细粒度操作及对应的预期结果合并为**逻辑上完整的自动化步骤**。
        - *操作合并原则*：将一组连续的、为了达成同一个业务目标的细碎操作（如输入、点击、选择）合并为一个步骤。**注意：合并后的步骤描述必须保留原用例中的具体操作动作（如“点击”、“输入”、“选择”等），按顺序连接，不要将其概括为抽象的业务术语（如用“登录并搜索”代替“输入用户名密码点击登录，然后输入关键字点击搜索”）。**
        - *预期结果合并原则*：
            - **最终状态优先**：合并后的预期结果应重点描述该步骤执行完后的最终页面状态或关键反馈（用于生成断言）。
            - **保持原意**：预期结果的描述应尽量保留原用例中的关键检查点，可以适当补充，但不要丢失原有的检查细节。
    - **展示拆解结果**：使用以下特定格式展示拆解后的步骤和预期结果：
        ```text
        测试ID
        [测试用例ID，如：TC_XXX_YYY_001]
        
        测试用例名称
        [测试用例名称]
        
        测试步骤
        步骤一
        [步骤一的具体描述]
        步骤二
        [步骤二的具体描述]
        
        预期结果
        预期结果一
        [预期结果一的具体描述]
        预期结果二
        [预期结果二的具体描述]
        ```
     - **保存拆解结果**：
         - 将上述拆解结果保存为一个文本文件。
         - **文件名**：`[case_id]_AI_create.txt`
         - **保存路径**：`[当前工作目录]/[case_id]/[case_id]_AI_create.txt`
     - **循环确认**：
        - 询问用户："拆解的步骤和预期结果是否符合预期？"
        - **如果不符合**：请求用户提供正确的步骤和预期结果，根据反馈调整拆解结果，并再次展示确认，直到用户回复"符合预期"。
         - **如果符合**：继续执行后续流程。

3.  **预期结果扩写**：
    - **切换到skill目录**：先切换到skill的工作目录：`cd "[skill目录路径]"`
    - **对每个预期结果进行扩写**：
         - **第一步：检索历史扩写记录**
           - 运行检索脚本：`"[python_path]" record-playwright-script/scripts/search_expanded_expected_result.py "[预期结果描述]"`
           - **解析输出**：脚本输出为 JSON 格式，包含是否找到相似记录及相似度信息。

         - **第二步：执行扩写**
           - **如果找到相似记录**（`found: true` 且相似度满足要求）：
             - 使用模型推理能力进行扩写：
               - 参考检索到的历史扩写记录，分析其扩写模式
               - 结合当前预期结果描述，生成详细的扩写内容
               - 扩写应包含：页面显示的具体内容、元素的具体状态、提示信息等细节
           - **如果未找到相似记录**：
             - 询问用户："未找到相似的历史扩写记录，请补充该预期结果的详细描述（如页面显示的具体内容、元素的具体状态、提示信息等）"
             - 等待用户输入补充的细节
             - 使用模型推理能力，基于用户提供的细节生成扩写后的预期结果

         - **第三步：展示扩写结果**
           - 向用户展示扩写前后的预期结果对比。

      - **展示完整扩写结果**：将扩写后的预期结果追加写入到之前生成的 `[case_id]_AI_create.txt` 文件中，使用以下格式：
          ```text
          
          扩写后的预期结果
          预期结果一
          [扩写后的预期结果一描述]
          预期结果二
          [扩写后的预期结果二描述]
          ```

      - **用户确认扩写结果**：
          - 询问用户："扩写后的预期结果是否符合预期？"
          - **如果符合**：继续执行后续流程。
          - **如果不符合**：
              - 请求用户提供正确的预期结果。
              - 使用用户提供的内容替换扩写结果，继续执行后续流程。

4.  **用例入库**：
       - 读取 `[当前工作目录]/[case_id]/[case_id]_AI_create.txt` 文件
       - 解析文件内容，提取测试步骤和对应的预期结果（包括原始预期结果和扩写后的预期结果）
       - 对每个步骤（按步骤序号 N，从 1 开始）：
         - 获取步骤描述、原始预期结果、扩写后的预期结果
         - 构造 metadata JSON，包含：
           ```json
           {
             "case_id": "[case_id]",
             "case_name": "[case_id]",
             "step_order": N,
             "step_description": "[步骤N的描述]",
             "checkpoint": "[原始预期结果]",
             "detailed_checkpoint": "[扩写后的预期结果]",
             "product_line_name": "云核心网产品线",
             "pdu_name": null,
             "product_id": null,
             "version_name": null,
             "feature": null
           }
           ```
         - 切换到skill目录：`cd "[skill目录路径]"`
         - 运行入库命令：
           `"[python_path]" record-playwright-script/scripts/save_expected_result.py '[metadata_json]'`
       - 检查每个步骤的入库结果，确保所有步骤都成功入库
       - 告知用户入库完成情况。

5.  **依次处理步骤（检索与录制）**：
     - 对拆解后的每个步骤 N（从 1 开始），依次执行以下流程：

     1.  **检索相似步骤**：
       - **切换到skill目录**：先切换到skill的工作目录：`cd "[skill目录路径]"`
       - 运行检索脚本：`"[python_path]" record-playwright-script/scripts/search_similar_steps.py "[步骤描述]"`
       - **解析输出**：脚本输出为 JSON 格式：`{"step_description": "...", "step_content": "..."}`。
       - **如果有相似结果**（JSON 解析成功且不为空）：
           - **展示相似步骤**：使用 Markdown 格式向用户展示检索到的信息：
               ````markdown
               **发现相似步骤**：[step_description]
                
               **脚本内容**：
               ```python
               [step_content]
               ```
               ````
           - 询问用户：“发现相似的测试步骤，是否直接复用？”
    
    2.  **分支处理**：
        - **情况 A：用户选择复用**
            - **读取与保存**：读取被复用脚本的内容，将其**保存到 case_id 目录下**，文件路径为：`[当前工作目录]/[case_id]/[case_id]_step[N].py`
            - **确认**：告知用户步骤 N 已复用成功，脚本已保存到 case_id 目录下。

        - **情况 B：未找到相似步骤 或 用户选择不复用**
            - **提示**：告知用户准备录制第 N 步："[步骤描述]"。
            - **生成文件名**：`[case_id]_step[N].py`。
            - **生成完整路径**：`[当前工作目录]/[case_id]/[case_id]_step[N].py`
            - **启动录制**：
                - 运行命令：`"[python_path]" -m playwright codegen --ignore-https-errors [URL] -o "[当前工作目录]/[case_id]/[case_id]_step[N].py"`
                 - *注意：脚本将直接保存到 case_id 目录下。如果后续步骤依赖之前的状态（如登录），用户需要在新打开的浏览器中重新进行必要的前置操作。*
             - **等待与确认**：
                 - 等待用户关闭浏览器。
                 - 询问用户："第 [N] 步录制完成，是否满意？"
                 - 如果**满意**：继续处理下一个步骤。
                 - 如果**不满意**：重新执行"启动录制"环节。

6.  **完成**：所有步骤录制完成后，汇总生成的文件列表。


## 示例

用户："帮我录制一个购物流程测试用例：1. 登录淘宝 2. 搜索 iPhone 3. 点击第一个商品 4. 查看详情 5. 添加到购物车 6. 结算"

Assistant:

**步骤 1：确定基础信息**
- URL: `https://www.taobao.com`
- 用例 ID (case_id): `TC_TAOBAO_SHOPPING_001`
- Python 解释器路径: `C:\Python39\python.exe`
- 脚本保存路径: `D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/`

**步骤 2：解析与拆解**
分析测试用例，将细粒度操作合并为逻辑完整的自动化步骤：

```text
测试ID
TC_TAOBAO_SHOPPING_001

测试用例名称
淘宝购物流程测试

测试步骤
步骤一
首先打开淘宝首页，然后在搜索框中输入 iPhone，最后点击搜索按钮

步骤二
点击搜索结果中的第一个商品，进入商品详情页

步骤三
查看商品详情，点击添加到购物车按钮，然后在购物车页面点击结算按钮

预期结果
预期结果一
搜索结果页面显示 iPhone 相关的商品列表

预期结果二
成功进入商品详情页，显示商品图片、价格、详情等信息

预期结果三
商品添加到购物车成功，结算页面显示订单信息和支付方式
```

- 已将拆解结果保存至 `D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/TC_TAOBAO_SHOPPING_001_AI_create.txt`

询问用户："拆解的步骤和预期结果是否符合预期？"
用户回复："符合预期"

**步骤 3：预期结果扩写**
切换到 skill 目录，对每个预期结果进行扩写：

**扩写预期结果一：**
- 运行检索脚本：`C:\Python39\python.exe record-playwright-script/scripts/search_expanded_expected_result.py "搜索结果页面显示 iPhone 相关的商品列表"`
- 未找到相似记录
- 询问用户补充细节
- 用户补充："搜索结果页面顶部显示搜索关键词'iPhone'，页面中间以网格布局展示商品卡片，每个卡片包含商品缩略图、标题、价格、销量等信息，底部显示分页导航"
- 生成扩写结果

**扩写预期结果二：**
- 运行检索脚本
- 找到相似记录，参考扩写模式生成扩写结果

**扩写预期结果三：**
- 运行检索脚本
- 未找到相似记录，询问用户补充细节
- 生成扩写结果

将扩写后的预期结果追加写入 `TC_TAOBAO_SHOPPING_001_AI_create.txt` 文件中：

```text

扩写后的预期结果
预期结果一
搜索结果页面顶部显示搜索关键词'iPhone'，页面中间以网格布局展示商品卡片，每个卡片包含商品缩略图、标题、价格、销量等信息，底部显示分页导航

预期结果二
[扩写后的预期结果二描述]

预期结果三
[扩写后的预期结果三描述]
```

询问用户："扩写后的预期结果是否符合预期？"
用户回复："符合预期"

**步骤 4：用例入库**
- 读取 `TC_TAOBAO_SHOPPING_001_AI_create.txt` 文件
- 解析文件内容，提取测试步骤和预期结果
- 对每个步骤构造 metadata JSON 并入库：

**步骤 1 入库：**
```json
{
  "case_id": "TC_TAOBAO_SHOPPING_001",
  "case_name": "TC_TAOBAO_SHOPPING_001",
  "step_order": 1,
  "step_description": "首先打开淘宝首页，然后在搜索框中输入 iPhone，最后点击搜索按钮",
  "checkpoint": "搜索结果页面显示 iPhone 相关的商品列表",
  "detailed_checkpoint": "搜索结果页面顶部显示搜索关键词'iPhone'，页面中间以网格布局展示商品卡片，每个卡片包含商品缩略图、标题、价格、销量等信息，底部显示分页导航",
  "product_line_name": "云核心网产品线",
  "pdu_name": null,
  "product_id": null,
  "version_name": null,
  "feature": null
}
```
运行命令：`C:\Python39\python.exe record-playwright-script/scripts/save_expected_result.py '[metadata]'`
入库成功

**步骤 2 入库：**
```json
{
  "case_id": "TC_TAOBAO_SHOPPING_001",
  "case_name": "TC_TAOBAO_SHOPPING_001",
  "step_order": 2,
  "step_description": "点击搜索结果中的第一个商品，进入商品详情页",
  "checkpoint": "成功进入商品详情页，显示商品图片、价格、详情等信息",
  "detailed_checkpoint": "[扩写后的预期结果二]",
  "product_line_name": "云核心网产品线",
  "pdu_name": null,
  "product_id": null,
  "version_name": null,
  "feature": null
}
```
运行命令：`C:\Python39\python.exe record-playwright-script/scripts/save_expected_result.py '[metadata]'`
入库成功

**步骤 3 入库：**
```json
{
  "case_id": "TC_TAOBAO_SHOPPING_001",
  "case_name": "TC_TAOBAO_SHOPPING_001",
  "step_order": 3,
  "step_description": "查看商品详情，点击添加到购物车按钮，然后在购物车页面点击结算按钮",
  "checkpoint": "商品添加到购物车成功，结算页面显示订单信息和支付方式",
  "detailed_checkpoint": "[扩写后的预期结果三]",
  "product_line_name": "云核心网产品线",
  "pdu_name": null,
  "product_id": null,
  "version_name": null,
  "feature": null
}
```
运行命令：`C:\Python39\python.exe record-playwright-script/scripts/save_expected_result.py '[metadata]'`
入库成功

告知用户：所有步骤已成功入库。

**步骤 5：依次处理步骤（检索与录制）**

**处理步骤 1：**
- 切换到 skill 目录
- 运行检索脚本：`C:\Python39\python.exe record-playwright-script/scripts/search_similar_steps.py "首先打开淘宝首页，然后在搜索框中输入 iPhone，最后点击搜索按钮"`
- 未找到相似步骤
- 提示用户准备录制第 1 步："首先打开淘宝首页，然后在搜索框中输入 iPhone，最后点击搜索按钮"
- 启动录制：`C:\Python39\python.exe -m playwright codegen --ignore-https-errors https://www.taobao.com -o "D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/TC_TAOBAO_SHOPPING_001_step1.py"`
- 用户操作并关闭浏览器
- 询问用户："第 1 步录制完成，是否满意？"
- 用户回复："满意"

**处理步骤 2：**
- 运行检索脚本：`C:\Python39\python.exe record-playwright-script/scripts/search_similar_steps.py "点击搜索结果中的第一个商品，进入商品详情页"`
- 找到相似步骤："点击搜索结果第一个商品"
- 展示相似步骤内容和脚本
- 询问用户："发现相似的测试步骤，是否直接复用？"
- 用户回复："不复用"
- 提示用户准备录制第 2 步："点击搜索结果中的第一个商品，进入商品详情页"
- 启动录制：`C:\Python39\python.exe -m playwright codegen --ignore-https-errors https://www.taobao.com -o "D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/TC_TAOBAO_SHOPPING_001_step2.py"`
- 用户操作并关闭浏览器
- 询问用户："第 2 步录制完成，是否满意？"
- 用户回复："满意"

**处理步骤 3：**
- 运行检索脚本：`C:\Python39\python.exe record-playwright-script/scripts/search_similar_steps.py "查看商品详情，点击添加到购物车按钮，然后在购物车页面点击结算按钮"`
- 未找到相似步骤
- 提示用户准备录制第 3 步："查看商品详情，点击添加到购物车按钮，然后在购物车页面点击结算按钮"
- 启动录制：`C:\Python39\python.exe -m playwright codegen --ignore-https-errors https://www.taobao.com -o "D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/TC_TAOBAO_SHOPPING_001_step3.py"`
- 用户操作并关闭浏览器
- 询问用户："第 3 步录制完成，是否满意？"
- 用户回复："满意"

**步骤 6：完成**
汇总生成的文件列表：
- `D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/TC_TAOBAO_SHOPPING_001_AI_create.txt`
- `D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/TC_TAOBAO_SHOPPING_001_step1.py`
- `D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/TC_TAOBAO_SHOPPING_001_step2.py`
- `D:/codes/test_executor/TC_TAOBAO_SHOPPING_001/TC_TAOBAO_SHOPPING_001_step3.py`

所有脚本已准备就绪，测试用例已成功入库。