"""管脚数人工确认对话框"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.models.device import Device
from src.services.config_service import load_pin_count_rules, save_pin_count_rules

logger = logging.getLogger("ParseApp")


class PinConfirmDialog(QDialog):
    def __init__(self, devices: list[Device], parent=None):
        super().__init__(parent)
        self.setWindowTitle("人工确认管脚数")
        self.setMinimumSize(700, 450)
        self._devices = devices
        self._unknown = [
            d for d in devices
            if d.pin_count == 0 and d.package.strip()
        ]
        self._pin_rules = load_pin_count_rules()
        self._spinners = []
        self._setup_ui()
        self.setModal(True)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            f"共 <b>{len(self._unknown)}</b> 个器件无法从封装推导管脚数，"
            f"请输入管脚数后点击「确认并记录」。"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["器件编码", "器件描述", "封装", "管脚数"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 180)
        self._table.setColumnWidth(2, 120)
        self._table.setColumnWidth(3, 80)

        self._table.setRowCount(len(self._unknown))
        for row, dev in enumerate(self._unknown):
            self._table.setItem(row, 0, QTableWidgetItem(dev.code))
            self._table.setItem(row, 1, QTableWidgetItem(dev.description))
            self._table.setItem(row, 2, QTableWidgetItem(dev.package))
            spinner = QSpinBox()
            spinner.setRange(0, 9999)
            spinner.setValue(0)
            self._table.setCellWidget(row, 3, spinner)
            self._spinners.append(spinner)

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
        count = 0
        for row, dev in enumerate(self._unknown):
            pin = self._spinners[row].value()
            if pin > 0:
                dev.pin_count = pin
                dev.total_pads = dev.pin_count * dev.quantity
                # 重新计算折算件数（系数默认为1.0）
                from src.services.config_service import load_coefficients
                coeffs = load_coefficients()
                coeff = 1.0
                pkg = dev.package.strip().lower()
                if pkg and pkg in coeffs:
                    coeff = float(coeffs[pkg])
                dev.converted_qty = dev.total_pads * coeff
                # 记录到映射表（学习）
                self._pin_rules[dev.package.strip().lower()] = pin
                count += 1

        if count > 0:
            save_pin_count_rules(self._pin_rules)
            QMessageBox.information(
                self, "已记录", f"已更新 {count} 个器件的管脚数并记录到映射表。"
            )
        self.accept()
