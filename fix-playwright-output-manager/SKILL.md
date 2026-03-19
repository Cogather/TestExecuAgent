---
name: fix-playwright-output-manager
description: 负责 Playwright 脚本的批量执行、步骤输出收集、日志归档、报告生成与目录上传。
---

# Fix Playwright Output Manager

这个 skill 只负责一件事：**把待执行的脚本按步骤运行，并把执行产物按固定结构收集起来**。

它不负责修复脚本逻辑，不负责环境锁定，也不负责结果上报。
使用前需要具备用例根目录，本 skill 只在既定根目录下生成步骤输出、报告，并在结束时执行目录上传。

## 适用场景

当目录中已经存在可执行的步骤脚本，需要开始执行、收集输出并生成报告时，使用本 skill。

## 需要的输入

至少需要以下信息：

1. `case_id`
2. `[case_id]_AI_create.txt`
3. `[case_id]_stepN.py`
4. 可选的执行目录或结果目录

## 工作流程

### 1. 输出准备

1. 检查当前目录下是否存在对应的步骤脚本。
2. 确认脚本输出结构与用例目录匹配。
3. 如有需要，先清理或创建步骤输出目录。

### 2. 执行与收集

1. 按步骤执行脚本。
2. 使用既有的执行管理方式收集 stdout、stderr、execution.json、downloads 和 reports。
3. 将输出保存到对应的 `step_001`、`step_002` 等目录。

### 3. 报告汇总

1. 生成每个步骤的执行摘要。
2. 生成整体执行报告。
3. 确保输出目录中包含足够的证据供后续验证阶段读取。

### 4. 上传归档

1. 在报告与步骤产物都已落盘后，调用上传脚本。
2. 将整个 `[case_id]` 文件夹上传到文件服务器：

```bash
python upload.py ./[case_id]
```

3. 根据脚本输出判断是否上传成功

## 主要脚本契约

本 skill 只使用既有的执行与输出脚本约定，不发明新的脚本名：

```bash
python scripts/step_output_manager.py --case-id "CASE_001" --script "CASE_001_step1.py" --step-num 1
python scripts/step_output_manager.py --case-id "CASE_001" --generate-report
python upload.py ./CASE_001
```

## 边界说明

- 不负责 Playwright 脚本修复
- 不负责环境锁定与释放
- 不负责结果上报
- 不负责用例级验证判定
- 不负责脚本备份
- 不负责断言补充

## 结束条件

当所有步骤的执行产物、报告和上传归档都已完成并落盘后，结束本 skill。
