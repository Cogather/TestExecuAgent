---
name: playwright-script-generalizer
description: 用于 Playwright 脚本参数泛化与还原。可将硬编码脚本提取为“模板 + 默认参数 JSON”用于入库，也可基于模板和新参数恢复为可执行脚本。适用于用户要求“提取参数/脚本泛化”或“按新参数还原脚本”的场景。
---

# Playwright 脚本参数泛化

## 概述
这个 skill 处理 Playwright 录制脚本的双向流程：

1. **阶段一（泛化/提取参数）**：把硬编码脚本转换为参数化模板，并提取默认参数到 JSON 文件，便于入库和复用。
2. **阶段二（还原/实例化）**：读取已入库模板与新参数 JSON，还原为可直接执行的 Python 脚本。

## 工作流

### 阶段一：泛化（提取参数）
当用户要求“提取参数”“脚本泛化”或“准备入库模板”时：

1. **执行提取脚本**：
   ```bash
   python3 result-finalizer/scripts/extract_playwright_params.py \
     -i <input_dir/script.py> \
     -o <output_dir/template_script.py> \
     -p <output_dir/default_params.json>
   ```
2. **结果说明**：明确告知模板脚本与默认参数 JSON 已生成，可用于后续入库或复用。

### 阶段二：还原（按新参数实例化）
当用户要求“用新参数还原脚本”或“从模板生成可执行脚本”时：

1. **执行还原脚本**：
   ```bash
   python3 result-finalizer/scripts/restore_playwright_script.py \
     -t <stored_dir/template_script.py> \
     -p <new_params.json> \
     -o <executable_script.py>
   ```
2. **结果说明**：明确告知模板与新参数已合并完成，输出脚本可直接执行。

## 示例

**用户**："把 `dir1/login.py` 提取参数，存到 `dir2` 里面"  
**Agent 执行**：  
`python3 result-finalizer/scripts/extract_playwright_params.py -i dir1/login.py -o dir2/template_login.py -p dir2/default_params.json`

**用户**："用 `new_env.json` 里的参数，把 `dir2/template_login.py` 还原成可以直接执行的脚本"  
**Agent 执行**：  
`python3 result-finalizer/scripts/restore_playwright_script.py -t dir2/template_login.py -p new_env.json -o ready_to_run_login.py`
