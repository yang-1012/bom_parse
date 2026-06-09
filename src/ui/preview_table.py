"""数据预览表格"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from src.models.device import Device

logger = logging.getLogger("ParseApp")

HEADERS = [
    "器件编码", "器件描述", "位号", "数量",
    "封装", "管脚数", "分类", "T面数量", "B面数量",
    "总焊点数", "折算后件数",
]


class PreviewTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices: list[Device] = []
        self._setup_ui()

    def _setup_ui(self):
        self.setColumnCount(len(HEADERS))
        self.setHorizontalHeaderLabels(HEADERS)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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

    def set_devices(self, devices: list[Device]):
        self._devices = devices
        self.setSortingEnabled(False)
        self.setRowCount(len(devices))
        self._populate(devices)
        self.setSortingEnabled(True)

    def get_devices(self) -> list[Device]:
        return self._devices

    def _populate(self, devices: list[Device]):
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
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 6 and dev.classification == "未分类":
                    item.setBackground(QColor(255, 230, 230))
                    item.setForeground(QColor(200, 0, 0))
                self.setItem(row, col, item)
