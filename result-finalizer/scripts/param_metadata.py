"""
基于键名与参数类型的启发式元数据推断（无模型、可复用到其它流水线）。

规则说明：
- URL / 断言 URL：仅标记 kind（url / assert_url），**不**标为 sensitive（多数页面地址视为非密级）。
- 邮箱、手机、工号、用户名、账号等 **不** 自动标为敏感。
- 仅当键名暗示 **密码、令牌、密钥、凭证** 等安全相关语义时 sensitive=true。
- 提取脚本会把原文写入各参数的 value；**参数 JSON 根即为参数字典**（与旧版 ``parameters`` 内层同形）。若仍存在顶层 ``parameters`` 键（历史文件），解包时自动取内层。
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, TypedDict


class ParamEntry(TypedDict, total=False):
    """参数 JSON 中每个键对应的结构，可后续扩展字段。"""

    value: str
    sensitive: bool
    kind: str  # "url" | "assert_url" | "input"


# 安全相关键名（不含单独 PASS，避免误伤 COMPASS 等；用 PASSWORD 等完整词）
_RE_SECRET = re.compile(
    r"(密码|口令|"
    r"PASSWORD|PASSWD|PASSPHRASE|PASSCODE|PASSKEY|"
    r"SECRET|TOKEN|密钥|令牌|凭证|"
    r"APIKEY|API_KEY|ACCESS_KEY|PRIVATE_KEY|PUBLIC_KEY|CLIENT_SECRET|REFRESH_TOKEN|"
    r"BEARER|CREDENTIAL|AUTHORIZATION|AUTH_TOKEN|JWT|OAUTH|"
    r"OTP|私钥|PRIVATE|"
    r"CVV|WEBHOOK|SESSION_TOKEN|COOKIE_TOKEN|"
    r"验证码|PIN码|签名密钥|SIGNING)",
    re.IGNORECASE,
)


def unwrap_parameters_root(raw: Any) -> Dict[str, Any]:
    """
    默认根对象即参数字典 ``{"KEY": {"value", "sensitive", "kind"}}``。
    若存在 ``parameters`` 子对象（历史/嵌套格式），则返回该子对象。
    """
    if isinstance(raw, dict) and "parameters" in raw and isinstance(raw["parameters"], dict):
        return dict(raw["parameters"])
    return raw if isinstance(raw, dict) else {}


def infer_param_metadata(key: str) -> Dict[str, Any]:
    """
    根据参数键名推断 kind、sensitive（value 由调用方填入）。
    """
    entry: Dict[str, Any] = {"value": "", "sensitive": False, "kind": "input"}

    if key.startswith("URL_"):
        entry["kind"] = "url"
        return entry

    if key.startswith("ASSERT_URL_"):
        entry["kind"] = "assert_url"
        return entry

    if _RE_SECRET.search(key):
        entry["sensitive"] = True

    return entry


def normalize_params_flat(raw: Dict[str, Any]) -> Dict[str, str]:
    """
    将 JSON 转为运行期扁平 params：根为参数字典、或旧版含 parameters、
    顶层扁平字符串、或 {"KEY": {"value": "..."}}。
    """
    raw = unwrap_parameters_root(raw)
    out: Dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(v, dict) and "value" in v:
            val = v["value"]
            out[k] = val if isinstance(val, str) else str(val)
        elif isinstance(v, str):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def resolve_value_for_restore(entry: Any) -> str:
    """还原脚本：从 JSON 某键的取值解析出要写入 Python 字面量的字符串。"""
    if isinstance(entry, dict) and "value" in entry:
        v = entry["value"]
        if v is None:
            return ""
        return v if isinstance(v, str) else str(v)
    if isinstance(entry, str):
        return entry
    if entry is None:
        return ""
    return str(entry)


def load_params_map_for_restore(raw: Any) -> Dict[str, Any]:
    """从整份 JSON 得到「参数名 -> 扁平字符串或带 value 的对象」，供还原替换使用。"""
    return unwrap_parameters_root(raw)


def get_source_script_basename(payload: Any) -> Optional[str]:
    """从参数 JSON 顶层读取 source_script（仅旧版载荷含此键），返回 basename。"""
    if not isinstance(payload, dict):
        return None
    s = payload.get("source_script")
    if isinstance(s, str) and s.strip():
        return os.path.basename(s.strip())
    return None
