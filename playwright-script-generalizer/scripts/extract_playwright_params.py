import re
import argparse
import json
import os

def extract_and_convert(input_file, output_file, params_file):
    """
    解析 Playwright 录制的 Python 脚本，提取 URL 和用户输入等硬编码参数，
    将其替换为参数化调用，并生成新的脚本和配置文件。
    """
    if not os.path.exists(input_file):
        print(f"❌ 错误: 找不到输入文件 {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    params = {}
    url_counter = 1
    input_counter = 1

    # 正则表达式匹配 Playwright 常见的硬编码参数并尝试提取业务上下文
    
    # 匹配 page.goto("url")
    goto_pattern = re.compile(r'(page\.goto\()([\'"])(.*?)\2')
    # 匹配 expect(...).to_have_url("url")
    expect_url_pattern = re.compile(r'(\.to_have_url\()([\'"])(.*?)\2')
    
    # 匹配常见的定位器模式，提取业务名称，例如 get_by_placeholder("请输入账号").fill("admin")
    # 捕获组:
    # 1: 整个定位器及方法调用前的部分, 例如: page.get_by_placeholder("请输入账号").fill(
    # 2: 业务描述词, 例如: 请输入账号
    # 3: 填充的方法, fill 或 type
    # 4: 引号 (' 或 ")
    # 5: 实际填充的值, 例如: admin
    business_input_pattern = re.compile(r'(.*?(?:get_by_placeholder|get_by_label|get_by_role|locator)\([\'"]?(.*?)[\'"]?(?:,\s*name=[\'"](.*?)[\'"])?\).*?)\.(fill|type)\(([\'"])(.*?)\5\)')

    # 对于没有匹配到业务特征的普通 fill/type (fallback)
    fallback_input_pattern = re.compile(r'(\.(?:fill|type)\()([\'"])(.*?)\2')

    out_lines = []
    
    def clean_name(text):
        """清洗提取到的文本，转换为合法的字典键或变量名。"""
        if not text:
            return ""
        # 移除非字母数字下划线中文的字符，用下划线替代
        cleaned = re.sub(r'[^\w\u4e00-\u9fa5]', '_', text).strip('_')
        # 去重下划线
        cleaned = re.sub(r'_+', '_', cleaned)
        return cleaned[:30] # 限制长度

    for line in lines:
        matched = False
        
        # 替换 goto 中的 URL
        def goto_repl(match):
            nonlocal url_counter
            val = match.group(3)
            # 尝试从 URL 中提取业务名 (最后一段)
            try:
                parts = val.split('/')
                last_part = parts[-1] if parts[-1] else parts[-2]
                biz_name = clean_name(last_part).upper()
                if not biz_name: biz_name = str(url_counter)
            except:
                biz_name = str(url_counter)
                
            key = f"URL_{biz_name}"
            # 处理重名
            if key in params and params[key] != val:
                key = f"URL_{biz_name}_{url_counter}"
                
            params[key] = val
            url_counter += 1
            return f'{match.group(1)}params["{key}"]'
            
        new_line = goto_pattern.sub(goto_repl, line)
        if new_line != line:
            out_lines.append(new_line)
            continue
            
        # 替换 expect(page).to_have_url("url") 中的 URL
        def expect_url_repl(match):
            nonlocal url_counter
            val = match.group(3)
            try:
                parts = val.split('/')
                last_part = parts[-1] if parts[-1] else parts[-2]
                biz_name = clean_name(last_part).upper()
                if not biz_name: biz_name = str(url_counter)
            except:
                biz_name = str(url_counter)
                
            key = f"ASSERT_URL_{biz_name}"
            if key in params and params[key] != val:
                key = f"ASSERT_URL_{biz_name}_{url_counter}"
                
            params[key] = val
            url_counter += 1
            return f'{match.group(1)}params["{key}"]'
            
        new_line = expect_url_pattern.sub(expect_url_repl, line)
        if new_line != line:
            out_lines.append(new_line)
            continue

        # 尝试匹配带业务上下文的输入 (例如 get_by_placeholder("用户名").fill("admin"))
        # 使用更精确的方式提取同行内的业务信息
        # 1. 尝试从 get_by_* 中提取
        biz_match = re.search(r'(?:get_by_placeholder|get_by_label|get_by_role|get_by_text|get_by_title)\([\'"]([^\'"]+)[\'"]', line)
        if not biz_match:
            # 2. 如果是 get_by_role('button', name='xxx')
            biz_match = re.search(r'name=[\'"]([^\'"]+)[\'"]', line)
        if not biz_match:
            # 3. 尝试从 locator 中提取 id 或其他特征 (比如 name="password")
            biz_match = re.search(r'locator\([\'"]#([^\'"]+)[\'"]\)', line)
        if not biz_match:
            biz_match = re.search(r'locator\([\'"].*?name=[\'"]([^\'"]+)[\'"].*?[\'"]\)', line)
            
        def input_repl(match):
            nonlocal input_counter
            method = match.group(1) # .fill( 或 .type(
            val = match.group(3)
            
            biz_name = ""
            if biz_match:
                biz_name = clean_name(biz_match.group(1)).upper()
            
            if biz_name:
                key = f"INPUT_{biz_name}"
            else:
                key = f"INPUT_{input_counter}"
                
            if key in params and params[key] != val:
                key = f"{key}_{input_counter}"
                
            params[key] = val
            input_counter += 1
            return f'{method}params["{key}"]'

        new_line = fallback_input_pattern.sub(input_repl, line)
        out_lines.append(new_line)

    # 写入转换后的脚本
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('import json\n')
        f.write('import os\n\n')
        f.write('# === 自动注入的参数加载逻辑 ===\n')
        f.write(f'PARAMS_FILE = "{os.path.basename(params_file)}"\n')
        f.write('if os.path.exists(PARAMS_FILE):\n')
        f.write('    with open(PARAMS_FILE, "r", encoding="utf-8") as f:\n')
        f.write('        params = json.load(f)\n')
        f.write('else:\n')
        # 如果配置文件丢失，则作为 fallback 的默认参数字典
        f.write(f'    params = {json.dumps(params, indent=4, ensure_ascii=False)}\n')
        f.write('# ==============================\n\n')
        
        for line in out_lines:
            f.write(line)
            
    # 提取的参数单独保存为 JSON，方便作为环境参数进行修改和配置
    with open(params_file, 'w', encoding='utf-8') as f:
        json.dump(params, f, indent=4, ensure_ascii=False)
        
    print("脚本参数提取与转换成功！")
    print(f"提取的参数总数: {len(params)}")
    print(f"转换后的脚本已保存至: {output_file}")
    print(f"参数配置文件已保存至: {params_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Playwright 脚本参数提取与转换工具")
    parser.add_argument("-i", "--input", required=True, help="输入的 Playwright 录制脚本路径 (.py)")
    parser.add_argument("-o", "--output", default="converted_script.py", help="输出的转换后脚本路径 (.py)")
    parser.add_argument("-p", "--params", default="params.json", help="输出的参数配置文件路径 (.json)")
    
    args = parser.parse_args()
    extract_and_convert(args.input, args.output, args.params)
