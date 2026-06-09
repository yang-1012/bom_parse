"""统一规则维护对话框 —— 标签页整合四种规则"""

import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from src.models.classification import ClassificationRule
from src.services.config_service import (
    get_classifications,
    load_classification_rules,
    save_classification_rules,
    update_classifications,
    load_force_rules,
    save_force_rules,
    load_coefficients,
    save_coefficients,
    load_pin_count_rules,
    save_pin_count_rules,
)

logger = logging.getLogger("ParseApp")


class RuleMaintainDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("规则维护")
        self.setMinimumSize(750, 550)
        self.setModal(True)

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._setup_classification_tab()
        self._setup_force_tab()
        self._setup_coefficient_tab()
        self._setup_pin_count_tab()

        # 全局底部按钮
        bottom = QHBoxLayout()
        bottom.addStretch()
        save_all_btn = QPushButton("全部保存")
        save_all_btn.clicked.connect(self._save_all)
        save_all_btn.setStyleSheet("font-weight: bold;")
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        bottom.addWidget(save_all_btn)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

    # ================================================================
    # Tab 1: 分类规则
    # ================================================================

    def _setup_classification_tab(self):
        tab = QWidget()
        self._tabs.addTab(tab, "分类规则")

        self._cls_data = load_classification_rules()
        self._cls_rules = get_classifications(self._cls_data)
        self._selected_category = None

        outer = QVBoxLayout(tab)
        main_layout = QHBoxLayout()

        # 左侧：分类列表
        left = QVBoxLayout()
        self._cls_cat_list = QListWidget()
        self._cls_cat_list.currentItemChanged.connect(self._on_category_changed)
        left.addWidget(self._cls_cat_list)

        cat_btns = QHBoxLayout()
        add_cat_btn = QPushButton("新建分类")
        add_cat_btn.clicked.connect(self._cls_add_category)
        del_cat_btn = QPushButton("删除分类")
        del_cat_btn.clicked.connect(self._cls_delete_category)
        cat_btns.addWidget(add_cat_btn)
        cat_btns.addWidget(del_cat_btn)
        left.addLayout(cat_btns)
        main_layout.addLayout(left, 1)

        # 右侧：关键词管理
        right = QVBoxLayout()

        right.addWidget(QLabel("包含关键词（命中任一即归类）:"))
        self._cls_kw_list = QListWidget()
        right.addWidget(self._cls_kw_list)

        kw_btns = QHBoxLayout()
        add_kw_btn = QPushButton("添加")
        add_kw_btn.clicked.connect(self._cls_add_keyword)
        del_kw_btn = QPushButton("删除")
        del_kw_btn.clicked.connect(self._cls_delete_keyword)
        kw_btns.addWidget(add_kw_btn)
        kw_btns.addWidget(del_kw_btn)
        right.addLayout(kw_btns)

        right.addWidget(QLabel("排除关键词（命中则跳过该分类）:"))
        self._cls_ex_list = QListWidget()
        right.addWidget(self._cls_ex_list)

        ex_btns = QHBoxLayout()
        add_ex_btn = QPushButton("添加")
        add_ex_btn.clicked.connect(self._cls_add_exclude)
        del_ex_btn = QPushButton("删除")
        del_ex_btn.clicked.connect(self._cls_delete_exclude)
        ex_btns.addWidget(add_ex_btn)
        ex_btns.addWidget(del_ex_btn)
        right.addLayout(ex_btns)

        main_layout.addLayout(right, 2)
        outer.addLayout(main_layout)

        # 底部操作按钮
        bottom = QHBoxLayout()
        import_btn = QPushButton("导入规则")
        import_btn.clicked.connect(self._cls_import)
        export_btn = QPushButton("导出规则")
        export_btn.clicked.connect(self._cls_export)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._cls_save)
        save_btn.setStyleSheet("font-weight: bold;")
        bottom.addWidget(import_btn)
        bottom.addWidget(export_btn)
        bottom.addStretch()
        bottom.addWidget(save_btn)
        outer.addLayout(bottom)

        self._cls_load_categories()

    def _cls_load_categories(self):
        self._cls_cat_list.clear()
        for name in sorted(self._cls_rules.keys()):
            self._cls_cat_list.addItem(QListWidgetItem(name))

    def _on_category_changed(self, current, previous):
        if not current:
            self._selected_category = None
            self._cls_kw_list.clear()
            self._cls_ex_list.clear()
            return
        name = current.text()
        self._selected_category = name
        rule = self._cls_rules.get(name)
        self._cls_kw_list.clear()
        self._cls_ex_list.clear()
        if rule:
            for kw in sorted(rule.keywords):
                self._cls_kw_list.addItem(kw)
            for ek in sorted(rule.exclude_keywords):
                self._cls_ex_list.addItem(ek)

    def _cls_add_category(self):
        name, ok = QInputDialog.getText(self, "新建分类", "分类名称:")
        if ok and name.strip():
            name = name.strip()
            if name not in self._cls_rules:
                self._cls_rules[name] = ClassificationRule(name=name)
                self._cls_load_categories()

    def _cls_delete_category(self):
        if not self._selected_category:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除分类 \"{self._selected_category}\" 吗？"
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self._cls_rules[self._selected_category]
            self._selected_category = None
            self._cls_kw_list.clear()
            self._cls_ex_list.clear()
            self._cls_load_categories()

    def _cls_add_keyword(self):
        if not self._selected_category:
            return
        kw, ok = QInputDialog.getText(self, "添加关键词", "关键词:")
        if ok and kw.strip():
            rule = self._cls_rules[self._selected_category]
            if kw.strip() not in rule.keywords:
                rule.keywords.append(kw.strip())
                self._cls_kw_list.addItem(kw.strip())

    def _cls_delete_keyword(self):
        if not self._selected_category:
            return
        item = self._cls_kw_list.currentItem()
        if item:
            rule = self._cls_rules[self._selected_category]
            if item.text() in rule.keywords:
                rule.keywords.remove(item.text())
            self._cls_kw_list.takeItem(self._cls_kw_list.row(item))

    def _cls_add_exclude(self):
        if not self._selected_category:
            return
        kw, ok = QInputDialog.getText(self, "添加排除关键词", "关键词:")
        if ok and kw.strip():
            rule = self._cls_rules[self._selected_category]
            if kw.strip() not in rule.exclude_keywords:
                rule.exclude_keywords.append(kw.strip())
                self._cls_ex_list.addItem(kw.strip())

    def _cls_delete_exclude(self):
        if not self._selected_category:
            return
        item = self._cls_ex_list.currentItem()
        if item:
            rule = self._cls_rules[self._selected_category]
            if item.text() in rule.exclude_keywords:
                rule.exclude_keywords.remove(item.text())
            self._cls_ex_list.takeItem(self._cls_ex_list.row(item))

    def _cls_save(self):
        update_classifications(self._cls_data, self._cls_rules)
        save_classification_rules(self._cls_data)
        QMessageBox.information(self, "保存成功", "分类规则已保存。")

    def _cls_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入分类规则", "", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            if "classifications" in imported:
                self._cls_data["classifications"] = imported["classifications"]
                self._cls_rules = get_classifications(self._cls_data)
                self._cls_load_categories()
                QMessageBox.information(self, "导入成功", "分类规则已导入，请点击下方保存按钮。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _cls_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出分类规则", "classification_rules_export.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            update_classifications(self._cls_data, self._cls_rules)
            export_data = {"classifications": self._cls_data["classifications"]}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # ================================================================
    # Tab 2: 强制指定
    # ================================================================

    def _setup_force_tab(self):
        tab = QWidget()
        self._tabs.addTab(tab, "强制指定")

        self._force_rules = load_force_rules()
        rules_data = load_classification_rules()
        classifications = get_classifications(rules_data)
        self._force_categories = list(classifications.keys())

        layout = QVBoxLayout(tab)

        self._force_table = QTableWidget()
        self._force_table.setColumnCount(4)
        self._force_table.setHorizontalHeaderLabels(["器件编码", "分类", "管脚数", "封装"])
        self._force_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            self._force_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        self._force_table.setColumnWidth(1, 120)
        self._force_table.setColumnWidth(2, 80)
        self._force_table.setColumnWidth(3, 120)
        self._force_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._force_table.setAlternatingRowColors(True)
        self._force_table.verticalHeader().setVisible(False)
        layout.addWidget(self._force_table)

        btns = QHBoxLayout()
        add_btn = QPushButton("添加")
        add_btn.clicked.connect(self._force_add)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._force_delete)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        layout.addLayout(btns)

        # 底部操作按钮
        bottom = QHBoxLayout()
        import_btn = QPushButton("导入")
        import_btn.clicked.connect(self._force_import)
        export_btn = QPushButton("导出")
        export_btn.clicked.connect(self._force_export)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._force_save)
        save_btn.setStyleSheet("font-weight: bold;")
        bottom.addWidget(import_btn)
        bottom.addWidget(export_btn)
        bottom.addStretch()
        bottom.addWidget(save_btn)
        layout.addLayout(bottom)

        self._force_load_table()

    def _force_load_table(self):
        self._force_table.setRowCount(len(self._force_rules))
        for row, (code, entry) in enumerate(sorted(self._force_rules.items())):
            item = QTableWidgetItem(code)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._force_table.setItem(row, 0, item)
            combo = QComboBox()
            combo.addItems(self._force_categories)
            cat = entry.get("classification", "未分类") if isinstance(entry, dict) else entry
            if cat in self._force_categories:
                combo.setCurrentText(cat)
            else:
                combo.addItem(cat)
                combo.setCurrentText(cat)
            self._force_table.setCellWidget(row, 1, combo)

            pin_count = entry.get("pin_count", 0) if isinstance(entry, dict) else 0
            self._force_table.setItem(row, 2, QTableWidgetItem(str(pin_count) if pin_count else ""))

            pkg = entry.get("package", "") if isinstance(entry, dict) else ""
            self._force_table.setItem(row, 3, QTableWidgetItem(pkg))

    def _force_collect(self):
        for row in range(self._force_table.rowCount()):
            code_item = self._force_table.item(row, 0)
            combo = self._force_table.cellWidget(row, 1)
            pin_item = self._force_table.item(row, 2)
            pkg_item = self._force_table.item(row, 3)
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

    def _force_add(self):
        code, ok1 = QInputDialog.getText(self, "添加强制指定", "器件编码:")
        if not ok1 or not code.strip():
            return
        code = code.strip()
        if code in self._force_rules:
            QMessageBox.warning(self, "重复", f"\"{code}\" 已存在强制指定规则。")
            return
        cat, ok2 = QInputDialog.getItem(
            self, "选择分类", "分类:", self._force_categories, 0, False
        )
        if ok2:
            self._force_rules[code] = {"classification": cat, "pin_count": 0, "package": ""}
            self._force_load_table()

    def _force_delete(self):
        row = self._force_table.currentRow()
        if row < 0:
            return
        code_item = self._force_table.item(row, 0)
        if not code_item:
            return
        code = code_item.text()
        reply = QMessageBox.question(self, "确认删除", f"删除 \"{code}\" 的强制指定?")
        if reply == QMessageBox.StandardButton.Yes:
            del self._force_rules[code]
            self._force_load_table()

    def _force_save(self):
        self._force_collect()
        save_force_rules(self._force_rules)
        QMessageBox.information(self, "保存成功", "强制指定规则已保存。")

    def _force_import(self):
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
                self._force_load_table()
                QMessageBox.information(self, "导入成功", "规则已导入，请点击下方保存按钮。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _force_export(self):
        self._force_collect()
        path, _ = QFileDialog.getSaveFileName(
            self, "导出强制规则", "force_rules_export.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._force_rules, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # ================================================================
    # Tab 3: 折算系数
    # ================================================================

    def _setup_coefficient_tab(self):
        tab = QWidget()
        self._tabs.addTab(tab, "折算系数")

        self._coefficients = load_coefficients()

        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("封装 → 折算系数映射表，用于设置封装的折算倍数。"))

        self._coef_table = QTableWidget(0, 2)
        self._coef_table.setHorizontalHeaderLabels(["封装", "折算系数"])
        self._coef_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._coef_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._coef_table.setColumnWidth(1, 100)
        self._coef_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._coef_table.setAlternatingRowColors(True)
        self._coef_table.verticalHeader().setVisible(False)
        layout.addWidget(self._coef_table)

        btns = QHBoxLayout()
        add_btn = QPushButton("新建")
        add_btn.clicked.connect(self._coef_add)
        edit_btn = QPushButton("编辑系数")
        edit_btn.clicked.connect(self._coef_edit)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._coef_delete)
        btns.addWidget(add_btn)
        btns.addWidget(edit_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        layout.addLayout(btns)

        # 底部操作按钮
        bottom = QHBoxLayout()
        import_btn = QPushButton("导入规则")
        import_btn.clicked.connect(self._coef_import)
        export_btn = QPushButton("导出规则")
        export_btn.clicked.connect(self._coef_export)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._coef_save)
        save_btn.setStyleSheet("font-weight: bold;")
        bottom.addWidget(import_btn)
        bottom.addWidget(export_btn)
        bottom.addStretch()
        bottom.addWidget(save_btn)
        layout.addLayout(bottom)

        self._coef_load_table()

    def _coef_load_table(self):
        self._coef_table.setRowCount(len(self._coefficients))
        for row, (pkg, val) in enumerate(sorted(self._coefficients.items())):
            self._coef_table.setItem(row, 0, QTableWidgetItem(pkg))
            self._coef_table.setItem(row, 1, QTableWidgetItem(str(val)))

    def _coef_add(self):
        pkg, ok1 = QInputDialog.getText(self, "新建封装", "封装名称:")
        if not ok1 or not pkg.strip():
            return
        val, ok2 = QInputDialog.getDouble(
            self, "折算系数", f"\"{pkg}\" 的折算系数:", 1.0, 0.0, 100.0, 2
        )
        if ok2:
            self._coefficients[pkg.strip()] = val
            self._coef_load_table()

    def _coef_edit(self):
        row = self._coef_table.currentRow()
        if row < 0:
            return
        pkg = self._coef_table.item(row, 0).text()
        current = self._coefficients.get(pkg, 1.0)
        val, ok = QInputDialog.getDouble(
            self, "编辑系数", f"\"{pkg}\" 的折算系数:", current, 0.0, 100.0, 2
        )
        if ok:
            self._coefficients[pkg] = val
            self._coef_load_table()

    def _coef_delete(self):
        row = self._coef_table.currentRow()
        if row < 0:
            return
        pkg = self._coef_table.item(row, 0).text()
        reply = QMessageBox.question(self, "确认删除", f"删除 \"{pkg}\" 的折算系数?")
        if reply == QMessageBox.StandardButton.Yes:
            del self._coefficients[pkg]
            self._coef_load_table()

    def _coef_save(self):
        save_coefficients(self._coefficients)
        QMessageBox.information(self, "保存成功", "折算系数已保存。")

    def _coef_import(self):
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
                self._coef_load_table()
                QMessageBox.information(self, "导入成功", "系数已导入，请点击下方保存按钮。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _coef_export(self):
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

    # ================================================================
    # Tab 4: 管脚数映射
    # ================================================================

    def _setup_pin_count_tab(self):
        tab = QWidget()
        self._tabs.addTab(tab, "管脚数映射")

        self._pin_rules = load_pin_count_rules()

        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("封装 → 管脚数映射表，用于从封装名称自动推导管脚数。"))

        self._pin_table = QTableWidget(0, 2)
        self._pin_table.setHorizontalHeaderLabels(["封装", "管脚数"])
        self._pin_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._pin_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._pin_table.setColumnWidth(1, 100)
        self._pin_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._pin_table.setAlternatingRowColors(True)
        self._pin_table.verticalHeader().setVisible(False)
        layout.addWidget(self._pin_table)

        btns = QHBoxLayout()
        add_btn = QPushButton("新建")
        add_btn.clicked.connect(self._pin_add)
        del_btn = QPushButton("删除")
        del_btn.clicked.connect(self._pin_delete)
        btns.addWidget(add_btn)
        btns.addWidget(del_btn)
        btns.addStretch()
        layout.addLayout(btns)

        # 底部操作按钮
        bottom = QHBoxLayout()
        import_btn = QPushButton("导入规则")
        import_btn.clicked.connect(self._pin_import)
        export_btn = QPushButton("导出规则")
        export_btn.clicked.connect(self._pin_export)
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self._pin_save)
        save_btn.setStyleSheet("font-weight: bold;")
        bottom.addWidget(import_btn)
        bottom.addWidget(export_btn)
        bottom.addStretch()
        bottom.addWidget(save_btn)
        layout.addLayout(bottom)

        self._pin_load_table()

    def _pin_load_table(self):
        self._pin_table.setRowCount(len(self._pin_rules))
        for row, (pkg, count) in enumerate(sorted(self._pin_rules.items())):
            self._pin_table.setItem(row, 0, QTableWidgetItem(pkg))
            self._pin_table.setItem(row, 1, QTableWidgetItem(str(count)))

    def _pin_add(self):
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
        self._pin_rules[pkg] = count
        self._pin_load_table()

    def _pin_delete(self):
        row = self._pin_table.currentRow()
        if row < 0:
            return
        pkg = self._pin_table.item(row, 0).text()
        reply = QMessageBox.question(self, "确认删除", f"确定要删除映射「{pkg}」吗？")
        if reply == QMessageBox.StandardButton.Yes:
            del self._pin_rules[pkg]
            self._pin_load_table()

    def _pin_save(self):
        save_pin_count_rules(self._pin_rules)
        QMessageBox.information(self, "保存成功", "管脚数映射已保存。")

    def _pin_import(self):
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
                    self._pin_rules[k.lower()] = int(v)
            self._pin_load_table()
            QMessageBox.information(self, "导入成功", "规则已导入，请点击下方保存按钮。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _pin_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出规则", "pin_count_rules_export.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._pin_rules, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    # ================================================================
    # 全局操作（"全部保存" 和 "关闭"）
    # ================================================================

    def _save_all(self):
        update_classifications(self._cls_data, self._cls_rules)
        save_classification_rules(self._cls_data)
        self._force_collect()
        save_force_rules(self._force_rules)
        save_coefficients(self._coefficients)
        save_pin_count_rules(self._pin_rules)
        QMessageBox.information(self, "保存成功", "所有规则已保存。")
