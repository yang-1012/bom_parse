"""B/T 面检测器

SYM_MIRROR 为 YES → B面, NO → T面
"""

import logging

logger = logging.getLogger("ParseApp")


def detect_side(sym_mirror_value: str) -> str:
    """返回 'T' 或 'B'，不明确返回 '?'"""
    val = str(sym_mirror_value).strip().upper()
    if val == "NO":
        return "T"
    elif val == "YES":
        return "B"
    else:
        return "?"
