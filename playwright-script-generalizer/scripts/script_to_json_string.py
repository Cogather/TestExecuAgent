#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 Python 脚本全文转换为 JSON 字符串字面量，便于放入 JSON 请求体（例如 java 接口的 pythonScript 字段）。

使用标准库 json.dumps，会自动处理：
  - 双引号 -> \\"
  - 反斜杠 -> \\\\
  - 换行 -> \\n
  - 控制字符等

用法:
  python script_to_json_string.py path/to/converted_script.py
  python script_to_json_string.py path/to/converted_script.py -o embedded.txt

输出为带外层双引号的合法 JSON 字符串片段，可直接作为 JSON 里某个字符串「值」粘贴
（键名后加冒号，再粘贴整段输出即可，无需再加引号）。
"""

import argparse
import json
import sys


def text_to_json_string_literal(text: str) -> str:
    """整段文本转为合法 JSON 字符串字面量（带外层双引号，供嵌入 JSON 请求体）。"""
    return json.dumps(text, ensure_ascii=False)


def file_to_json_string_literal(path: str) -> str:
    """读取 UTF-8 文件全文，再转为 JSON 字符串字面量。"""
    with open(path, "r", encoding="utf-8") as f:
        return text_to_json_string_literal(f.read())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="将 .py 文件内容转为 JSON 字符串字面量（供嵌入 JSON 体）"
    )
    parser.add_argument("input", help="Python 脚本路径（如提取后的 converted_*.py）")
    parser.add_argument(
        "-o",
        "--output",
        help="写入文件；默认打印到标准输出",
    )
    args = parser.parse_args()

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        print(f"读取失败: {e}", file=sys.stderr)
        sys.exit(1)

    out = text_to_json_string_literal(content)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"已写入: {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()
