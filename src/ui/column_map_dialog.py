"""列映射确认对话框"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

logger = logging.getLogger("ParseApp")

_STANDARD_FIELDS = [
    "器件编码",
    "器件描述",
    "位号",
    "数量",
    "封装",
    "管脚数",
    "单位",
]


class ColumnMapDialog(QDialog):
    """让用户确认/修改 BOM 列与标准字段的映射关系"""

    def __init__(self, column_map: dict, raw_columns: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("列映射确认")
        self.setMinimumSize(550, 400)

        self._result_map: dict = {}

        layout = QVBoxLayout(self)

        # 提示文字
        label = QLabel(
            "请确认或修改 BOM 表头各列对应的标准字段：\n"
            "已自动匹配的已预填，未匹配的请手动选择。"
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        # 表格
        self._table = QTableWidget(len(raw_columns), 2)
        self._table.setHorizontalHeaderLabels(["原始列名", "映射字段"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)

        options = list(_STANDARD_FIELDS) + ["不导入此列"]

        for i, col_name in enumerate(raw_columns):
            # 左列：原始列名（只读）
            item = QTableWidgetItem(col_name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(i, 0, item)

            # 右列：下拉选择
            combo = QComboBox()
            combo.addItems(options)

            # 预填：已有映射则选中对应标准字段，否则"不导入此列"
            mapped = column_map.get(col_name, "")
            if mapped in _STANDARD_FIELDS:
                combo.setCurrentText(mapped)
            else:
                combo.setCurrentText("不导入此列")

            self._table.setCellWidget(i, 1, combo)

        layout.addWidget(self._table)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("确认")
        btn_ok.setDefault(True)
        btn_cancel = QPushButton("取消")
        btn_layout.addWidget(btn_ok)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        btn_ok.clicked.connect(self._on_accept)
        btn_cancel.clicked.connect(self.reject)

    def _on_accept(self):
        self._result_map = {}
        for i in range(self._table.rowCount()):
            col_name = self._table.item(i, 0).text()
            combo = self._table.cellWidget(i, 1)
            field = combo.currentText()
            if field != "不导入此列":
                self._result_map[col_name] = field
        self.accept()

    def get_column_map(self) -> dict:
        return self._result_map
