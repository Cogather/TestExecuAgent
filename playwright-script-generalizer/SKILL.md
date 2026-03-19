---
name: playwright-script-generalizer
description: Extracts parameters from Playwright scripts for storage (generalization), and restores stored templates back into executable scripts using new parameters. Use when the user wants to generalize a script or restore/instantiate a script with new parameters.
---

# Playwright Script Generalizer

## Overview
This skill automates the two-way lifecycle of Playwright recorded scripts:
1. **Phase 1 (Generalize/Extract)**: Converts a hardcoded script into a parameterized template and extracts default parameters into a JSON file, ready for storage/archiving.
2. **Phase 2 (Restore/Instantiate)**: Takes a stored parameterized template and a new JSON parameter file, and restores it into a fully executable, hardcoded Python script.

## Workflows

### Phase 1: Generalize (Extract Parameters)
When the user asks to extract parameters, generalize, or prepare a script for storage:

1. **Execute the extraction script**:
   ```bash
   python .cursor/skills/playwright-script-generalizer/scripts/extract_playwright_params.py -i <input_dir/script.py> -o <output_dir/template_script.py> -p <output_dir/default_params.json>
   ```
2. **Report**: Explain that the script has been parameterized and the default parameters have been extracted to a JSON file, ready for storage.

### Phase 2: Restore (Instantiate with New Params)
When the user asks to restore a script, apply new parameters, or generate an executable script from a template:

1. **Execute the restore script**:
   ```bash
   python .cursor/skills/playwright-script-generalizer/scripts/restore_playwright_script.py -t <stored_dir/template_script.py> -p <new_params.json> -o <executable_script.py>
   ```
2. **Report**: Explain that the template has been successfully merged with the new parameters, and the resulting script is ready to be executed without any external dependencies.

## Examples

**User**: "把 dir1/login.py 提取参数，存到 dir2 里面"
**Agent Action**:
Run: `python .cursor/skills/playwright-script-generalizer/scripts/extract_playwright_params.py -i dir1/login.py -o dir2/template_login.py -p dir2/default_params.json`

**User**: "用 new_env.json 里的参数，把 dir2/template_login.py 还原成可以直接执行的脚本"
**Agent Action**:
Run: `python .cursor/skills/playwright-script-generalizer/scripts/restore_playwright_script.py -t dir2/template_login.py -p new_env.json -o ready_to_run_login.py`
