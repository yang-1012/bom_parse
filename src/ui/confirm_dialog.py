"""未分类器件人工确认对话框"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.models.device import Device
from src.services.config_service import (
    add_to_history,
    get_classifications,
    load_classification_rules,
    save_classification_rules,
)

logger = logging.getLogger("ParseApp")


class ConfirmDialog(QDialog):
    def __init__(self, devices: list[Device], parent=None):
        super().__init__(parent)
        self.setWindowTitle("人工确认未分类器件")
        self.setMinimumSize(800, 500)
        self._devices = devices
        self._unclassified = [d for d in devices if d.classification == "未分类"]
        rules_data = load_classification_rules()
        classifications = get_classifications(rules_data)
        self._categories = list(classifications.keys())
        self._setup_ui()
        self.setModal(True)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            f"共 <b>{len(self._unclassified)}</b> 个未分类器件，"
            f"请在下拉框中选择正确分类后点击「确认并记录」"
        )
        layout.addWidget(info)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["器件编码", "器件描述", "封装", "指定分类"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive
        )
        self._table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Interactive
        )
        self._table.setColumnWidth(0, 180)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 120)

        self._combos = []

        self._table.setRowCount(len(self._unclassified))
        for row, dev in enumerate(self._unclassified):
            self._table.setItem(row, 0, QTableWidgetItem(dev.code))
            self._table.setItem(row, 1, QTableWidgetItem(dev.description))
            self._table.setItem(row, 2, QTableWidgetItem(dev.package))
            combo = QComboBox()
            combo.addItem("（跳过）")
            combo.addItems(self._categories)
            combo.setCurrentIndex(0)
            self._table.setCellWidget(row, 3, combo)
            self._combos.append(combo)

        layout.addWidget(self._table)

        btns = QHBoxLayout()
        confirm_btn = QPushButton("确认并记录")
        confirm_btn.clicked.connect(self._confirm)
        confirm_btn.setStyleSheet("font-weight: bold;")
        skip_btn = QPushButton("全部跳过")
        skip_btn.clicked.connect(self.close)
        btns.addStretch()
        btns.addWidget(confirm_btn)
        btns.addWidget(skip_btn)
        layout.addLayout(btns)

    def _confirm(self):
        rules_data = load_classification_rules()
        count = 0

        for row, dev in enumerate(self._unclassified):
            combo = self._combos[row]
            cat = combo.currentText()
            if cat and cat != "（跳过）":
                dev.classification = cat
                add_to_history(rules_data, dev.code, dev.description, cat)
                count += 1

        if count > 0:
            save_classification_rules(rules_data)
            QMessageBox.information(
                self, "已记录", f"已更新 {count} 个器件的分类并记录到历史。"
            )
        self.accept()
