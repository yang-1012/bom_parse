"""工具栏"""

import logging

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QToolBar, QWidget

logger = logging.getLogger("ParseApp")


class MainToolBar(QToolBar):
    import_bom = Signal()
    import_coord = Signal()
    start_parse = Signal()
    export_result = Signal()
    rule_maintain = Signal()
    force_edit = Signal()
    clear_data = Signal()

    def __init__(self, parent=None):
        super().__init__("工具栏", parent)
        self.setMovable(False)
        self._setup_actions()

    def _setup_actions(self):
        actions = [
            ("导入BOM", "导入 BOM 文件", self.import_bom),
            ("导入坐标", "导入坐标文件 (.txt)", self.import_coord),
            ("开始解析", "执行分类解析", self.start_parse),
            ("导出结果", "导出 Excel 报表", self.export_result),
            ("规则维护", "维护分类关键词规则", self.rule_maintain),
            ("强制指定", "维护强制指定规则", self.force_edit),
            ("清除数据", "清空当前数据", self.clear_data),
        ]

        for text, tooltip, signal in actions:
            action = QAction(text, self)
            action.setToolTip(tooltip)
            action.triggered.connect(signal.emit)
            self.addAction(action)
