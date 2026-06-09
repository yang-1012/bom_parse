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


class StatsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "分类", "种类数", "折算件数", "占比(种类)", "占比(件数)"
        ])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self._table)

    def update_stats(self, devices: list[Device]):
        cat_types = defaultdict(int)
        cat_qtys = defaultdict(float)
        for dev in devices:
            cat_types[dev.classification] += 1
            cat_qtys[dev.classification] += dev.converted_qty

        total_types = sum(cat_types.values())
        total_qty = sum(cat_qtys.values())

        rows = []
        for cat in CATEGORY_ORDER:
            if cat in cat_types or cat == "未分类":
                rows.append((cat, cat_types.get(cat, 0), cat_qtys.get(cat, 0.0)))

        # 兜底：order 中没有的类别也加上
        for cat in sorted(cat_types.keys()):
            if cat not in CATEGORY_ORDER:
                rows.append((cat, cat_types[cat], cat_qtys[cat]))

        self._table.setRowCount(len(rows) + 1)  # +1 for total row

        for r, (cat, t_count, qty) in enumerate(rows):
            t_pct = f"{t_count / total_types * 100:.1f}%" if total_types else "0%"
            q_pct = f"{qty / total_qty * 100:.1f}%" if total_qty else "0%"

            cat_item = QTableWidgetItem(cat)
            if cat == "未分类":
                cat_item.setForeground(QBrush(QColor(200, 0, 0)))
            self._table.setItem(r, 0, cat_item)
            self._table.setItem(r, 1, QTableWidgetItem(str(t_count)))
            self._table.setItem(r, 2, QTableWidgetItem(f"{qty:.2f}"))
            self._table.setItem(r, 3, QTableWidgetItem(t_pct))
            self._table.setItem(r, 4, QTableWidgetItem(q_pct))

        # 合计行
        total_row = len(rows)
        bold = QBrush(QColor(0, 0, 0))
        for col, text in enumerate([
            "合计", str(total_types), f"{total_qty:.2f}", "100%", "100%"
        ]):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setForeground(bold)
            self._table.setItem(total_row, col, item)
