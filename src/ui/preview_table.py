"""数据预览表格"""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
)

from src.models.device import Device
from src.services.config_service import load_classification_rules, get_classifications

logger = logging.getLogger("ParseApp")

HEADERS = [
    "器件编码", "器件描述", "位号", "数量",
    "封装", "管脚数", "分类", "T面数量", "B面数量",
    "总焊点数", "折算后件数",
]


class ClassificationDelegate(QStyledItemDelegate):
    """分类列编辑器 —— 下拉选择"""

    def __init__(self, classifications: list[str], parent=None):
        super().__init__(parent)
        self._classifications = classifications

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self._classifications)
        combo.setCurrentIndex(-1)
        return combo

    def setEditorData(self, editor, index):
        val = index.data(Qt.ItemDataRole.DisplayRole)
        if val:
            idx = editor.findText(val)
            if idx >= 0:
                editor.setCurrentIndex(idx)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.ItemDataRole.DisplayRole)


class PreviewTable(QTableWidget):
    data_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: list[Device] = []
        self._coefficients: dict[str, float] = {}
        self._classifications: list[str] = []
        self._setup_ui()
        self._load_classifications()

    def _load_classifications(self):
        rules_data = load_classification_rules()
        classifications = get_classifications(rules_data)
        self._classifications = sorted(classifications.keys())
        if "未分类" not in self._classifications:
            self._classifications.append("未分类")
        self.setItemDelegateForColumn(6, ClassificationDelegate(self._classifications))

    def set_coefficients(self, coeffs: dict[str, float]):
        self._coefficients = coeffs

    def _setup_ui(self):
        self.setColumnCount(len(HEADERS))
        self.setHorizontalHeaderLabels(HEADERS)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.setSortingEnabled(True)

        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i in range(len(HEADERS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        self.setColumnWidth(0, 160)
        self.setColumnWidth(1, 260)
        self.setColumnWidth(2, 160)
        self.setColumnWidth(3, 60)
        self.setColumnWidth(4, 100)
        self.setColumnWidth(5, 60)
        self.setColumnWidth(6, 90)
        self.setColumnWidth(7, 70)
        self.setColumnWidth(8, 70)
        self.setColumnWidth(9, 80)
        self.setColumnWidth(10, 90)

        self.cellChanged.connect(self._on_cell_changed)

    def set_devices(self, devices: list[Device]):
        self._devices = devices
        self.setSortingEnabled(False)
        self.setRowCount(len(devices))
        self._populate(devices)
        self.setSortingEnabled(True)

    def get_devices(self) -> list[Device]:
        return self._devices

    def _populate(self, devices: list[Device]):
        editable_cols = {4, 5, 6}
        self.blockSignals(True)
        for row, dev in enumerate(devices):
            values = [
                dev.code, dev.description, dev.refdes,
                str(dev.quantity), dev.package, str(dev.pin_count),
                dev.classification,
                str(dev.t_side_count), str(dev.b_side_count),
                str(dev.total_pads), f"{dev.converted_qty:.2f}",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                if col not in editable_cols:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 6 and dev.classification == "未分类":
                    item.setBackground(QColor(255, 230, 230))
                    item.setForeground(QColor(200, 0, 0))
                self.setItem(row, col, item)
        self.blockSignals(False)

    def _on_cell_changed(self, row: int, col: int):
        if row < 0 or row >= len(self._devices):
            return
        dev = self._devices[row]
        item = self.item(row, col)
        if item is None:
            return
        new_val = item.text().strip()

        if col == 4:  # 封装
            dev.package = new_val
            self._recalc_device(dev)
            self._refresh_row(row, dev)
        elif col == 5:  # 管脚数
            try:
                dev.pin_count = int(float(new_val))
            except (ValueError, TypeError):
                dev.pin_count = 0
            self._recalc_device(dev)
            self._refresh_row(row, dev)
        elif col == 6:  # 分类
            dev.classification = new_val if new_val else "未分类"
            self._refresh_row(row, dev)

        self.data_changed.emit()

    def _recalc_device(self, dev: Device):
        pkg = dev.package.strip()
        coeff = 1.0
        if pkg and pkg in self._coefficients:
            coeff = float(self._coefficients[pkg])
        elif pkg:
            for known_pkg, val in self._coefficients.items():
                if known_pkg.lower() in pkg.lower() or pkg.lower() in known_pkg.lower():
                    coeff = float(val)
                    break
        dev.total_pads = dev.pin_count * dev.quantity
        dev.converted_qty = dev.total_pads * coeff

    def _refresh_row(self, row: int, dev: Device):
        """更新行中因联动可能变化的单元格（管脚数、总焊点数、折算件数、分类颜色）"""
        self.blockSignals(True)
        self.item(row, 5).setText(str(dev.pin_count))
        self.item(row, 6).setText(dev.classification)
        self.item(row, 9).setText(str(dev.total_pads))
        self.item(row, 10).setText(f"{dev.converted_qty:.2f}")

        # 分类颜色
        class_item = self.item(row, 6)
        if dev.classification == "未分类":
            class_item.setBackground(QColor(255, 230, 230))
            class_item.setForeground(QColor(200, 0, 0))
        else:
            class_item.setBackground(QColor(255, 255, 255))
            class_item.setForeground(QColor(0, 0, 0))
        self.blockSignals(False)
