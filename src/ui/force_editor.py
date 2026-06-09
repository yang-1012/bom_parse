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
        self.setMinimumSize(600, 450)
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
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["器件编码", "指定分类"])
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self._table)

        btns = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton("编辑")
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._delete)
        btns.addWidget(add_btn)
        btns.addWidget(edit_btn)
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
        for row, (code, cat) in enumerate(sorted(self._force_rules.items())):
            self._table.setItem(row, 0, QTableWidgetItem(code))
            combo = QComboBox()
            combo.addItems(self._categories)
            if cat in self._categories:
                combo.setCurrentText(cat)
            else:
                combo.setCurrentText(cat)
            self._table.setCellWidget(row, 1, combo)

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
        if ok2:
            self._force_rules[code] = cat
            self._load_table()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0:
            return
        code_item = self._table.item(row, 0)
        if not code_item:
            return
        code = code_item.text()
        combo = self._table.cellWidget(row, 1)
        new_cat = combo.currentText() if combo else ""
        if new_cat:
            self._force_rules[code] = new_cat

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

    def _save(self):
        # 先收集当前编辑中的 combo 值
        for row in range(self._table.rowCount()):
            code_item = self._table.item(row, 0)
            combo = self._table.cellWidget(row, 1)
            if code_item and combo:
                self._force_rules[code_item.text()] = combo.currentText()
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
            # 先收集 combo 值
            for row in range(self._table.rowCount()):
                code_item = self._table.item(row, 0)
                combo = self._table.cellWidget(row, 1)
                if code_item and combo:
                    self._force_rules[code_item.text()] = combo.currentText()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._force_rules, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
