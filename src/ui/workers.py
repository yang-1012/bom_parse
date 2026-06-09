"""后台工作线程"""

import logging

import pandas as pd
from PySide6.QtCore import QThread, Signal

from src.classifiers.rule_engine import RuleEngine
from src.classifiers.side_detector import detect_side
from src.models.classification import ClassificationRule
from src.models.device import Device
from src.parsers.bom_parser import parse_bom
from src.parsers.coordinate_parser import parse_coordinate
from src.services.config_service import (
    get_classifications,
    get_classification_history,
    load_classification_rules,
    load_coefficients,
    load_force_rules,
)
from src.services.export_service import export_to_excel

logger = logging.getLogger("ParseApp")


class LoadBomWorker(QThread):
    finished_signal = Signal(list, dict)  # (devices_raw, column_map)
    error_signal = Signal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            rules_data = load_classification_rules()
            aliases = rules_data.get("field_aliases", {})
            devices_raw, column_map = parse_bom(self.file_path, aliases)
            self.finished_signal.emit(devices_raw, column_map)
        except Exception as e:
            logger.exception("BOM 加载失败")
            self.error_signal.emit(str(e))


class LoadCoordinateWorker(QThread):
    finished_signal = Signal(object)  # pd.DataFrame
    error_signal = Signal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            df, _ = parse_coordinate(self.file_path)
            self.finished_signal.emit(df)
        except Exception as e:
            logger.exception("坐标文件加载失败")
            self.error_signal.emit(str(e))


class ClassifyWorker(QThread):
    finished_signal = Signal(list)  # list[Device]
    progress_signal = Signal(int, int)  # current, total
    error_signal = Signal(str)

    def __init__(self, devices_raw: list[dict], bom_column_map: dict,
                 coord_df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self.devices_raw = devices_raw
        self.bom_column_map = bom_column_map
        self.coord_df = coord_df

    def run(self):
        try:
            rules_data = load_classification_rules()
            force_rules = load_force_rules()
            coefficients = load_coefficients()
            classifications = get_classifications(rules_data)
            history = get_classification_history(rules_data)

            engine = RuleEngine(force_rules, history, classifications)

            devices = []
            total = len(self.devices_raw)

            for i, raw in enumerate(self.devices_raw):
                code = _clean_str(raw.get(self._col("器件编码"), ""))
                desc = _clean_str(raw.get(self._col("器件描述"), ""))

                result = engine.classify(code, desc)

                device = Device(
                    code=code,
                    description=desc,
                    refdes=_clean_str(raw.get(self._col("位号"), "")),
                    quantity=self._parse_int(raw.get(self._col("数量"), "0")),
                    classification=result.category,
                    package=_clean_str(raw.get(self._col("封装"), "")),
                    _raw=raw,
                )

                self._assign_side_counts(device)
                self._apply_coefficient(device, coefficients)

                devices.append(device)
                self.progress_signal.emit(i + 1, total)

            self.finished_signal.emit(devices)
        except Exception as e:
            logger.exception("分类运算失败")
            self.error_signal.emit(str(e))

    def _col(self, std_field: str) -> str | None:
        for col, mapped in self.bom_column_map.items():
            if mapped == std_field:
                return col
        return None

    @staticmethod
    def _parse_int(val) -> int:
        try:
            return int(float(str(val).replace(",", "")))
        except (ValueError, TypeError):
            return 0

    def _assign_side_counts(self, device: Device) -> None:
        refdes = device.refdes
        if not refdes:
            return

        ref_list = [r.strip() for r in refdes.replace(";", ",").split(",") if r.strip()]
        t_count = 0
        b_count = 0
        unknown_count = 0

        for ref in ref_list:
            side = self._lookup_side(ref)
            if side == "T":
                t_count += 1
            elif side == "B":
                b_count += 1
            else:
                unknown_count += 1

        if t_count == 0 and b_count == 0:
            device.t_side_count = len(ref_list)
            device.b_side_count = 0
        elif unknown_count > 0:
            if t_count >= b_count:
                device.t_side_count = t_count + unknown_count
                device.b_side_count = b_count
            else:
                device.t_side_count = t_count
                device.b_side_count = b_count + unknown_count
        else:
            device.t_side_count = t_count
            device.b_side_count = b_count

    def _lookup_side(self, ref: str) -> str:
        if self.coord_df is None or self.coord_df.empty:
            return "?"
        for col in self.coord_df.columns:
            col_lower = col.lower()
            if any(kw in col_lower for kw in ["sym_mirror", "mirror", "side", "layer", "面"]):
                for _, row in self.coord_df.iterrows():
                    refdes_cell = ""
                    for rc in self.coord_df.columns:
                        rc_lower = rc.lower()
                        if any(kw in rc_lower for kw in ["refdes", "ref", "reference", "位号", "designator"]):
                            refdes_cell = str(row.get(rc, ""))
                            break
                    if ref in _split_refdes(refdes_cell):
                        return detect_side(str(row.get(col, "")))
                break
        return "?"

    def _apply_coefficient(self, device: Device, coefficients: dict) -> None:
        pkg = device.package.strip()
        coeff = 1.0
        if pkg and pkg in coefficients:
            coeff = float(coefficients[pkg])
        elif pkg:
            for known_pkg, val in coefficients.items():
                if known_pkg.lower() in pkg.lower() or pkg.lower() in known_pkg.lower():
                    coeff = float(val)
                    break
        device.total_pads = device.t_side_count + device.b_side_count
        device.converted_qty = device.total_pads * coeff


def _clean_str(val) -> str:
    """将 pandas NaN 字符串转为空字符串"""
    s = str(val).strip()
    if s.lower() in ("nan", "nat", "none", "null", ""):
        return ""
    return s


def _split_refdes(text: str) -> list[str]:
    """将位号字符串拆分为列表"""
    text = str(text).strip()
    if not text:
        return []
    parts = text.replace(";", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


class ExportWorker(QThread):
    finished_signal = Signal(str)  # output path
    error_signal = Signal(str)

    def __init__(self, devices: list[Device], source_path: str, parent=None):
        super().__init__(parent)
        self.devices = devices
        self.source_path = source_path

    def run(self):
        try:
            path = export_to_excel(self.devices, self.source_path)
            self.finished_signal.emit(path)
        except Exception as e:
            logger.exception("导出失败")
            self.error_signal.emit(str(e))
