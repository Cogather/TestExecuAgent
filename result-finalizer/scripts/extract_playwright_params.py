import argparse
import copy
import json
import os
import re
import shutil
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

# 同目录工具：键名敏感性与 JSON 结构
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from param_metadata import infer_param_metadata
from script_to_json_string import file_to_json_string_literal

# Playwright ARIA role：仅出现 role、没有 name= 时，不宜单独用作业务键名
GENERIC_ROLES = frozenset({
    "textbox", "button", "link", "combobox", "checkbox", "radio", "img",
    "heading", "list", "listitem", "menu", "menuitem", "tab", "row", "cell",
    "grid", "navigation", "searchbox", "search", "dialog", "alert", "form",
    "progressbar", "scrollbar", "separator", "slider", "switch", "tree",
    "treeitem", "option", "article", "banner", "contentinfo", "main", "region",
    "section", "toolbar", "tooltip", "application",
})

FILL_TYPE_PATTERN = re.compile(
    r"(page\..+?)\.(fill|type)\(([\"'])(.*?)\3\)",
)

GOTO_PATTERN = re.compile(r"(page\.goto\()([\"'])(.*?)\2")
EXPECT_URL_PATTERN = re.compile(r"(\.to_have_url\()([\"'])(.*?)\2")


def clean_name(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"[^\w\u4e00-\u9fa5]", "_", text).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned[:80]


def extract_semantic_key_from_chain(chain: str) -> Optional[str]:
    s = chain.strip()
    if not s:
        return None
    inner = s[5:] if s.startswith("page.") else s

    m = re.search(
        r'get_by_role\s*\(\s*["\']([^"\']*)["\']\s*,\s*name\s*=\s*["\']([^"\']+)["\']',
        inner,
    )
    if m and m.group(2).strip():
        return clean_name(m.group(2)).upper() or None

    m = re.search(r'get_by_role\s*\(\s*name\s*=\s*["\']([^"\']+)["\']', inner)
    if m and m.group(1).strip():
        return clean_name(m.group(1)).upper() or None

    m = re.search(r'get_by_role\s*\(\s*["\']([^"\']+)["\']', inner)
    if m:
        role = m.group(1).strip().lower()
        if role not in GENERIC_ROLES:
            return clean_name(m.group(1)).upper() or None

    for method in (
        "get_by_placeholder",
        "get_by_label",
        "get_by_text",
        "get_by_title",
        "get_by_alt_text",
        "get_by_test_id",
    ):
        m = re.search(rf'{method}\s*\(\s*["\']([^"\']+)["\']', inner)
        if m and m.group(1).strip():
            return clean_name(m.group(1)).upper() or None

    m = re.search(r'locator\s*\(\s*["\']#([^"\']+)["\']', inner)
    if m and m.group(1).strip():
        return clean_name(m.group(1)).upper() or None

    m = re.search(r'locator\s*\(\s*["\']([^"\']+)["\']', inner)
    if m and m.group(1).strip():
        return clean_name(m.group(1)).upper() or None

    return None


def allocate_key(
    base: Optional[str],
    prefix: str,
    counter: int,
    used: Set[str],
) -> Tuple[str, int]:
    if base:
        candidate = f"{prefix}_{base}"
    else:
        candidate = f"{prefix}_{counter}"
        counter += 1

    if candidate not in used:
        used.add(candidate)
        return candidate, counter

    n = 2
    while f"{candidate}_{n}" in used:
        n += 1
    key = f"{candidate}_{n}"
    used.add(key)
    return key, counter


def _rich_params_for_template_embed(rich_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    写入模板内联 json.loads(...) 的载荷：与 rich_params 结构相同，但 sensitive=true 的 value 置空，
    避免模板单独入库或分享时携带密码等明文；完整值仍只写入 -p 参数 JSON。
    """
    out = copy.deepcopy(rich_params)
    for v in out.values():
        if isinstance(v, dict) and v.get("sensitive") is True:
            v["value"] = ""
    return out


def _generated_header_loader() -> str:
    """写入模板文件顶部的、无外部依赖的参数解析逻辑。"""
    return '''
def _params_flat_from_json(raw):
    """根对象即各参数字典；若含旧版 {"parameters": {...}} 则解包。"""
    if isinstance(raw, dict) and "parameters" in raw and isinstance(raw["parameters"], dict):
        raw = raw["parameters"]
    params = {}
    for k, v in raw.items():
        if isinstance(v, dict) and "value" in v:
            val = v["value"]
            params[k] = val if isinstance(val, str) else str(val)
        elif isinstance(v, str):
            params[k] = v
        else:
            params[k] = str(v)
    return params
'''.lstrip("\n")


def _backup_nonempty_dir_to_timestamped_subdir(
    dir_path: str,
    backup_root: str,
    archive_basename: str,
) -> None:
    """
    若 dir_path 为目录且内含条目，则将其下**所有项**整体迁入
    backup_root / f"{archive_basename}.{时间戳}[.n]" / 下（不删 dir_path 本身）。
    """
    if not os.path.isdir(dir_path):
        return
    names = os.listdir(dir_path)
    if not names:
        return
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_root, f"{archive_basename}.{stamp}")
    n = 0
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(backup_root, f"{archive_basename}.{stamp}.{n}")
    os.makedirs(dest, exist_ok=True)
    for name in names:
        shutil.move(os.path.join(dir_path, name), os.path.join(dest, name))
    print(f"已备份目录 {dir_path} 内文件至: {dest}")


def _emit_json_value_artifacts(
    template_path: str,
    params_path: str,
    input_abs: str,
    skip: bool,
) -> None:
    """与输入脚本同级：<stem>_json/ 下写入 script.jsonvalue.txt、params.jsonvalue.txt。"""
    if skip:
        return
    parent = os.path.dirname(input_abs)
    stem = os.path.splitext(os.path.basename(input_abs))[0]
    json_dir = os.path.join(parent, f"{stem}_json")
    json_bak_root = os.path.join(parent, f"{stem}_json_bak")
    _backup_nonempty_dir_to_timestamped_subdir(json_dir, json_bak_root, f"{stem}_json")
    os.makedirs(json_dir, exist_ok=True)
    tpl_lit = file_to_json_string_literal(template_path)
    par_lit = file_to_json_string_literal(params_path)
    script_out = os.path.join(json_dir, "script.jsonvalue.txt")
    params_out = os.path.join(json_dir, "params.jsonvalue.txt")
    with open(script_out, "w", encoding="utf-8") as f:
        f.write(tpl_lit)
    with open(params_out, "w", encoding="utf-8") as f:
        f.write(par_lit)
    print(f"已写入 JSON 字符串片段: {script_out}")
    print(f"已写入 JSON 字符串片段: {params_out}")


def backup_if_exists(path: str) -> Optional[str]:
    """
    若 path 为已存在文件，则复制到当前工作目录下的 out.bak/，相对路径与源文件相对 cwd 一致，避免与输出目录混杂。
    源文件不在 cwd 下时放入 out.bak/_outside/。
    """
    if not os.path.isfile(path):
        return None
    abs_path = os.path.abspath(path)
    cwd = os.path.abspath(os.getcwd())
    sep = os.sep
    if abs_path.startswith(cwd + sep):
        rel = os.path.relpath(abs_path, cwd)
        rel_dir, rel_base = os.path.split(rel)
    else:
        rel_dir = "_outside"
        rel_base = os.path.basename(abs_path)

    name, ext = os.path.splitext(rel_base)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"{name}.bak.{stamp}{ext}"
    backup_dir = os.path.join(cwd, "out.bak", rel_dir)
    backup_path = os.path.join(backup_dir, backup_name)
    n = 0
    while os.path.exists(backup_path):
        n += 1
        backup_name = f"{name}.bak.{stamp}.{n}{ext}"
        backup_path = os.path.join(backup_dir, backup_name)
    os.makedirs(backup_dir, exist_ok=True)
    shutil.copy2(abs_path, backup_path)
    return backup_path


def relocate_extraneous_output_files(output_file: str, params_file: str) -> None:
    """
    输出目录内只保留本次 -o / -p 两个文件名；其余普通文件一律迁到 out.bak/（路径镜像规则同 backup_if_exists）。
    子目录不处理。在覆盖备份之前调用。
    """
    keep = {os.path.basename(output_file), os.path.basename(params_file)}
    dirs_done: Set[str] = set()
    cwd = os.path.abspath(os.getcwd())
    sep = os.sep
    for target in (output_file, params_file):
        d = os.path.dirname(os.path.abspath(target))
        if not d or d in dirs_done:
            continue
        dirs_done.add(d)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            if name in keep:
                continue
            src = os.path.join(d, name)
            if not os.path.isfile(src):
                continue
            if src.startswith(cwd + sep):
                rel_dir = os.path.dirname(os.path.relpath(src, cwd))
            else:
                rel_dir = "_outside"
            dest_dir = os.path.join(cwd, "out.bak", rel_dir)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, name)
            n = 0
            while os.path.exists(dest):
                n += 1
                stem, ext = os.path.splitext(name)
                dest = os.path.join(dest_dir, f"{stem}.moved{n}{ext}")
            shutil.move(src, dest)
            print(f"已迁出输出目录至 out.bak: {src} -> {dest}")


def extract_and_convert(
    input_file: str,
    output_file: str,
    params_file: str,
    *,
    sibling_product_layout: bool = False,
    skip_json_artifacts: bool = False,
) -> None:
    if not os.path.exists(input_file):
        print(f"❌ 错误: 找不到输入文件 {input_file}")
        return

    input_abs = os.path.abspath(input_file)

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    ordered_keys: List[str] = []
    key_set: Set[str] = set()
    key_values: Dict[str, str] = {}
    key_chains: Dict[str, str] = {}

    def add_key(k: str, raw_value: str, chain: Optional[str] = None) -> None:
        if k not in key_set:
            key_set.add(k)
            ordered_keys.append(k)
            key_values[k] = raw_value
            if chain is not None:
                key_chains[k] = chain

    url_counter = 1
    input_counter = 1
    used_input_keys: Set[str] = set()
    out_lines: List[str] = []

    for line in lines:
        def goto_repl(match: re.Match) -> str:
            nonlocal url_counter
            url_val = match.group(3)
            try:
                parts = url_val.split("/")
                last_part = parts[-1] if parts[-1] else parts[-2]
                biz_name = clean_name(last_part).upper()
                if not biz_name:
                    biz_name = str(url_counter)
            except Exception:
                biz_name = str(url_counter)

            key = f"URL_{biz_name}"
            if key in key_set:
                key = f"URL_{biz_name}_{url_counter}"
            add_key(key, url_val)
            url_counter += 1
            return f'{match.group(1)}params["{key}"]'

        new_line = GOTO_PATTERN.sub(goto_repl, line)
        if new_line != line:
            out_lines.append(new_line)
            continue

        def expect_url_repl(match: re.Match) -> str:
            nonlocal url_counter
            url_val = match.group(3)
            try:
                parts = url_val.split("/")
                last_part = parts[-1] if parts[-1] else parts[-2]
                biz_name = clean_name(last_part).upper()
                if not biz_name:
                    biz_name = str(url_counter)
            except Exception:
                biz_name = str(url_counter)

            key = f"ASSERT_URL_{biz_name}"
            if key in key_set:
                key = f"ASSERT_URL_{biz_name}_{url_counter}"
            add_key(key, url_val)
            url_counter += 1
            return f'{match.group(1)}params["{key}"]'

        new_line = EXPECT_URL_PATTERN.sub(expect_url_repl, line)
        if new_line != line:
            out_lines.append(new_line)
            continue

        def process_fills(text: str) -> str:
            nonlocal input_counter

            def repl(m: re.Match) -> str:
                nonlocal input_counter
                chain = m.group(1)
                meth = m.group(2)
                fill_val = m.group(4)
                semantic = extract_semantic_key_from_chain(chain)
                key, input_counter = allocate_key(
                    semantic, "INPUT", input_counter, used_input_keys
                )
                add_key(key, fill_val, chain)
                return f'{chain}.{meth}(params["{key}"])'

            return FILL_TYPE_PATTERN.sub(repl, text)

        out_lines.append(process_fills(line))

    rich_params: Dict[str, Any] = {}
    for k in ordered_keys:
        meta = infer_param_metadata(k, chain=key_chains.get(k))
        meta["value"] = key_values.get(k, "")
        rich_params[k] = meta

    # 参数 JSON 仅写入「parameters 内部」的对象：无 schema_version / source_script 等顶层元数据
    out_dir = os.path.dirname(os.path.abspath(output_file))
    if sibling_product_layout:
        stem = os.path.splitext(os.path.basename(input_abs))[0]
        parent = os.path.dirname(input_abs)
        product_dir = os.path.join(parent, stem)
        bak_root = os.path.join(parent, f"{stem}_bak")
        _backup_nonempty_dir_to_timestamped_subdir(product_dir, bak_root, stem)
    if out_dir and not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    relocate_extraneous_output_files(output_file, params_file)

    b1 = backup_if_exists(output_file)
    if b1:
        print(f"已备份: {output_file} -> {b1}")
    b2 = backup_if_exists(params_file)
    if b2:
        print(f"已备份: {params_file} -> {b2}")

    params_basename = os.path.basename(params_file)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("import json\n")
        f.write("import os\n\n")
        f.write(_generated_header_loader())
        f.write("\n")
        f.write("# === 自动注入的参数加载逻辑 ===\n")
        f.write(f'PARAMS_FILE = "{params_basename}"\n')
        f.write("if os.path.exists(PARAMS_FILE):\n")
        f.write('    with open(PARAMS_FILE, "r", encoding="utf-8") as f:\n')
        f.write("        _raw = json.load(f)\n")
        f.write("    params = _params_flat_from_json(_raw)\n")
        f.write("else:\n")
        f.write(
            "    # 与 params 同结构；sensitive=true 的 value 在此为空（防入库泄露），"
            "运行需依赖 PARAMS_FILE 或自行注入\n"
        )
        _embedded = json.dumps(_rich_params_for_template_embed(rich_params), ensure_ascii=False)
        f.write(f"    _raw = json.loads({repr(_embedded)})\n")
        f.write("    params = _params_flat_from_json(_raw)\n")
        f.write("# ==============================\n\n")

        for line in out_lines:
            f.write(line)

    with open(params_file, "w", encoding="utf-8") as f:
        json.dump(rich_params, f, indent=4, ensure_ascii=False)

    _emit_json_value_artifacts(output_file, params_file, input_abs, skip_json_artifacts)

    print("脚本参数提取与转换成功！")
    print(f"提取的参数键数量: {len(ordered_keys)}（JSON 仅为参数字典：各键 value / sensitive / kind）")
    print(f"转换后的脚本已保存至: {output_file}")
    print(f"参数配置文件已保存至: {params_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Playwright 脚本参数提取与转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
默认（不写 -d）：与输入脚本同级创建 <脚本主名>/ ，写入 converted_<主名>.py 与 params_<主名>.json；
若该目录已有文件，先迁入 <主名>_bak/<主名>.时间戳/ 。并生成 <主名>_json/ 下的 JSON 字符串片段（已有则备份到 <主名>_json_bak/）。

显式 -d：仍使用原「输出目录 + 文件名」行为，多余文件迁 out.bak/；仍会生成与输入同级 <主名>_json/（除非 --skip-json-artifacts）。

示例:
  python extract_playwright_params.py -i src/login.py
  python extract_playwright_params.py -i src/login.py -d out/extract_login -o template.py -p params.json
        """.strip(),
    )
    parser.add_argument("-i", "--input", required=True, help="输入的 Playwright 录制脚本路径 (.py)")
    parser.add_argument(
        "-d",
        "--out-dir",
        default=None,
        help="指定后：产物写入该目录；-o/-p 仅取文件名放入该目录（与默认「脚本同级 <主名>/」二选一）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="模板文件名；默认不写 -d 时为 converted_<主名>.py，写 -d 时为 converted_script.py",
    )
    parser.add_argument(
        "-p",
        "--params",
        default=None,
        help="参数 JSON 文件名；默认不写 -d 时为 params_<主名>.json，写 -d 时为 params.json",
    )
    parser.add_argument(
        "--skip-json-artifacts",
        action="store_true",
        help="不生成 <主名>_json/ 下的 script.jsonvalue.txt / params.jsonvalue.txt",
    )

    args = parser.parse_args()

    inp_abs = os.path.abspath(args.input)
    parent = os.path.dirname(inp_abs)
    stem = os.path.splitext(os.path.basename(inp_abs))[0]

    if args.out_dir:
        out_dir = os.path.abspath(args.out_dir)
        os.makedirs(out_dir, exist_ok=True)
        obn = os.path.basename(args.output or "converted_script.py")
        pbn = os.path.basename(args.params or "params.json")
        output_path = os.path.join(out_dir, obn)
        params_path = os.path.join(out_dir, pbn)
        sibling_layout = False
    else:
        product_dir = os.path.join(parent, stem)
        obn = os.path.basename(args.output or f"converted_{stem}.py")
        pbn = os.path.basename(args.params or f"params_{stem}.json")
        output_path = os.path.join(product_dir, obn)
        params_path = os.path.join(product_dir, pbn)
        sibling_layout = True

    extract_and_convert(
        args.input,
        output_path,
        params_path,
        sibling_product_layout=sibling_layout,
        skip_json_artifacts=args.skip_json_artifacts,
    )
