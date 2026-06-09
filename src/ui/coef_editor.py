"""折算系数维护对话框"""

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

from src.services.config_service import load_coefficients, save_coefficients

logger = logging.getLogger("ParseApp")


class CoefficientEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("折算系数维护")
        self.setMinimumSize(500, 450)
        self._coefficients = load_coefficients()
        self._setup_ui()
        self._load_table()
        self.setModal(True)

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("封装 → 折算系数映射表，用于设置封装的折算倍数。"))

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["封装", "折算系数"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 100)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        btns = QHBoxLayout()
        add_btn = QPushButton("新建")
        add_btn.clicked.connect(self._add)
        edit_btn = QPushButton("编辑系数")
        edit_btn.clicked.connect(self._edit)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._delete)
        btns.addWidget(add_btn)
        btns.addWidget(edit_btn)
        btns.addWidget(del_btn)
        layout.addLayout(btns)

        bottom = QHBoxLayout()
        import_btn = QPushButton("导入规则")
        import_btn.clicked.connect(self._import_coeffs)
        export_btn = QPushButton("导出规则")
        export_btn.clicked.connect(self._export_coeffs)
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
        self._table.setRowCount(len(self._coefficients))
        for row, (pkg, val) in enumerate(sorted(self._coefficients.items())):
            self._table.setItem(row, 0, QTableWidgetItem(pkg))
            self._table.setItem(row, 1, QTableWidgetItem(str(val)))

    def _add(self):
        pkg, ok1 = QInputDialog.getText(self, "新建封装", "封装名称:")
        if not ok1 or not pkg.strip():
            return
        val, ok2 = QInputDialog.getDouble(
            self, "折算系数", f"\"{pkg}\" 的折算系数:", 1.0, 0.0, 100.0, 2
        )
        if ok2:
            self._coefficients[pkg.strip()] = val
            self._load_table()

    def _edit(self):
        row = self._table.currentRow()
        if row < 0:
            return
        pkg = self._table.item(row, 0).text()
        current = self._coefficients.get(pkg, 1.0)
        val, ok = QInputDialog.getDouble(
            self, "编辑系数", f"\"{pkg}\" 的折算系数:", current, 0.0, 100.0, 2
        )
        if ok:
            self._coefficients[pkg] = val
            self._load_table()

    def _delete(self):
        row = self._table.currentRow()
        if row < 0:
            return
        pkg = self._table.item(row, 0).text()
        reply = QMessageBox.question(self, "确认删除", f"删除 \"{pkg}\" 的折算系数?")
        if reply == QMessageBox.StandardButton.Yes:
            del self._coefficients[pkg]
            self._load_table()

    def _save(self):
        save_coefficients(self._coefficients)
        QMessageBox.information(self, "保存成功", "折算系数已保存。")

    def _import_coeffs(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入系数", "", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            if isinstance(imported, dict):
                self._coefficients.update({k: float(v) for k, v in imported.items()})
                self._load_table()
                QMessageBox.information(self, "导入成功", "系数已导入，请点击保存。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _export_coeffs(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出系数", "coefficients_export.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._coefficients, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
