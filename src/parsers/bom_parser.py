"""BOM 文件解析器 —— 支持模糊列名匹配，支持 CSV/TXT/Excel"""

import logging
import re
from typing import Optional

import pandas as pd

from src.parsers.encoding_detector import detect_encoding

logger = logging.getLogger("ParseApp")

_EXCEL_EXT = {".xlsx", ".xls", ".xlsm"}


def _normalize(text: str) -> str:
    return re.sub(r"[ _\-/]", "", str(text)).lower()


def _build_alias_map(field_aliases: dict) -> dict:
    alias_map = {}
    for std_field, aliases in field_aliases.items():
        for alias in aliases:
            key = _normalize(alias)
            if key not in alias_map:
                alias_map[key] = std_field
    return alias_map


def _match_column(col_name: str, alias_map: dict) -> Optional[str]:
    key = _normalize(col_name)

    if key in alias_map:
        return alias_map[key]

    for alias_key, std_field in alias_map.items():
        if alias_key in key or key in alias_key:
            return std_field

    part_synonyms = {"partnumber", "partno", "partnum", "pn", "mpn",
                     "part-no", "part-number"}
    desc_synonyms = {"description", "desc", "spec", "specification"}
    ref_synonyms = {"refdes", "designator", "ref", "reference", "position",
                    "positions", "pad"}
    qty_synonyms = {"qty", "quantity", "count", "pcs", "pc", "units", "pieces",
                    "ea", "sum"}
    pkg_synonyms = {"package", "packagetype", "footprint", "pkg",
                    "封装", "封装形式", "元件封装", "包装", "bodysize", "case",
                    "mountingtype", "安装方式", "smt/tht"}
    pin_synonyms = {"pincount", "pins", "pin", "管脚数", "引脚数",
                    "numberofpins", "pin数量", "leadcount", "脚数", "焊盘数"}

    if key in part_synonyms:
        return "器件编码"
    if key in desc_synonyms:
        return "器件描述"
    if key in ref_synonyms:
        return "位号"
    if key in qty_synonyms:
        return "数量"
    if key in pkg_synonyms:
        return "封装"
    if key in pin_synonyms:
        return "管脚数"

    return None


def parse_pin_count(package: str, rules: dict) -> int | None:
    """从封装名称推导管脚数，返回 None 表示无法推导"""
    pkg_lower = package.lower().strip()
    if not pkg_lower:
        return None
    for key, val in rules.items():
        if key in pkg_lower:
            return val
    return None


def _detect_separator(file_path: str, encoding: str) -> str:
    """检测分隔符：找能产生最一致列数的分隔符"""
    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        lines = [f.readline().rstrip("\r\n") for _ in range(30)]
        lines = [l for l in lines if l.strip()]

    candidates = ["\t", ",", ";", "|"]
    best_sep = ","
    best_score = -1

    for sep in candidates:
        col_counts = []
        for line in lines:
            parts = line.split(sep)
            if len(parts) > 1:
                col_counts.append(len(parts))
        if not col_counts:
            continue
        # 评分：列数 > 1 的行越多越好，方差越小越好
        majority_cols = max(set(col_counts), key=col_counts.count)
        consistency = col_counts.count(majority_cols)
        if consistency > best_score and majority_cols > 1:
            best_score = consistency
            best_sep = sep

    logger.info(f"检测分隔符: {repr(best_sep)} (一致行数: {best_score})")
    return best_sep


def _read_csv_flexible(file_path: str, encoding: str, sep: str) -> pd.DataFrame:
    """灵活读取 CSV，跳过元数据行找到表头"""
    # 先用不同 skiprows 尝试
    for skip in range(0, 15):
        try:
            df = pd.read_csv(
                file_path, encoding=encoding, sep=sep, dtype=str,
                keep_default_na=False, skip_blank_lines=True,
                skiprows=skip, on_bad_lines="skip",
            )
            if len(df) > 0 and len(df.columns) > 1:
                logger.info(f"CSV 读取成功 (skiprows={skip}, {len(df)} 行, {len(df.columns)} 列)")
                return df
        except Exception:
            continue

    # 最后用 Python 引擎
    df = pd.read_csv(
        file_path, encoding=encoding, sep=sep, dtype=str,
        keep_default_na=False, skip_blank_lines=True,
        engine="python", on_bad_lines="skip",
    )
    return df


def parse_bom(file_path: str, field_aliases: dict) -> tuple[list[dict], dict]:
    """解析 BOM 文件 (支持 CSV/TXT/Excel)

    Returns:
        (devices_raw, column_map): 原始器件列表 + 列名→标准字段映射
    """
    ext = file_path.lower()[file_path.rfind("."):]

    if ext in _EXCEL_EXT:
        return _parse_excel(file_path, field_aliases)

    encoding = detect_encoding(file_path)
    sep = _detect_separator(file_path, encoding)

    df = _read_csv_flexible(file_path, encoding, sep)

    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    logger.info(f"BOM 文件加载: {len(df)} 行, 列: {list(df.columns)}")

    alias_map = _build_alias_map(field_aliases)
    column_map = {}

    for col in df.columns:
        matched = _match_column(col, alias_map)
        if matched:
            column_map[col] = matched
            logger.info(f"列匹配: '{col}' → '{matched}'")

    devices_raw = df.to_dict(orient="records")
    return devices_raw, column_map


def _parse_excel(file_path: str, field_aliases: dict) -> tuple[list[dict], dict]:
    """解析 Excel 文件"""
    xls = pd.ExcelFile(file_path)
    sheet_name = xls.sheet_names[0]
    logger.info(f"Excel 文件, Sheet: '{sheet_name}'")

    for skip in range(0, 15):
        try:
            df = pd.read_excel(
                file_path, sheet_name=sheet_name, dtype=str, skiprows=skip
            )
            df = df.dropna(how="all").dropna(axis=1, how="all")
            if len(df) > 0 and len(df.columns) > 1:
                logger.info(f"Excel 读取成功 (skiprows={skip}, {len(df)} 行)")
                break
        except Exception:
            continue
    else:
        df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)

    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    logger.info(f"Excel 加载: {len(df)} 行, 列: {list(df.columns)}")

    alias_map = _build_alias_map(field_aliases)
    column_map = {}
    for col in df.columns:
        matched = _match_column(col, alias_map)
        if matched:
            column_map[col] = matched

    devices_raw = df.to_dict(orient="records")
    return devices_raw, column_map
