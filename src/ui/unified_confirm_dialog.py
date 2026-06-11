"""人工确认统一对话框 —— 管脚数 + 未分类器件"""

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
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.models.device import Device
from src.services.config_service import (
    add_to_history,
    get_classifications,
    load_classification_rules,
    load_coefficients,
    load_pin_count_rules,
    save_classification_rules,
    save_pin_count_rules,
    upsert_force_rule,
)

logger = logging.getLogger("ParseApp")


class UnifiedConfirmDialog(QDialog):
    def __init__(self, devices: list[Device], parent=None):
        super().__init__(parent)
        self.setWindowTitle("人工确认")
        self.setMinimumSize(850, 500)

        # 两个过滤条件取并集，按 id(dev) 去重保持插入顺序
        seen = set()
        self._pending: list[Device] = []
        for d in devices:
            if (d.pin_count == 0 and d.package.strip()) or d.classification == "未分类":
                if id(d) not in seen:
                    seen.add(id(d))
                    self._pending.append(d)

        rules_data = load_classification_rules()
        classifications = get_classifications(rules_data)
        self._categories = list(classifications.keys())
        self._pin_rules = load_pin_count_rules()
        self._combos: list[QComboBox] = []
        self._spinners: list[QSpinBox] = []

        self._setup_ui()
        self.setModal(True)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            f"共 <b>{len(self._pending)}</b> 个器件需要人工确认，"
            f"请修改分类和/或管脚数后点击「确认并记录」。"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["器件编码", "器件描述", "封装", "指定分类", "管脚数"]
        )
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
        self._table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Interactive
        )
        self._table.setColumnWidth(0, 180)
        self._table.setColumnWidth(2, 100)
        self._table.setColumnWidth(3, 120)
        self._table.setColumnWidth(4, 80)

        self._table.setRowCount(len(self._pending))
        for row, dev in enumerate(self._pending):
            self._table.setItem(row, 0, QTableWidgetItem(dev.code))
            self._table.setItem(row, 1, QTableWidgetItem(dev.description))
            self._table.setItem(row, 2, QTableWidgetItem(dev.package))

            combo = QComboBox()
            combo.addItem("（跳过）")
            combo.addItems(self._categories)
            if dev.classification != "未分类":
                idx = combo.findText(dev.classification)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self._table.setCellWidget(row, 3, combo)
            self._combos.append(combo)

            spinner = QSpinBox()
            spinner.setRange(0, 9999)
            spinner.setValue(dev.pin_count)
            self._table.setCellWidget(row, 4, spinner)
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
        rules_data = load_classification_rules()
        coeffs = load_coefficients()
        cls_count = 0
        pin_count = 0

        for row, dev in enumerate(self._pending):
            # ---- 分类 ----
            combo = self._combos[row]
            cat = combo.currentText()
            if cat and cat != "（跳过）" and cat != dev.classification:
                dev.classification = cat
                add_to_history(rules_data, dev.code, dev.description, cat)
                upsert_force_rule(
                    code=dev.code,
                    classification=cat,
                    pin_count=dev.pin_count,
                    package=dev.package,
                )
                cls_count += 1

            # ---- 管脚数 ----
            spinner = self._spinners[row]
            pin = spinner.value()
            if pin > 0 and pin != dev.pin_count:
                dev.pin_count = pin
                dev.total_pads = dev.pin_count * dev.quantity
                pkg = dev.package.strip().lower()
                coeff = float(coeffs.get(pkg, dev.pin_count))
                dev.converted_qty = dev.total_pads // coeff
                self._pin_rules[pkg] = pin
                upsert_force_rule(
                    code=dev.code,
                    classification=dev.classification,
                    pin_count=pin,
                    package=dev.package,
                )
                pin_count += 1

        if cls_count > 0:
            save_classification_rules(rules_data)
        if pin_count > 0:
            save_pin_count_rules(self._pin_rules)

        parts: list[str] = []
        if cls_count > 0:
            parts.append(f"{cls_count} 个器件的分类")
        if pin_count > 0:
            parts.append(f"{pin_count} 个器件的管脚数")
        if parts:
            QMessageBox.information(
                self, "已记录", f"已更新{'、'.join(parts)}并记录到规则。"
            )
        self.accept()
