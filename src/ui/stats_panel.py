"""统计区面板 —— 表格形式呈现"""

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.models.device import Device

CATEGORY_ORDER = [
    "SMT器件", "插件器件", "压接器件", "装配器件",
    "通孔回流", "辅料", "测试分类", "未分类",
]

HEADERS = ["分类", "器件行数", "总数量", "T面件数", "B面件数", "折算后件数"]


class StatsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._table = QTableWidget(0, len(HEADERS))
        self._table.setHorizontalHeaderLabels(HEADERS)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        header = self._table.horizontalHeader()
        for i in range(len(HEADERS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self._table)

    def update_stats(self, devices: list[Device]):
        cat_types = defaultdict(int)
        cat_qty = defaultdict(int)
        cat_t = defaultdict(int)
        cat_b = defaultdict(int)
        cat_qtys = defaultdict(float)
        for dev in devices:
            cat_types[dev.classification] += 1
            cat_qty[dev.classification] += dev.quantity
            cat_t[dev.classification] += dev.t_side_count
            cat_b[dev.classification] += dev.b_side_count
            cat_qtys[dev.classification] += dev.converted_qty

        rows = []
        for cat in CATEGORY_ORDER:
            if cat in cat_types or cat == "未分类":
                rows.append(cat)

        for cat in sorted(cat_types.keys()):
            if cat not in CATEGORY_ORDER:
                rows.append(cat)

        self._table.setRowCount(len(rows) + 1)

        for r, cat in enumerate(rows):
            cat_item = QTableWidgetItem(cat)
            if cat == "未分类":
                cat_item.setForeground(QBrush(QColor(200, 0, 0)))
            self._table.setItem(r, 0, cat_item)
            self._table.setItem(r, 1, QTableWidgetItem(str(cat_types[cat])))
            self._table.setItem(r, 2, QTableWidgetItem(str(cat_qty[cat])))
            self._table.setItem(r, 3, QTableWidgetItem(str(cat_t[cat])))
            self._table.setItem(r, 4, QTableWidgetItem(str(cat_b[cat])))
            self._table.setItem(r, 5, QTableWidgetItem(f"{cat_qtys[cat]:.2f}"))

        # 合计行
        total_row = len(rows)
        bold = QBrush(QColor(0, 0, 0))
        totals = [
            "合计",
            str(sum(cat_types.values())),
            str(sum(cat_qty.values())),
            str(sum(cat_t.values())),
            str(sum(cat_b.values())),
            f"{sum(cat_qtys.values()):.2f}",
        ]
        for col, text in enumerate(totals):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(bold)
            self._table.setItem(total_row, col, item)
