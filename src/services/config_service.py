"""配置文件读写服务

管理三个配置文件:
- config/classification_rules.json  -- 分类规则 + 字段别名 + 分类历史
- config/force_rules.json          -- 强制指定规则
- config/coefficients.json         -- 折算系数
"""

import json
import logging
import os
from datetime import datetime
from typing import Any

from src.models.classification import ClassificationRule

logger = logging.getLogger("ParseApp")

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")

os.makedirs(_CONFIG_DIR, exist_ok=True)


def _config_path(filename: str) -> str:
    return os.path.join(_CONFIG_DIR, filename)


def _read_json(filename: str) -> dict:
    path = _config_path(filename)
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(filename: str, data: dict) -> None:
    path = _config_path(filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"配置已保存: {filename}")


# ---- classification_rules.json ----

def load_classification_rules() -> dict:
    """加载分类规则 (classifications + field_aliases + classification_history)"""
    return _read_json("classification_rules.json")


def save_classification_rules(data: dict) -> None:
    data["last_updated"] = datetime.now().isoformat()
    _write_json("classification_rules.json", data)


def get_classifications(data: dict) -> dict[str, ClassificationRule]:
    """从配置数据中提取分类规则"""
    result = {}
    for name, rule in data.get("classifications", {}).items():
        result[name] = ClassificationRule(
            name=name,
            keywords=rule.get("keywords", []),
            exclude_keywords=rule.get("exclude_keywords", []),
        )
    return result


def update_classifications(data: dict, rules: dict[str, ClassificationRule]) -> None:
    """更新配置中的分类规则"""
    data["classifications"] = {}
    for name, rule in rules.items():
        data["classifications"][name] = {
            "keywords": rule.keywords,
            "exclude_keywords": rule.exclude_keywords,
        }


def get_field_aliases(data: dict) -> dict[str, list[str]]:
    return data.get("field_aliases", {})


def get_classification_history(data: dict) -> list[dict]:
    return data.get("classification_history", [])


def add_to_history(data: dict, part_number: str, description: str,
                   classification: str) -> None:
    """追加一条分类记录到历史"""
    history = data.setdefault("classification_history", [])
    # 去重
    for entry in history:
        if (entry.get("part_number") == part_number
                and entry.get("description") == description):
            entry["classification"] = classification
            return
    history.append({
        "part_number": part_number,
        "description": description,
        "classification": classification,
    })


# ---- force_rules.json ----

def load_force_rules() -> dict[str, dict]:
    """加载强制指定规则，兼容旧格式 {"编码": "分类"} → 新格式"""
    raw = _read_json("force_rules.json")
    result = {}
    for code, val in raw.items():
        if isinstance(val, str):
            result[code] = {"classification": val, "pin_count": 0, "package": ""}
        elif isinstance(val, dict):
            result[code] = {
                "classification": val.get("classification", "未分类"),
                "pin_count": val.get("pin_count", 0),
                "package": val.get("package", ""),
            }
    return result


def save_force_rules(rules: dict[str, dict]) -> None:
    _write_json("force_rules.json", rules)


def upsert_force_rule(
    code: str,
    classification: str | None = None,
    pin_count: int | None = None,
    package: str | None = None,
) -> None:
    """更新或新增一条强制指定规则（只修改传入的字段）"""
    rules = load_force_rules()
    entry = rules.get(code, {"classification": "未分类", "pin_count": 0, "package": ""})
    if classification is not None:
        entry["classification"] = classification
    if pin_count is not None:
        entry["pin_count"] = pin_count
    if package is not None:
        entry["package"] = package
    rules[code] = entry
    save_force_rules(rules)


# ---- coefficients.json ----

def load_coefficients() -> dict[str, float]:
    return _read_json("coefficients.json")


def save_coefficients(coeffs: dict[str, float]) -> None:
    _write_json("coefficients.json", coeffs)


# ---- pin_count_rules.json ----

def load_pin_count_rules() -> dict[str, int]:
    return _read_json("pin_count_rules.json")


def save_pin_count_rules(rules: dict[str, int]) -> None:
    _write_json("pin_count_rules.json", rules)
