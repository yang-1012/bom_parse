"""强制指定规则维护对话框"""

import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.services.config_service import (
    get_classifications,
    load_classification_rules,
    load_force_rules,
    save_force_rules,
)

logger = logging.getLogger("ParseApp")


class ForceEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("强制指定规则维护")
        self.setMinimumSize(750, 450)
        self._force_rules = load_force_rules()
        rules_data = load_classification_rules()
        classifications = get_classifications(rules_data)
        self._categories = list(classifications.keys())
        self._setup_ui()
        self._load_table()
        self.setModal(True)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["器件编码", "分类", "管脚数", "封装"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for i in range(1, 4):
            self._table.horizontalHeader().setSectionResizeMode(
                i, QHeaderView.ResizeMode.Interactive
            )
        self._table.setColumnWidth(1, 120)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 120)
        layout.addWidget(self._table)

        btns = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._delete)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        layout.addLayout(btns)

        bottom = QHBoxLayout()
        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._import_force)
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._export_force)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet("font-weight: bold;")
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        bottom.addWidget(import_btn)
        bottom.addWidget(export_btn)
        bottom.addStretch()
        bottom.addWidget(save_btn)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

    def _load_table(self):
        self._table.setRowCount(len(self._force_rules))
        for row, (code, entry) in enumerate(sorted(self._force_rules.items())):
            self._table.setItem(row, 0, QTableWidgetItem(code))
            combo = QComboBox()
            combo.addItems(self._categories)
            cat = entry.get("classification", "未分类") if isinstance(entry, dict) else entry
            if cat in self._categories:
                combo.setCurrentText(cat)
            else:
                combo.addItem(cat)
                combo.setCurrentText(cat)
            self._table.setCellWidget(row, 1, combo)

            pin_count = entry.get("pin_count", 0) if isinstance(entry, dict) else 0
            self._table.setItem(row, 2, QTableWidgetItem(str(pin_count) if pin_count else ""))

            pkg = entry.get("package", "") if isinstance(entry, dict) else ""
            self._table.setItem(row, 3, QTableWidgetItem(pkg))

    def _add(self):
        code, ok1 = QInputDialog.getText(self, "添加强制指定", "器件编码:")
        if not ok1 or not code.strip():
            return
        code = code.strip()
        if code in self._force_rules:
            QMessageBox.warning(self, "重复", f"\"{code}\" 已存在强制指定规则。")
            return

        cat, ok2 = QInputDialog.getItem(
            self, "选择分类", "分类:", self._categories, 0, False
        )
        if not ok2:
            return

        self._force_rules[code] = {"classification": cat, "pin_count": 0, "package": ""}
        self._load_table()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0:
            return
        code_item = self._table.item(row, 0)
        if not code_item:
            return
        code = code_item.text()
        reply = QMessageBox.question(self, "确认删除", f"删除 \"{code}\" 的强制指定?")
        if reply == QMessageBox.StandardButton.Yes:
            del self._force_rules[code]
            self._load_table()

    def _collect(self):
        for row in range(self._table.rowCount()):
            code_item = self._table.item(row, 0)
            combo = self._table.cellWidget(row, 1)
            pin_item = self._table.item(row, 2)
            pkg_item = self._table.item(row, 3)
            if code_item and combo:
                code = code_item.text()
                try:
                    pin = int(pin_item.text()) if pin_item and pin_item.text().strip() else 0
                except ValueError:
                    pin = 0
                pkg = pkg_item.text().strip() if pkg_item else ""
                self._force_rules[code] = {
                    "classification": combo.currentText(),
                    "pin_count": pin,
                    "package": pkg,
                }

    def _save(self):
        self._collect()
        save_force_rules(self._force_rules)
        QMessageBox.information(self, "保存成功", "强制指定规则已保存。")

    def _import_force(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入强制规则", "", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            if isinstance(imported, dict):
                self._force_rules.update(imported)
                self._load_table()
                QMessageBox.information(self, "导入成功", "规则已导入，请点击保存。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _export_force(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出强制规则", "force_rules_export.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            self._collect()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._force_rules, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
