"""后台工作线程"""

import logging

import pandas as pd
from PySide6.QtCore import QThread, Signal

from src.classifiers.rule_engine import RuleEngine
from src.classifiers.side_detector import detect_side
from src.models.classification import ClassificationRule
from src.models.device import Device
from src.parsers.bom_parser import parse_bom, parse_pin_count
from src.parsers.coordinate_parser import parse_coordinate
from src.services.config_service import (
    get_classifications,
    get_classification_history,
    load_classification_rules,
    load_coefficients,
    load_force_rules,
    load_pin_count_rules,
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
            pin_count_rules = load_pin_count_rules()
            classifications = get_classifications(rules_data)
            history = get_classification_history(rules_data)

            engine = RuleEngine(force_rules, history, classifications)
            coord_lookup = self._build_coord_lookup()

            devices = []
            total = len(self.devices_raw)

            for i, raw in enumerate(self.devices_raw):
                code = _clean_str(raw.get(self._col("器件编码"), ""))
                desc = _clean_str(raw.get(self._col("器件描述"), ""))

                # 强制覆盖规则（最高优先级）
                force_ov = engine.get_force_override(code)

                # 封装: force > 坐标文件 COMP_DEVICE_TYPE > BOM 封装列
                force_pkg = force_ov.get("package", "") if force_ov else ""
                bom_pkg = _clean_str(raw.get(self._col("封装"), ""))
                coord_pkg = ""
                refdes_raw = _clean_str(raw.get(self._col("位号"), ""))
                if refdes_raw and coord_lookup:
                    refs = _split_refdes(refdes_raw)
                    if refs:
                        coord_pkg = coord_lookup.get(refs[0], {}).get("package", "")
                pkg = force_pkg if force_pkg else (coord_pkg if coord_pkg else bom_pkg)

                # 管脚数: force > pin_count_rules 推导
                if force_ov and force_ov.get("pin_count", 0) > 0:
                    pin_count = force_ov["pin_count"]
                else:
                    result_pin = parse_pin_count(pkg, pin_count_rules)
                    pin_count = result_pin if result_pin is not None else 0

                result = engine.classify(code, desc)

                device = Device(
                    code=code,
                    description=desc,
                    refdes=refdes_raw,
                    quantity=self._parse_int(raw.get(self._col("数量"), "0")),
                    classification=result.category,
                    package=pkg,
                    pin_count=pin_count,
                    _raw=raw,
                )

                self._assign_side_counts(device, coord_lookup)
                # 只在有坐标文件时用量覆盖 BOM 数量，否则保留原始数量
                if coord_lookup and (device.t_side_count > 0 or device.b_side_count > 0):
                    device.quantity = device.t_side_count + device.b_side_count
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

    def _build_coord_lookup(self) -> dict[str, dict[str, str]]:
        """从坐标文件构建 {refdes: {package, side}} 查找表"""
        if self.coord_df is None or self.coord_df.empty:
            return {}

        refdes_keywords = ["refdes", "ref", "reference", "位号", "designator", "ref des"]
        pkg_keywords = [
            "comp_device_type", "comp device type", "device_type",
            "component_type", "devicetype", "package", "footprint",
            "pkg", "封装", "package_type", "foot_print",
        ]
        side_keywords = ["sym_mirror", "mirror", "side", "layer", "面"]

        refdes_col = None
        pkg_col = None
        side_col = None
        for col in self.coord_df.columns:
            col_lower = col.lower()
            if refdes_col is None and any(kw in col_lower for kw in refdes_keywords):
                refdes_col = col
            if pkg_col is None and any(kw in col_lower for kw in pkg_keywords):
                pkg_col = col
            if side_col is None and any(kw in col_lower for kw in side_keywords):
                side_col = col

        if refdes_col is None:
            return {}

        lookup = {}
        for _, row in self.coord_df.iterrows():
            refdes_cell = str(row.get(refdes_col, ""))
            if not refdes_cell:
                continue
            pkg_val = _clean_str(row.get(pkg_col, "")) if pkg_col else ""
            side_val = str(row.get(side_col, "")) if side_col else ""

            for ref in _split_refdes(refdes_cell):
                if ref and ref not in lookup:
                    entry = {}
                    if pkg_val:
                        entry["package"] = pkg_val
                    if side_val:
                        entry["side"] = side_val
                    lookup[ref] = entry

        if lookup:
            logger.info(f"坐标查找表: {len(lookup)} 个位号, "
                        f"含封装: {sum(1 for v in lookup.values() if 'package' in v)}, "
                        f"含面别: {sum(1 for v in lookup.values() if 'side' in v)}")
        return lookup

    def _assign_side_counts(self, device: Device,
                            coord_lookup: dict[str, dict[str, str]]) -> None:
        refdes = device.refdes
        if not refdes:
            return

        ref_list = _split_refdes(refdes)
        t_count = 0
        b_count = 0
        unknown_count = 0

        for ref in ref_list:
            entry = coord_lookup.get(ref, {})
            side_val = entry.get("side", "")
            side = detect_side(side_val) if side_val else "?"
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

    def _apply_coefficient(self, device: Device, coefficients: dict) -> None:
        pkg = device.package.strip()
        coeff = max(device.pin_count, 1)
        if pkg and pkg in coefficients:
            coeff = float(coefficients[pkg])
        elif pkg:
            for known_pkg, val in coefficients.items():
                if known_pkg.lower() in pkg.lower() or pkg.lower() in known_pkg.lower():
                    coeff = float(val)
                    break
        device.total_pads = device.pin_count * device.quantity
        device.converted_qty = device.total_pads // coeff


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
