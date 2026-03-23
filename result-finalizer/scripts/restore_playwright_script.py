import argparse
import json
import re
import os

def restore_script(template_file, params_file, output_file):
    """
    读取入库的泛化模板脚本和新的参数 JSON 文件，
    将模板中的 params["KEY"] 还原为硬编码的实际值，生成可直接执行的脚本。
    """
    if not os.path.exists(template_file):
        print(f"错误: 找不到模板文件 {template_file}")
        return
    if not os.path.exists(params_file):
        print(f"错误: 找不到参数文件 {params_file}")
        return

    with open(params_file, 'r', encoding='utf-8') as f:
        params = json.load(f)

    with open(template_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 移除头部自动注入的参数加载逻辑
    # 匹配 extract_playwright_params.py 生成的头部代码块
    header_pattern = r'import json\nimport os\n\n# === 自动注入的参数加载逻辑 ===.*?# ==============================\n+'
    content = re.sub(header_pattern, '', content, flags=re.DOTALL)

    # 2. 替换 params["KEY"] 为实际的字符串
    def replacer(match):
        key = match.group(1)
        if key in params:
            # 使用 json.dumps 确保字符串被正确转义并带有双引号
            return json.dumps(params[key], ensure_ascii=False)
        else:
            print(f"⚠️ 警告: 参数文件中缺失键 '{key}'，将保留原样。")
            return match.group(0)

    # 匹配 params["KEY"] 或 params['KEY']
    content = re.sub(r'params\[[\'"]([^\'"]+)[\'"]\]', replacer, content)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print("脚本还原成功！")
    print(f"还原后的可执行脚本已保存至: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="根据新参数还原 Playwright 脚本")
    parser.add_argument("-t", "--template", required=True, help="入库的模板脚本路径")
    parser.add_argument("-p", "--params", required=True, help="新的参数 JSON 文件路径")
    parser.add_argument("-o", "--output", default="restored_script.py", help="还原后的可执行脚本路径")
    
    args = parser.parse_args()
    restore_script(args.template, args.params, args.output)
