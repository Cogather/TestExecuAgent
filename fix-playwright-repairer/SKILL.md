---
name: fix-playwright-repairer
description: 负责 Playwright 脚本的诊断、循环修复、断言补充与静态优化。
---

# Fix Playwright Repairer

这个 skill 只负责一件事：**把已有的 Playwright 脚本修复到可稳定执行的状态**。

它聚焦于脚本内容本身，不负责环境占用、脚本输出管理或修复结果上报。

## 适用场景

当脚本存在选择器不稳、等待不合理、断言缺失、弹窗处理不完整或其他执行问题时，使用本 skill。

## 需要的输入

至少需要以下信息：

1. `case_id`
2. 已确认的 `[case_id]_AI_create.txt`
3. 待修复的 `[case_id]_stepN.py`

## 工作流程

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

## 边界说明

- 不负责环境锁定与释放
- 不负责脚本执行与输出收集
- 不负责脚本修复结果上报
- 不改写 `[case_id]_AI_create.txt`

## 结束条件

当脚本已修复到可交付执行、且关键断言与静态结构已经稳定时，结束本 skill。
