"""智能编码检测器"""

import logging
import re

logger = logging.getLogger("ParseApp")

# 常用中文编码优先，latin-1 放在最后（它能解码任何字节，仅作最后手段）
_ENCODINGS = ["utf-8", "gbk", "gb2312", "utf-16", "utf-8-sig", "gb18030", "latin-1"]


def _try_decode(raw: bytes, enc: str) -> str | None:
    try:
        return raw.decode(enc)
    except (UnicodeDecodeError, UnicodeError):
        return None


def _has_garbled(text: str) -> bool:
    """乱码检测：latin-1 解码中文会产出大量 ÂÃ©® 等高位字符"""
    sample = text[:8000]
    if not sample:
        return False

    # latin-1 解码中文的典型特征：大量 0xC0-0xFF 范围的孤立字符
    high_bytes = len([ch for ch in sample if 0xC0 <= ord(ch) <= 0xFF])
    total = len(sample)
    if high_bytes > total * 0.15:
        return True

    # 不可打印字符比例
    garbled = 0
    for ch in sample:
        cp = ord(ch)
        if cp < 0x20 and ch not in "\r\n\t":
            garbled += 1
        elif 0xD800 <= cp <= 0xDFFF:
            garbled += 1
    if garbled > total * 0.05:
        return True

    # latin-1 解码中文：连续的 ÂÃ 模式
    if re.search(r"[\xC2\xC3][\xA0-\xBF]", sample):
        latin_patterns = len(re.findall(r"[\xC0-\xFF]{2,}", sample))
        if latin_patterns > total * 0.05:
            return True

    return False


def detect_encoding(file_path: str) -> str:
    """依次尝试编码列表，解码成功且无乱码则返回"""
    with open(file_path, "rb") as f:
        raw = f.read()

    # BOM 检测
    if raw[:3] == b"\xef\xbb\xbf":
        logger.info("检测到 UTF-8 BOM")
        return "utf-8-sig"
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        logger.info("检测到 UTF-16 BOM")
        return "utf-16"

    for enc in _ENCODINGS:
        text = _try_decode(raw, enc)
        if text is not None and not _has_garbled(text):
            logger.info(f"编码检测成功: {enc}")
            return enc

    # 兜底
    logger.warning("所有编码尝试失败，使用 utf-8（忽略错误）")
    return "utf-8"


def read_file_with_encoding(file_path: str) -> str:
    """检测编码并读取文件内容"""
    encoding = detect_encoding(file_path)
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        return f.read()
