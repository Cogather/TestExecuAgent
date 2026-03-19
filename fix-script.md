---
name: fix-playwright-scripts
description: 统一循环的 Playwright 脚本调测与回放系统。自动检测当前工作目录脚本文件，采用五阶段统一流程（环境管理（可选）→脚本准备→Playwright MCP验证→循环调测与断言补充→报告汇总→环境释放（可选）），实现脚本修复与优化的闭环。
---

#  Playwright 脚本修复与回放

当用户请求修复 Playwright 脚本、处理 Codegen 生成的代码时，Skill 自动检测当前工作目录是否存在 Python 脚本文件（`*.py`），采用**五阶段统一流程**：环境管理（可选）→脚本准备→Playwright MCP验证→循环调测与断言补充→报告汇总→环境释放（可选）。该系统支持自动检测和手动指定两种场景，实现调测与回放的深度整合。

## 核心流程（五阶段统一循环）

### 零阶段：环境管理（可选）

**环境占用的作用**
确保测试环境独占使用，避免多个测试任务同时运行导致冲突。

**环境占用机制**
使用 `scripts/env_manager.py` 脚本通过命令行执行。

```bash
# 占用环境
python .opencode/skills/fix-playwright-scripts/scripts/env_manager.py \
    --action lock \
    --platform_env_id <平台环境ID> \
    --user <用户名> \
    --lock_reason "测试agent占用" \
    --expect_unlock_time "2024-01-03 10:00:00"
```

**环境释放**
```bash
# 释放环境
python .opencode/skills/fix-playwright-scripts/scripts/env_manager.py \
    --action unlock \
    --platform_env_id <平台环境ID>
```

**参数说明**
- `--action`: 必填，操作类型：`lock`（占用）或 `unlock`（释放）
- `--platform_env_id`: 必填，平台环境ID
- `--user`: 占用时必填，用户名
- `--lock_reason`: 选填，锁定原因（默认为"测试agent占用"）
- `--expect_unlock_time`: 选填，期望解锁时间（默认为两天后）

**环境管理说明**
- **可选步骤**：如果用户未提供环境ID，跳过此步骤，不影响后续流程
- **占用时机**：在脚本准备阶段之前执行
- **释放时机**：在报告汇总阶段之后执行
- **失败处理**：环境占用失败不阻断流程，记录警告并继续执行
- **资源清理**：无论流程成功或失败，最后都要尝试释放环境
- **脚本路径**：`.opencode/skills/fix-playwright-scripts/scripts/env_manager.py`
- **返回值**：脚本成功时返回0，失败时返回1

### 第一阶段：脚本准备

**触发条件自动识别**
Skill 自动检测当前工作目录中是否存在 Python 脚本文件（`*.py`）：
- **自动触发**：检测到当前工作目录存在 Python 脚本文件，自动进入修复流程
- **手动触发**：若未检测到脚本文件，提示用户提供或指定脚本文件路径

**输入来源处理**
```bash
# 输入目录结构
<case_id>/
├── [case_id]_AI_create.txt      # 包含测试用例的每一个步骤详细信息
└── [case_id]_stepN.py          # 步骤N的codegen初始脚本（N=1,2,3...）

# 自动触发场景（检测到脚本文件）
# 自动使用当前工作目录中的 Python 脚本文件
# 路径：<case_id>/

# 手动触发场景（未检测到脚本文件）
# 提示用户提供或指定脚本文件路径
```

**脚本预处理**
1. 脚本语法检查：`python -m py_compile <script.py>`
2. 依赖检查：确认 Playwright 等依赖已安装
3. 环境配置检查：验证 BASE_URL、TEST_USER 等环境变量
4. 脚本规范化：统一换行符、编码格式
5. 解析 `[case_id]_AI_create.txt` 中的测试步骤详细信息
6. 备份初始脚本到 `backup/` 目录

### 第二阶段：Playwright MCP验证（核心创新）

**基于测试步骤的MCP执行验证**
- 解析 `[case_id]_AI_create.txt` 获取测试用例的每一个步骤详细信息
- 根据**测试步骤**和**初始脚本**（`[case_id]_stepN.py`）使用 Playwright MCP 工具执行
- 将脚本中的每个操作映射到 Playwright MCP 工具（navigate、type、click、select_option 等）
- 逐步执行验证：
  1. 解析脚本中的页面操作（导航、输入、点击、选择等）
  2. 使用 Playwright MCP 工具拦截浏览器快照
  3. 根据 snapshot 确认元素位置和属性
  4. 执行 MCP 工具完成对应操作
  5. 记录每一步执行状态和异常

**验证输出**
- 记录每个操作的执行结果（成功/失败）
- 捕获实际的页面快照、日志、错误信息
- 识别脚本中不适合的元素定位（需要修复的选择器）
- 识别缺失的操作（如弹窗处理、文件上传等）
- 生成初始验证报告，为脚本修复提供依据

### 第三阶段：循环调测与断言补充（核心）

**调测循环机制**
- **最大循环次数**：3 次
- **失败处理**：第 3 次失败后停止修复，记录失败原因，询问用户是否需要手动干预
- **成功条件**：脚本无错误执行完成

**详细执行步骤**

**循环 1：基于MCP验证结果的首次修复**
1. **脚本修复**：
   - 根据第二阶段 MCP 验证结果，逐条修复已识别的问题
   - 修复范围：选择器优化、添加缺失逻辑（弹窗/下载）、调整等待时间
   - 修复时参考 MCP 快照中的实际页面结构和元素属性

2. **执行脚本**：
   - 运行 `python script.py`
   - 捕获 stdout 和 stderr 输出
   - 记录执行时间

3. **结果判断**：
   - 成功：进入断言补充阶段
   - 失败：记录错误信息，进入循环 2

**循环 2：针对执行报错的二次修复**
1. **错误分析**：
   - 超时错误：检查元素是否存在、增加超时时间
   - 选择器错误：使用 playwright_browser_snapshot 重新获取页面结构，优化选择器
   - 弹窗/对话框：添加 dialog 处理逻辑
   - 下载问题：配置 set_default_download_path
   - 其他未知错误：查看错误堆栈，定位问题代码行

2. **脚本修复**：
   - 针对性修改脚本代码
   - 如需更多信息，可再次使用 playwright_browser_snapshot 获取页面快照辅助分析

3. **执行脚本**：
   - 再次运行 `python script.py`
   - 捕获输出

4. **结果判断**：
   - 成功：进入断言补充阶段
   - 失败：记录错误信息，进入循环 3

**循环 3：最后的修复尝试**
1. **深度诊断**：
   - 获取完整错误堆栈
   - 关键代码行上下文分析
   - 必要时使用 playwright_browser_console_messages 查看浏览器控制台错误
   - 必要时使用 playwright_browser_network_requests 检查网络请求状态

2. **脚本修复**：
   - 综合所有信息进行修复
   - 如无法定位原因，询问用户页面信息或是否需要手动干预

3. **执行脚本**：
   - 最后一次运行 `python script.py`

4. **结果判断**：
   - 成功：进入断言补充阶段
   - 失败：停止修复，生成报告说明失败原因，询问用户

**断言补充阶段（修复成功后执行）**
1. **识别关键操作点**：
   - 登录/登出操作：验证 URL 变化、用户信息显示
   - 表单提交：验证提交成功提示、数据变化
   - 页面导航：验证页面标题、关键元素可见性
   - 数据操作（增删改）：验证操作结果显示
   - 文件下载：验证下载文件存在、文件名正确

2. **补充断言**：
   ```python
   # URL 变化验证
   expect(page).to_have_url(re.compile(r'dashboard'))
   
   # 元素可见性验证
   expect(page.get_by_text('欢迎回来')).to_be_visible()
   expect(page.get_by_role('heading', name='订单列表')).to_be_visible()
   
   # 下载完成验证
   with page.expect_download() as download_info:
       page.get_by_text('导出').click()
   download = download_info.value
   assert download.suggested_filename.startswith('export_')
   
   # 表单提交验证
   expect(page.get_by_text('保存成功')).to_be_visible()
   ```

3. **最终验证**：
   - 再次运行脚本，确保所有断言通过
   - 如有断言失败，进入修复循环（不计入主循环次数）

**优化代码（断言补充后）**
1. **移除硬编码等待**：
   - 检查所有 wait_for_timeout 调用
   - 分析是否可替换为 wait_for_load_state 或 wait_for_selector

2. **选择器优化**：
   - 检查是否还有复杂的 XPath 或 CSS 选择器
   - 优先使用 get_by_role、get_by_text、get_by_label

3. **代码重复提取**：
   - 提取共同的配置代码（如 context 初始化）
   - 提取公共辅助函数

4. **注释完善**：
   - 为每个关键步骤添加注释
   - 代码结构清晰易懂

## 核心工作流

遵循 **环境占用 → 备份初始脚本 → Playwright MCP验证 → 循环修复3次 → 断言补充 → 静态优化 → 输出管理 → 环境释放** 的流程：

1. **环境占用**（零阶段，可选）：
   - 检查用户是否提供环境ID
   - 如果提供，使用 `env_manager.py` 占用环境
   - 占用失败不阻断流程，记录警告

2. **备份初始脚本**（第一阶段）：将 `[case_id]_stepN.py` 复制到 `backup/` 目录

3. **Playwright MCP验证**（第二阶段）：根据 `[case_id]_AI_create.txt` 中的测试步骤和初始脚本，使用 Playwright MCP 工具执行一遍，记录问题和运行状态。

4. **循环修复3次 → 断言补充 → 静态优化 → 输出管理**

5. **环境释放**（流程结束，可选）：
   - 如果之前成功占用环境，使用 `env_manager.py` 释放环境
   - 确保资源清理
2. **循环修复3次**（第三阶段核心）：
   - **第1次**：基于MCP验证结果修复（选择器、弹窗、下载逻辑等）
   - **第2次**：基于执行报错修复（针对性解决运行时错误）
   - **第3次**：深度诊断修复（查看控制台、网络请求等）
   - 每次修复后执行 `python script.py` 验证
   - 第3次失败后停止并询问用户
3. **断言补充**（第三阶段）：为关键操作点添加断言验证（URL、元素、下载等）
4. **静态优化**（第三阶段）：移除硬编码等待、优化选择器、提取重复代码
5. **输出管理**：使用 `step_output_manager.py` 保存执行日志和文件

### 第四阶段：脚本上报与结果输出

## 脚本上报流程

当用户确认脚本修复无误后，需要调用 `scripts/store_steps.py` 脚本上报修复后的脚本。

### 上报步骤

1. **收集脚本信息**：准备包含脚本元数据的数据结构
2. **准备脚本内容**：确保修复后的脚本文件在正确路径
3. **收集步骤信息**，包括步骤order，步骤描述，步骤checkpoint，需要和原始步骤描述/checkpoint保持一致
4. **执行上报**：先复制脚本store_steps.py到并cd到用例工作目录，再通过 `python store_steps.py --case_id "ID123" --case_name "测试用例" --step_order 1 --step_description "步骤描述" --checkpoint "检查点" --tool_name "tool.py"(纯文件)` 命令上报,注意参数内容要用双引号

### 结果输出

使用step_output_manager.py对每个步骤生成结果输出，各个步骤依次执行
## step_output_manager.py 使用说明

`step_output_manager.py` 是一个用于管理 Playwright 脚本修复过程中每个步骤输出的工具脚本，可以自动创建目录结构、保存日志、收集下载文件和报告文件，并生成整体执行报告。

### 命令行调用方式

#### 1. 执行指定步骤并记录输出

```bash
python scripts/step_output_manager.py \
    --case-id "CASE_001" \
    --script "CASE_001_step1.py" \
    --step-num 1
```

参数说明：
- `--case-id`：必填，用例ID
- `--script`：必填，要执行的脚本文件路径
- `--step-num`：必填，步骤编号（1、2、3...）

执行后会自动创建以下目录结构：
```
CASE_001/
├── step_001/
│   ├── stdout.log          # 标准输出日志
│   ├── stderr.log          # 错误输出日志
│   ├── execution.json      # 执行日志（JSON格式）
│   ├── downloads/          # 下载的文件（如果有）
│   └── reports/            # 报告文件（如果有）
├── logs/                   # 全局执行日志
└── reports/                # 全局执行报告
```

#### 2. 列出所有步骤的执行摘要

```bash
python scripts/step_output_manager.py \
    --case-id "CASE_001" \
    --list-steps
```

#### 3. 生成整体执行报告

```bash
python scripts/step_output_manager.py \
    --case-id "CASE_001" \
    --generate-report
```

报告将保存到 `CASE_001/reports/overall_report.md`，包含：
- 用例概述（总步骤数、成功/失败步骤）
- 逐步骤执行情况（状态、返回码、执行时长、文件数量）
- 各步骤输出目录路径



### 使用场景

1. **脚本修复后执行**：在脚本修复完成后，使用 `step_output_manager.py` 执行脚本并记录输出
2. **逐步骤执行**：对每个步骤单独执行并记录输出，便于问题定位
3. **报告汇总**：自动生成包含所有步骤执行情况的整体报告
4. **输出统一管理**：将日志、下载文件、报告文件统一保存到结构化目录中


### 第五阶段：环境释放（可选）

根据零阶段的环境占用情况，执行环境释放：
- 如果之前成功占用环境，使用 `env_manager.py` 释放环境
- 确保资源清理，无论流程成功或失败
- 释放环境失败不影响报告生成

**第三阶段：循环调测与断言补充**
- 根据 MCP 验证结果进行首次脚本修复（循环1）
- 修复后的脚本覆盖原文件 `[case_id]_stepN.py`
- 执行脚本并记录错误
- 针对性修复执行错误（最多3次循环）
- 修复成功后进行断言补充和代码优化
- 记录修复历史和日志


## 运行命令

```bash
# 普通 Python 脚本
python 脚本路径.py
```

## 常见报错与修复方向

| 报错类型 / 关键词                     | 修复方向                                                |
| ------------------------------------- | ------------------------------------------------------- |
| `TimeoutError` / `Timeout`            | 增加 `timeout`、改用 `wait_for`、检查选择器是否匹配     |
| `Locator resolved to` / `strict mode` | 选择器匹配到多个元素，加 `.first` 或收紧选择器          |
| `No node found` / `Unable to find`    | 选择器失效，改用语义化选择器或检查页面结构              |
| `dialog` / `Dialog`                   | 补充 `page.on('dialog', ...)` 监听                      |
| `download` / `Download`               | 补充 `set_default_download_path` 或 `expect_download`   |
| `Target closed`                       | 页面/浏览器过早关闭，检查关闭顺序或等待逻辑             |
| `ModuleNotFoundError`                 | 安装依赖 `pip install playwright && playwright install` |

---


## 代码优化策略

### 1. 初始化配置 (Context Setup)

创建 Context 时禁用权限（防弹窗干扰）并忽略 HTTPS 错误。

```python
context = browser.new_context(
    ignore_https_errors=True,
    permissions=[]  # 禁止地理位置、通知等弹窗
)
```

### 2. 强化选择器与注释 (Selectors & Comments)

- **注释**：结合测试步骤为关键代码块添加注释。
- **选择器**：将 CSS/XPath 替换为语义化定位器。

```python
# 步骤 1: 登录系统
page.get_by_role("button", name="提交").click()
```

### 3. 优化等待逻辑 (Waits)

在页面跳转、弹窗、下载导出等关键操作前，适当增加等待以确保稳定性。

```python
# ❌ 避免无意义的长等待
time.sleep(10)

# ✅ 推荐：事件驱动等待
page.wait_for_load_state("networkidle")
# 特殊场景：在不稳定操作前短暂等待加载
page.wait_for_timeout(2000) 
```

### 4. 文件上传与下载 (Uploads & Downloads)

**文件上传:**
优先使用 `set_input_files`。若元素非 Input 类型（如 Span/Button），需配合 `expect_file_chooser`。

```python
# 方式 1: 直接设置（推荐）
page.get_by_label("上传文件").set_input_files("file.txt")

# 方式 2: 监听文件选择器（处理非 Input 触发）
with page.expect_file_chooser() as fc_info:
    page.get_by_text("点击上传").click()
file_chooser = fc_info.value
file_chooser.set_files("file.txt")
```

**文件下载:**
必须显式配置下载路径到**当前工作目录**。

```python
# 全局配置
context = browser.new_context(accept_downloads=True)

# 局部配置（操作前）
page.context.set_default_download_path(os.getcwd())
```

### 5. 补充断言 (Assertions)

Codegen 代码通常缺少断言，必须补充。

```python
# 动作
page.get_by_role("button", name="登录").click()

# 验证
expect(page).to_have_url(re.compile("dashboard"))
expect(page.get_by_text("欢迎回来")).to_be_visible()
```

## 修复检查清单

完成修复后逐项确认：

- [ ] MCP验证已完成并记录问题清单
- [ ] 修复循环已完成（最多3次）
- [ ] 脚本可以成功执行无报错
- [ ] 无 `wait_for_timeout` 或已替换为事件等待
- [ ] 存在弹窗时，已补充 `page.on('dialog')` 或关闭按钮/ESC 等关闭逻辑
- [ ] 无 `xpath=` 或复杂 CSS（如 `nth-child` 链），优先语义化选择器
- [ ] 关键操作点已补充 `expect` 断言
- [ ] URL、账号等敏感/环境相关数据已参数化
- [ ] 重复代码已提取
- [ ] 涉及文件下载时，已设置 `set_default_download_path` 到工作目录
- [ ] 执行日志已保存到对应步骤目录
- [ ] 执行报告已生成



## 输出管理

### 目录结构

**输入目录结构**
```
<case_id>/
├── [case_id]_AI_create.txt      # 包含测试用例的每一个步骤详细信息
└── [case_id]_stepN.py          # 步骤N的codegen初始脚本（N=1,2,3...）
```

**输出目录结构（修复后）**
```
<case_id>/
├── [case_id]_AI_create.txt      # 测试用例详细信息（保留）
├── [case_id]_stepN.py          # 修复后的脚本文件（覆盖原文件）
├── step_001/                # 步骤1的输出目录
│   ├── stdout.log          # 标准输出日志
│   ├── stderr.log          # 错误输出日志
│   ├── execution.json      # 执行日志（JSON格式）
│   ├── downloads/          # 下载的文件
│   └── reports/            # 步骤报告文件
├── step_002/                # 步骤2的输出目录
│   ├── stdout.log
│   ├── stderr.log
│   ├── execution.json
│   ├── downloads/
│   └── reports/
├── step_003/                # 步骤3的输出目录
│   └── ...
├── logs/                    # 全局执行日志
├── reports/                 # 全局执行报告（包括整体报告）
└── backup/                  # 初始脚本备份
    └── [case_id]_stepN.py  # 原始codegen脚本备份（N=1,2,3...）
```


**Playwright MCP工具映射参考**

```text
脚本操作                    → Playwright MCP工具
page.goto(url)            → playwright_browser_navigate
locator.fill(text)        → playwright_browser_type
locator.click()           → playwright_browser_click
locator.select_option()   → playwright_browser_select_option
page.screenshot()         → playwright_browser_take_screenshot
page.wait_for_timeout()   → playwright_browser_wait_for
page.wait_for_load_state()  → playwright_browser_evaluate
```

### 报告格式

**执行报告（Markdown）**
```markdown
# Playwright 脚本调测与修复报告

## 用例概述
- 用例ID: CASE_001
- 触发模式: 自动检测（检测到脚本文件）
- 总步骤数: 1（单个脚本文件）
- 测试步骤数: 5
- 执行时间: 2024-01-01 10:00:00

## MCP验证情况

### 初始MCP验证结果
- 验证开始时间: 2024-01-01 10:00:00
- 快照捕获数量: 8
- 发现问题数: 3
- MCP验证通过: 否

### 识别的问题清单
1. 第4行: 选择器 `#submit-btn` 无法定位唯一元素（页面存在2个匹配）
2. 第8行: 缺少弹窗处理逻辑
3. 第12行: 超时时间过短（当前2000ms，页面加载需要5000ms+）

### MCP修复方案
- 第4行: 使用 `page.get_by_role('button', name='提交')` 替换原选择器
- 第8行: 添加 `page.on('dialog', lambda dialog: dialog.accept())`
- 第12行: 超时调整为 `page.wait_for_selector('...', timeout=10000)`

## 修复循环历史

### 第1次修复（基于MCP验证）
- 修复时间: 2024-01-01 10:00:30
- 修复内容:
  - 第4行: 选择器优化（ID → get_by_role）
  - 第8行: 添加弹窗处理
  - 第12行: 超时时间调整
- 执行结果: ❌ 失败（TimeoutError）
- 错误信息: 第14行元素定位超时

### 第2次修复（基于执行报错）
- 修复时间: 2024-01-01 10:01:15
- 错误诊断: 使用 playwright_browser_snapshot 获取页面结构，发现元素因动画延迟显示
- 修复内容: 第14行前添加 `page.wait_for_load_state('networkidle')`
- 执行结果: ✅ 成功

## 逐步骤执行情况

### 测试步骤 2: 输入用户名
- 脚本行号: 4-5
- 状态: ✅ 成功
- MCP验证发现: 0个问题
- 断言补充: ✅ 已补充输入值验证

### 测试步骤 3: 输入密码
- 脚本行号: 6-7
- 状态: ✅ 成功
- MCP验证发现: 0个问题
- 断言补充: ✅ 已补充输入值验证

### 测试步骤 4: 点击登录按钮
- 脚本行号: 8
- 状态: ✅ 成功（第1次修复后）
- MCP验证发现: 1个问题（选择器不唯一）
- 修复方案: 使用 get_by_role('button', name='提交')
- 修复循环: 第1次
- 断言补充: ✅ 已补充点击后验证

### 测试步骤 5: 验证登录成功
- 脚本行号: 9-15
- 状态: ✅ 成功（第2次修复后）
- MCP验证发现: 1个问题（弹窗）
- 修复方案: 第8行添加 dialog 处理，第12行增加超时，第14行前添加 networkidle 等待
- 修复循环: 第1次（dialog/超时）、第2次（networkidle）
- 断言补充: ✅ 已补充 URL 变化和用户信息元素验证

## 修复历史
1. 第1次修复（基于MCP验证）：使用 get_by_role 替换 ID 选择器
2. 第2次修复（执行报错）：增加超时时间到 60000ms
3. 第3次修复（深度诊断）：添加 page.wait_for_load_state('networkidle') 确保页面加载完成
4. 断言补充：添加 URL、元素可见性、下载完成验证

## 断言补充记录
- 测试步骤 1: 添加 `expect(page.get_by_role('heading', name='登录')).to_be_visible()`
- 测试步骤 2: 添加 `expect(page.get_by_placeholder('请输入用户名')).to_have_value(username)`
- 测试步骤 3: 添加 `expect(page.get_by_placeholder('请输入密码')).to_have_value('********')`
- 测试步骤 4: 添加 `expect(page.get_by_text('登录中...')).to_be_visible()`
- 测试步骤 5: 添加 `expect(page).to_have_url(re.compile(r'dashboard'))` 和 `expect(page.get_by_text('欢迎回来')).to_be_visible()`

## 结果汇总
- 总测试步骤数: 5
- 成功步骤: 5
- 失败步骤: 0
- 总修复循环次数: 2（第1次基于MCP验证，第2次基于执行报错）
- 断言补充数量: 5
- 代码优化项: 3（移除硬等待、优化选择器、添加networkidle等待）
- MCP验证截图数量: 8
- 执行总耗时: 90秒
```

### 环境预检（整合在第一阶段）

在脚本准备阶段进行环境检查：

```bash
where python  # 或 which python3
python -c "from playwright.sync_api import sync_playwright"
```

⚠️ **如果不通过，不得继续执行，并标记为环境阻断。**

### 数据获取（整合在各阶段）

**自动检测模式**
- 检测当前工作目录是否存在 Python 脚本文件（`*.py`）
- 若存在，直接使用本地脚本文件，路径：`<case_id>/`
- 若不存在，提示用户提供或指定脚本文件路径

### 执行与验证（整合在第二/三阶段）

**第二阶段：Playwright MCP验证（新增）**
1. 使用 Playwright MCP 工具根据 `[case_id]_AI_create.txt` 中的测试步骤和初始脚本执行一遍
2. 使用 playwright_browser_snapshot 获取页面快照
3. 根据快照找到元素位置并执行实际操作
4. 记录每个步骤执行状态、快照、错误信息
5. 生成MCP验证报告，识别需要修复的问题
6. MCP工具映射：
   - navigate → playwright_browser_navigate
   - type/fill → playwright_browser_type
   - click → playwright_browser_click
   - select_option → playwright_browser_select_option
   - 等待 → playwright_browser_wait_for
   - 其他复杂操作 → playwright_browser_run_code

**第三阶段：循环调测与断言补充**
- 根据 MCP 验证结果进行首次脚本修复（循环1）
- 修复后的脚本覆盖原文件 `[case_id]_stepN.py`
- 执行脚本并记录错误
- 针对性修复执行错误（最多3次循环）
- 修复成功后进行断言补充和代码优化
- 记录修复历史和日志

## 运行命令

### 完整流程执行

**自动检测流程**
1. 检测当前工作目录是否存在 Python 脚本文件（`*.py`）
2. 若存在，自动使用本地脚本文件，按照三阶段流程依次执行
3. 若不存在，提示用户提供或指定脚本文件路径
4. 通过自然语言描述指导每个步骤的执行

### 分阶段执行指导

**第一阶段：脚本准备**
- 自动检测当前工作目录是否存在 Python 脚本文件（`*.py`）
- 检查是否存在 `[case_id]_AI_create.txt` 测试用例详情文件
- 若存在，直接使用本地脚本文件；若不存在，提示用户提供脚本路径
- 备份初始脚本到 `backup/` 目录
- 执行脚本预处理（语法检查、依赖检查、环境配置检查、脚本规范化）
- 解析 `[case_id]_AI_create.txt` 中的测试步骤详细信息

**第二阶段：Playwright MCP验证**
- 解析用户提供的测试步骤和初始脚本
- 将脚本操作映射到 Playwright MCP 工具
- 使用 MCP 工具逐步执行并捕获页面快照
- 识别元素定位问题、缺失的弹窗处理等
- 生成初始MCP验证报告

**第三阶段：循环调测与断言补充**
- 循环1（基于MCP验证）：修复选择器、弹窗、下载等逻辑，执行脚本
- 循环2（基于执行报错）：针对运行时错误修复，执行脚本
- 循环3（深度诊断）：使用console/network等工具深度修复，执行脚本
- 修复成功后进行断言补充和代码优化
- 如3次循环均失败，停止并询问用户

**第二阶段：Playwright MCP验证**
- 解析用户提供的测试步骤和初始脚本
- 将脚本操作映射到 Playwright MCP 工具
- 使用 MCP 工具逐步执行并捕获页面快照
- 识别元素定位问题、缺失的弹窗处理等
- 生成初始MCP验证报告

**第三阶段：循环调测与断言补充**
- 根据 MCP 验证结果进行首次脚本修复（循环1）
- 执行脚本并记录错误
- 针对性修复执行错误（最多3次循环，第3次失败后停止并询问用户）
- 修复成功后进行断言补充和代码优化

**第四阶段：报告汇总**
- 生成中文执行报告（Markdown 格式）
- 汇总MCP验证情况、修复历史、断言补充记录、执行结果
- 包含MCP执行快照和问题识别记录

## 输入参数

### 必填参数
- `case_id`：用例ID

### 选填参数
- `max_retry`：最大重试次数（默认 3）
- `env_id`：平台环境ID（用于环境占用/释放，选填）
- `user`：用户名（占用环境时必填）
- `env_config`：环境配置（JSON 格式）
  - `BASE_URL`：基础 URL
  - `TEST_USER`：测试用户名
  - `TEST_PASS`：测试密码
  - 其他环境变量

### 自动检测逻辑
Skill 启动时自动检测当前工作目录（`<case_id>/`）：
- 若检测到 Python 脚本文件（`*.py`），自动进入修复流程
- 若未检测到脚本文件，提示用户提供或指定脚本文件路径

## 触发条件与输入来源

### 自动检测（检测到脚本文件）

**触发条件**
- Skill 启动时检测到当前工作目录（`<case_id>/`）存在 Python 脚本文件（`*.py`）

**输入来源**
- 直接使用当前工作目录中的脚本文件
- 路径：`<case_id>/`

### 手动指定（未检测到脚本文件）

**触发条件**
- Skill 启动时未检测到当前工作目录存在 Python 脚本文件

**输入来源**
- 提示用户提供或指定脚本文件路径

## 关键约束总结

| 约束类型          | 说明                                     | 违反后果               |
| ----------------- | ---------------------------------------- | ---------------------- |
| MCP验证必须先执行 | 脚本修复必须先基于MCP工具验证            | 无法准确识别定位问题   |
| 最大调测循环次数  | 最多 3 次循环，第3次失败后停止并询问用户 | 避免无限循环，提高效率 |
| 环境预检必须通过  | Python、Playwright 依赖必须可用          | 后续步骤无法执行       |
| 断言补充必须完整  | 修复成功后必须为关键操作点补充断言       | 确保测试覆盖率和可靠性 |
| 报告汇总必须准确  | 修复历史、MCP验证和断言补充记录必须准确  | 影响结果分析           |
## 详细参考

更多选择器转换规则和边界情况见 `reference.md`。