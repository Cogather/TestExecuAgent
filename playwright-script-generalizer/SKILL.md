---
name: playwright-script-generalizer
description: >-
  从 Playwright 录制的 Python 脚本中提取参数并生成可归档的模板与默认参数 JSON（支持 -d 输出目录、自动建目录、覆盖前将旧文件备份到 out.bak/）；
  或将已保存的模板与新参数 JSON 合并，还原为可直接运行的硬编码脚本。
  在用户要求泛化脚本、提取参数、归档、还原脚本、用新参数生成可执行脚本时使用。
---

# Playwright 脚本泛化

## 概述

本技能覆盖 Playwright 录制脚本的双向流程：

1. **阶段一（泛化 / 提取）**：将写死具体值的脚本转为带 `params["键"]` 的模板；**模板与参数 JSON 放在同一目录**（推荐 `-d out/<子目录>`）。**参数 JSON 根即为参数字典**：`{"KEY": {"value": "...", "sensitive": bool, "kind": "..."}, ...}`，不含 `schema_version`、`source_script`、也不再用顶层 `parameters` 包裹（历史文件若仍含 `parameters` 键，还原时会自动解包）。**键名**从定位方式推断（placeholder / role name / label / locator 等，略）。
2. **阶段二（还原 / 实例化）**：读取模板与参数 JSON，将 `params["键"]` 替换为字面量。默认写入 **`out/restored/`**（可用 `-d` 改）；**输出文件名**：若参数 JSON 为旧版且含 `source_script` 则沿用；否则模板名为 `converted_xxx.py` 时推断为 `xxx.py`，否则与模板 basename 相同。也可用 **`-o 完整路径.py`** 指定输出。兼容旧式含 `parameters` 包裹或扁平字符串值。

## 工作流程

### 阶段一：泛化（提取参数）

当用户要求提取参数、泛化脚本或「存成模板 + 默认参数」时：

1. **运行提取脚本**（推荐每次输出到**独立目录**，便于版本与分享）：
   ```bash
   python TestExecAgent/skills/playwright-script-generalizer/scripts/extract_playwright_params.py -i <input.py> -d <输出目录> -o <模板文件名.py> -p <参数文件名.json>
   ```
   - **`-d` / `--out-dir`**：指定输出目录；**不存在则自动创建**。`-o`、`-p` 在此模式下只写**文件名**（如 `template.py`、`params.json`），实际路径为 `<输出目录>/<文件名>`。
   - **`out/` 目录**：仅保留本次 `-o` 模板与 `-p` 参数两个文件；同目录下其它文件会在写入前自动迁到 **`out.bak/`** 下同相对路径（子目录不处理）。
   - **同名文件**：若目标路径已存在，会先将旧文件复制到 **`out.bak/`**（如 `out.bak/out/sample_extract/原名.bak.时间戳.ext`），再写入新内容。
   - 若不使用 `-d`，仍可用 `-o`/`-p` 传**完整路径**（行为与以前一致）；若目标路径的父目录不存在，也会自动创建。

2. **向用户说明**：参数文件默认带 **原脚本提取出的原文**（各键的 `value`），并带 `sensitive` / `kind`（由 `param_metadata.py` 判定：**URL 不标敏感**；邮箱/账号/用户名等**不**自动标敏感；仅键名暗示密码、令牌、密钥、凭证等**安全相关**时为 `sensitive: true`，可手工改）。模板通过 `_params_flat_from_json` 读 `value`。

### 阶段二：还原（用新参数生成可执行脚本）

当用户要求还原脚本、套用新参数或从模板生成可执行文件时：

1. **运行还原脚本**（默认输出到 `out/restored/`，文件名见上文命名规则）：
   ```bash
   python TestExecAgent/skills/playwright-script-generalizer/scripts/restore_playwright_script.py -t <模板.py> -p <参数.json>
   ```
   - **`-d` / `--out-dir`**：还原目录，默认 `out/restored`。
   - **`-o` / `--output-file`**：若指定 `某路径/脚本.py`，则写入该路径（忽略 `-d` 与默认命名）。
2. **向用户说明**：生成脚本为硬编码字面量，可直接运行；新格式参数 JSON 无文件名元数据时，还原命名依赖模板名 `converted_xxx.py` → `xxx.py`，或显式 `-o`。

## 示例

**用户**：「把 dir1/login.py 提取参数，存到 dir2 里面」

**代理应执行**（独立目录 + 默认文件名示例）：
`python TestExecAgent/skills/playwright-script-generalizer/scripts/extract_playwright_params.py -i dir1/login.py -d dir2/login_extract -o template_login.py -p default_params.json`

**用户**：「用 new_env.json 还原 dir2 里的模板」

**代理应执行**（结果默认在 `out/restored/`，文件名由模板 `converted_*.py` 或旧 JSON 的 `source_script` 决定）：
`python TestExecAgent/skills/playwright-script-generalizer/scripts/restore_playwright_script.py -t dir2/converted_login.py -p new_env.json`

若需指定输出路径：加 `-o build/login_ready.py`。

### 将提取后的模板嵌入 JSON 请求体（双引号等转义）

要把 `converted_*.py` **整段作为 JSON 里某个字符串字段的值**（例如 HTTP POST 的 `pythonScript`），不能手工拼接：脚本里的 `"`、`\`、换行都必须按 JSON 规则转义。

使用辅助脚本生成**合法 JSON 字符串字面量**（输出已含外层双引号，可直接接在 `"pythonScript":` 后面）：

```bash
python TestExecAgent/skills/playwright-script-generalizer/scripts/script_to_json_string.py out/sample_extract/converted_sample_script.py
# 或写入文件
python TestExecAgent/skills/playwright-script-generalizer/scripts/script_to_json_string.py out/sample_extract/converted_sample_script.py -o script_json_value.txt
```

说明：内部使用 `json.dumps(..., ensure_ascii=False)`，双引号变为 `\"`，换行为 `\n`，反斜杠为 `\\`，中文不转 `\uXXXX`。若请求体整体仍是一个 JSON，建议用程序构造对象再序列化，避免把多段拼接搞错。接口里的 `envParams` 与提取得到的 `params_*.json` 同形：**根对象即参数字典**（无 `schema_version` / `source_script` / 外层 `parameters`）。
