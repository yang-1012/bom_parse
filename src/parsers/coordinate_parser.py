"""坐标文件(.txt)解析器"""

import logging

import pandas as pd

from src.parsers.encoding_detector import detect_encoding

logger = logging.getLogger("ParseApp")


def parse_coordinate(file_path: str) -> tuple[pd.DataFrame, str]:
    """解析坐标文件

    Returns:
        (dataframe, encoding): 解析后的 DataFrame 和使用的编码
    """
    encoding = detect_encoding(file_path)

    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        content = f.read()

    lines = content.splitlines()
    header_line = -1
    for i, line in enumerate(lines):
        lower = line.lower()
        if "refdes" in lower or "ref des" in lower or "reference" in lower or "位号" in line:
            header_line = i
            break

    if header_line < 0:
        header_line = 0
        for i, line in enumerate(lines):
            parts = [p.strip() for p in line.replace("\t", ",").split(",") if p.strip()]
            if len(parts) >= 3:
                header_line = i
                break

    logger.info(f"坐标文件表头行: {header_line + 1}")

    try:
        df = pd.read_csv(
            file_path, encoding=encoding, sep=None, engine="python",
            skiprows=header_line, dtype=str, keep_default_na=False,
            skip_blank_lines=True
        )
    except Exception:
        sep = "\t" if "\t" in lines[header_line] else ","
        df = pd.read_csv(
            file_path, encoding=encoding, sep=sep,
            skiprows=header_line, dtype=str, keep_default_na=False,
            skip_blank_lines=True
        )

    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(c).strip() for c in df.columns]
    logger.info(f"坐标文件加载: {len(df)} 行, 列: {list(df.columns)}")

    return df, encoding
