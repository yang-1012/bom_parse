"""分类规则维护对话框"""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.models.classification import ClassificationRule
from src.services.config_service import (
    get_classifications,
    load_classification_rules,
    save_classification_rules,
    update_classifications,
)

logger = logging.getLogger("ParseApp")


class RuleEditorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("分类规则维护")
        self.setMinimumSize(700, 500)
        self._data = load_classification_rules()
        self._rules = get_classifications(self._data)
        self._selected_category = None
        self._setup_ui()
        self._load_categories()
        self.setModal(True)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)

        # 左侧：分类列表
        left = QVBoxLayout()
        self._cat_list = QListWidget()
        self._cat_list.currentItemChanged.connect(self._on_category_changed)
        left.addWidget(self._cat_list)

        cat_btns = QHBoxLayout()
        add_btn = QPushButton("新建分类")
        add_btn.clicked.connect(self._add_category)
        del_btn = QPushButton("删除分类")
        del_btn.clicked.connect(self._delete_category)
        cat_btns.addWidget(add_btn)
        cat_btns.addWidget(del_btn)
        left.addLayout(cat_btns)

        main_layout.addLayout(left, 1)

        # 右侧：关键词管理
        right = QVBoxLayout()

        kw_label = QLabel("包含关键词（命中任一即归类）:")
        right.addWidget(kw_label)
        self._kw_list = QListWidget()
        right.addWidget(self._kw_list)

        kw_btns = QHBoxLayout()
        add_kw_btn = QPushButton("添加")
        add_kw_btn.clicked.connect(self._add_keyword)
        del_kw_btn = QPushButton("删除")
        del_kw_btn.clicked.connect(self._delete_keyword)
        kw_btns.addWidget(add_kw_btn)
        kw_btns.addWidget(del_kw_btn)
        right.addLayout(kw_btns)

        ex_label = QLabel("排除关键词（命中则跳过该分类）:")
        right.addWidget(ex_label)
        self._ex_list = QListWidget()
        right.addWidget(self._ex_list)

        ex_btns = QHBoxLayout()
        add_ex_btn = QPushButton("添加")
        add_ex_btn.clicked.connect(self._add_exclude)
        del_ex_btn = QPushButton("删除")
        del_ex_btn.clicked.connect(self._delete_exclude)
        ex_btns.addWidget(add_ex_btn)
        ex_btns.addWidget(del_ex_btn)
        right.addLayout(ex_btns)

        main_layout.addLayout(right, 2)

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

        main_widget = QWidget()
        main_widget.setLayout(main_layout)

        outer = QVBoxLayout(self)
        outer.addWidget(main_widget)
        outer.addLayout(bottom)

    def _load_categories(self):
        self._cat_list.clear()
        for name in sorted(self._rules.keys()):
            item = QListWidgetItem(name)
            self._cat_list.addItem(item)

    def _on_category_changed(self, current, previous):
        if not current:
            self._selected_category = None
            self._kw_list.clear()
            self._ex_list.clear()
            return

        name = current.text()
        self._selected_category = name
        rule = self._rules.get(name)
        self._kw_list.clear()
        self._ex_list.clear()
        if rule:
            for kw in sorted(rule.keywords):
                self._kw_list.addItem(kw)
            for ek in sorted(rule.exclude_keywords):
                self._ex_list.addItem(ek)

    def _add_category(self):
        name, ok = QInputDialog.getText(self, "新建分类", "分类名称:")
        if ok and name.strip():
            name = name.strip()
            if name not in self._rules:
                self._rules[name] = ClassificationRule(name=name)
                self._load_categories()

    def _delete_category(self):
        if not self._selected_category:
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除分类 \"{self._selected_category}\" 吗？"
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self._rules[self._selected_category]
            self._selected_category = None
            self._kw_list.clear()
            self._ex_list.clear()
            self._load_categories()

    def _add_keyword(self):
        if not self._selected_category:
            return
        kw, ok = QInputDialog.getText(self, "添加关键词", "关键词:")
        if ok and kw.strip():
            rule = self._rules[self._selected_category]
            if kw.strip() not in rule.keywords:
                rule.keywords.append(kw.strip())
                self._kw_list.addItem(kw.strip())

    def _delete_keyword(self):
        if not self._selected_category:
            return
        item = self._kw_list.currentItem()
        if item:
            rule = self._rules[self._selected_category]
            if item.text() in rule.keywords:
                rule.keywords.remove(item.text())
            self._kw_list.takeItem(self._kw_list.row(item))

    def _add_exclude(self):
        if not self._selected_category:
            return
        kw, ok = QInputDialog.getText(self, "添加排除关键词", "关键词:")
        if ok and kw.strip():
            rule = self._rules[self._selected_category]
            if kw.strip() not in rule.exclude_keywords:
                rule.exclude_keywords.append(kw.strip())
                self._ex_list.addItem(kw.strip())

    def _delete_exclude(self):
        if not self._selected_category:
            return
        item = self._ex_list.currentItem()
        if item:
            rule = self._rules[self._selected_category]
            if item.text() in rule.exclude_keywords:
                rule.exclude_keywords.remove(item.text())
            self._ex_list.takeItem(self._ex_list.row(item))

    def _save(self):
        update_classifications(self._data, self._rules)
        save_classification_rules(self._data)
        QMessageBox.information(self, "保存成功", "分类规则已保存。")

    def _import_rules(self):
        from PySide6.QtWidgets import QFileDialog
        import json

        path, _ = QFileDialog.getOpenFileName(
            self, "导入规则", "", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            if "classifications" in imported:
                self._data["classifications"] = imported["classifications"]
                self._rules = get_classifications(self._data)
                self._load_categories()
                QMessageBox.information(self, "导入成功", "分类规则已导入，请点击保存。")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _export_rules(self):
        from PySide6.QtWidgets import QFileDialog
        import json

        path, _ = QFileDialog.getSaveFileName(
            self, "导出规则", "classification_rules_export.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            update_classifications(self._data, self._rules)
            export_data = {"classifications": self._data["classifications"]}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "导出成功", f"已导出到 {path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
