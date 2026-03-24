import argparse
import json
import os
import re
import sys
from typing import Optional

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from param_metadata import (
    get_source_script_basename,
    load_params_map_for_restore,
    resolve_value_for_restore,
)

_INJECTED_BLOCK_END_MARKER = "# =============================="


def strip_injected_header(content: str) -> str:
    """去掉 extract 注入块；用 str.find 避免正则在大段 json.loads 上灾难性回溯。"""
    if not content or not content.startswith("import json"):
        return content
    marker_at = content.find(_INJECTED_BLOCK_END_MARKER)
    if marker_at < 0:
        return content
    after = marker_at + len(_INJECTED_BLOCK_END_MARKER)
    n = len(content)
    while after < n:
        ch = content[after]
        if ch in "\n\r \t":
            after += 1
        else:
            break
    return content[after:]


def infer_source_basename_from_template(template_file: str) -> str:
    """无 source_script 时：模板名为 converted_xxx.py 则还原为 xxx.py。"""
    tb = os.path.basename(template_file)
    if tb.startswith("converted_") and tb.lower().endswith(".py"):
        return tb[len("converted_") :]
    return tb


def resolve_restore_destination(
    out_dir: Optional[str],
    output_file: Optional[str],
    payload: dict,
    template_file: str,
) -> str:
    """
    - 指定 -o/--output-file 且路径以 .py 结尾：写入该文件（可含目录）。
    - 否则：写入 out-dir（默认 out/restored）下；文件名优先旧版 payload.source_script，否则从模板名 converted_xxx.py 推断。
    """
    source_base = get_source_script_basename(payload) or infer_source_basename_from_template(
        template_file
    )

    if output_file:
        of = output_file.strip().strip('"')
        if not of.lower().endswith(".py"):
            raise ValueError("-o/--output-file 须为以 .py 结尾的完整路径")
        dest = os.path.abspath(of)
        parent = os.path.dirname(dest)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return dest

    base_dir = out_dir if out_dir is not None else "out/restored"
    base_dir = os.path.abspath(base_dir.strip().rstrip(os.sep + "/"))
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, source_base)


def restore_script(
    template_file: str,
    params_file: str,
    out_dir: Optional[str],
    output_file: Optional[str],
) -> None:
    if not os.path.exists(template_file):
        print(f"错误: 找不到模板文件 {template_file}")
        return
    if not os.path.exists(params_file):
        print(f"错误: 找不到参数文件 {params_file}")
        return

    with open(params_file, "r", encoding="utf-8") as f:
        full_payload = json.load(f)
    if not isinstance(full_payload, dict):
        print("错误: 参数文件顶层应为 JSON 对象")
        return

    params = load_params_map_for_restore(full_payload)
    try:
        dest_path = resolve_restore_destination(out_dir, output_file, full_payload, template_file)
    except ValueError as e:
        print(f"错误: {e}")
        return

    with open(template_file, "r", encoding="utf-8") as f:
        content = f.read()

    content = strip_injected_header(content)

    def replacer(match) -> str:
        key = match.group(1)
        if key in params:
            val = resolve_value_for_restore(params[key])
            return json.dumps(val, ensure_ascii=False)
        print(f"⚠️ 警告: 参数文件中缺失键 '{key}'，将保留原样。")
        return match.group(0)

    content = re.sub(r'params\[[\'"]([^\'"]+)[\'"]\]', replacer, content)

    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("脚本还原成功！")
    print(f"还原后的可执行脚本已保存至: {dest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="根据新参数还原 Playwright 脚本（默认写入 out/restored/ 且与原脚本同名）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
目录约定：
  提取：模板与参数 JSON 放在同一目录（如 out/sample_extract/）。
  还原：默认写入 out/restored/<输出名>.py；新格式参数 JSON 无 source_script 时，
        从模板名 converted_xxx.py 推断为 xxx.py；旧版 JSON 仍可含 source_script。
  显式指定输出文件：-o path/to/file.py
        """.strip(),
    )
    parser.add_argument("-t", "--template", required=True, help="参数化模板 .py 路径")
    parser.add_argument("-p", "--params", required=True, help="参数 JSON 路径")
    parser.add_argument(
        "-d",
        "--out-dir",
        default="out/restored",
        help="还原脚本输出目录（默认 out/restored）；与 -o 指定 .py 文件互斥生效",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        default=None,
        help="直接指定输出的 .py 完整路径；若设置则不再使用 -d 与默认命名",
    )

    args = parser.parse_args()
    restore_script(
        args.template,
        args.params,
        None if args.output_file else args.out_dir,
        args.output_file,
    )
