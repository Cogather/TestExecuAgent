---
name: playwright-script-generalizer
description: >-
  从 Playwright 录制的 Python 脚本中提取参数并生成模板与参数 JSON；默认产物与输入脚本同级（<主名>/ 与 <主名>_json/），
  支持目录级备份（<主名>_bak/、<主名>_json_bak/）；可选 -d 指定其它输出目录。提取完成后自动生成可嵌入 API 的 JSON 字符串片段。
  或将模板与新参数 JSON 还原为硬编码脚本。在用户要求泛化、提取参数、归档、还原、或生成 JSON 嵌入片段时使用。
---

# Playwright 脚本泛化

## 概述

1. **阶段一（泛化 / 提取）**：将写死具体值的脚本转为带 `params["键"]` 的模板。**默认不写 `-d` 时**：与输入 `.py` **同级**创建 **`<脚本主名>/`**，在其中写入 **`converted_<主名>.py`** 与 **`params_<主名>.json`**（不再使用 `out/子目录` 作为默认位置）。若 **`<主名>/` 已存在且有内容**，会先将其中**所有文件**迁入 **`<主名>_bak/<主名>.时间戳/`** 再写入本次产物。**参数 JSON** 含完整 `value`；**模板内嵌回退**中 `sensitive: true` 的 `value` 为空，防入库泄露。提取结束后**自动**在与脚本同级生成 **`<主名>_json/`**，内含 **`script.jsonvalue.txt`**、**`params.jsonvalue.txt`**（整文件经 `json.dumps` 后的合法 JSON 字符串字面量，可直接作 API 里字符串字段值）；若该目录已存在且有内容，先备份到 **`<主名>_json_bak/<主名>_json.时间戳/`**。
2. **仍可使用 `-d 输出目录`**：模板与参数只写入该目录（`-o`/`-p` 仅文件名），行为与旧版一致（多余文件迁 `out.bak/` 等）；**JSON 字符串产物仍写在输入脚本同级的 `<主名>_json/`**（除非加 **`--skip-json-artifacts`**）。
3. **阶段二（还原）**：读取模板与参数 JSON，将 `params["键"]` 替换为字面量；默认 **`out/restored/`**，可用 **`-d`/`-o`** 调整。

## 工作流程

**脚本路径约定**：`extract_playwright_params.py`、`restore_playwright_script.py`、`script_to_json_string.py` 与 `param_metadata.py` 位于**同一目录**（与本 SKILL 同属该技能包）。执行时使用指向这些脚本的相对或绝对路径；**文档示例不写 `.cursor/`**，便于拷贝到其它环境。

### 阶段一：泛化（提取参数）

当用户要求提取参数、泛化脚本或「存成模板 + 默认参数」时：

1. **推荐命令（默认布局，与脚本同级）**：
   ```bash
   python extract_playwright_params.py -i <录制脚本.py>
   ```
   - 产物目录：`<录制脚本所在目录>/<脚本主名>/`  
     - `converted_<主名>.py`、`params_<主名>.json`
   - 备份：若上述目录已有文件 → **`<主名>_bak/<主名>.YYYYMMDD_HHMMSS[/序号]/`**
   - JSON 嵌入片段：**`<主名>_json/script.jsonvalue.txt`**、**`params.jsonvalue.txt`**
   - JSON 目录备份：若 **`<主名>_json/`** 已有文件 → **`<主名>_json_bak/<主名>_json.时间戳[/序号]/`**
   - **`--skip-json-artifacts`**：跳过生成 `<主名>_json/`（仍可做模板与参数提取）。

2. **指定其它输出目录（与旧版一致）**：
   ```bash
   python extract_playwright_params.py -i <录制脚本.py> -d <输出目录> -o <模板.py> -p <参数.json>
   ```
   - **`-d`**：目录不存在会创建；`-o`/`-p` 在此模式下只写**文件名**。
   - 单文件覆盖前仍可能备份到 **`out.bak/`**；输出目录内多余文件会迁到 **`out.bak/`**（规则同前）。

3. **向用户说明**：`sensitive` / `kind` 由 `param_metadata.py` 推断（URL 不标敏感；密码 / `type=password` 定位链等标敏感，可手工改 JSON）。生产运行依赖 **`params_*.json`** 或等价注入以提供敏感值。

### 阶段二：还原（用新参数生成可执行脚本）

```bash
python restore_playwright_script.py -t <模板.py> -p <参数.json>
```

- **`-d`**：还原目录，默认 `out/restored`。
- **`-o`**：指定输出 `.py` 完整路径时忽略默认命名。

模板路径示例（默认提取后）：`<录制脚本同级>/<主名>/converted_<主名>.py`，参数：同目录 `params_<主名>.json`。

## 示例

**用户**：「把 `dir1/login.py` 泛化一下」

**代理应执行**：

`python extract_playwright_params.py -i dir1/login.py`

→ `dir1/login/converted_login.py`、`dir1/login/params_login.json`，以及 `dir1/login_json/` 下两个 `.jsonvalue.txt`（如有旧目录会先备份到 `login_bak/`、`login_json_bak/`）。

**用户**：「用 `new_env.json` 还原 `dir1/login/converted_login.py`」

**代理应执行**：

`python restore_playwright_script.py -t dir1/login/converted_login.py -p new_env.json`

（或 `-o` 指定输出路径。）

### 单独将某文件转为 JSON 字符串值

若只需转换、不跑完整提取：

```bash
python script_to_json_string.py path/to/converted_sample_script.py
python script_to_json_string.py path/to/converted_sample_script.py -o embedded.txt
```

提取流程已默认生成 `script.jsonvalue.txt` / `params.jsonvalue.txt`，一般无需再手工调用。

说明：内部使用 `json.dumps(..., ensure_ascii=False)`。接口里的 `envParams` 与 `params_*.json` 同形：**根对象即参数字典**（无 `schema_version` / `source_script` / 外层 `parameters`）。
