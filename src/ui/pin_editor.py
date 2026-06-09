"""管脚数映射维护对话框"""

import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.services.config_service import load_pin_count_rules, save_pin_count_rules

logger = logging.getLogger("ParseApp")


class PinEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管脚数映射维护")
        self.setMinimumSize(500, 450)
        self._rules = load_pin_count_rules()
        self._setup_ui()
        self._populate_table()
        self.setModal(True)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel("封装 → 管脚数映射表，用于从封装名称自动推导管脚数。")
        layout.addWidget(info)

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["封装", "管脚数"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 100)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        # 操作按钮
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("新建")
        add_btn.clicked.connect(self._add)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._delete)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 底部按钮
        bottom = QHBoxLayout()
        import_btn = QPushButton("导入规则")
        import_btn.clicked.connect(self._import_rules)
        export_btn = QPushButton("导出规则")
        export_btn.clicked.connect(self._export_rules)
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

    def _populate_table(self):
        self._table.setRowCount(len(self._rules))
        for row, (pkg, count) in enumerate(sorted(self._rules.items())):
            item_pkg = QTableWidgetItem(pkg)
            item_count = QTableWidgetItem(str(count))
            self._table.setItem(row, 0, item_pkg)
            self._table.setItem(row, 1, item_count)

    def _add(self):
        pkg, ok = QInputDialog.getText(self, "新建映射", "封装名称:")
        if not ok or not pkg.strip():
            return
        pkg = pkg.strip().lower()
        count_str, ok = QInputDialog.getText(self, "管脚数", f"「{pkg}」的管脚数:")
        if not ok or not count_str.strip():
            return
        try:
            count = int(count_str.strip())
        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入整数。")
            return
        self._rules[pkg] = count
        self._populate_table()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0:
            return
        pkg = self._table.item(row, 0).text()
        reply = QMessageBox.question(self, "确认删除", f"确定要删除映射「{pkg}」吗？")
        if reply == QMessageBox.StandardButton.Yes:
            del self._rules[pkg]
            self._populate_table()

    def _save(self):
        save_pin_count_rules(self._rules)
        QMessageBox.information(self, "保存成功", "管脚数映射已保存。")

    def _import_rules(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入规则", "", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            for k, v in imported.items():
                if isinstance(v, (int, float)):
                    self._rules[k.lower()] = int(v)
            self._populate_table()
            QMessageBox.information(self, "导入成功", "规则已导入，请点击保存。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _export_rules(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出规则", "pin_count_rules_export.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._rules, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
