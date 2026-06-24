"""主窗口"""

import logging
import os
import threading

import pandas as pd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QProgressBar,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.models.device import Device
from src.services.config_service import load_classification_rules, load_coefficients
from src.ui.column_map_dialog import ColumnMapDialog
from src.ui.coef_editor import CoefficientEditorDialog
from src.ui.force_editor import ForceEditorDialog
from src.ui.pin_editor import PinEditorDialog
from src.ui.unified_confirm_dialog import UnifiedConfirmDialog
from src.ui.preview_table import PreviewTable
from src.ui.rule_editor import RuleEditorDialog
from src.ui.rule_maintain_dialog import RuleMaintainDialog
from src.ui.stats_panel import StatsPanel
from src.ui.toolbar import MainToolBar
from src.ui.workers import (
    ClassifyWorker,
    ExportWorker,
    LoadBomWorker,
    LoadCoordinateWorker,
)

logger = logging.getLogger("ParseApp")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BOM 解析分类工具")
        self.setMinimumSize(1100, 650)

        self._bom_raw: list[dict] = []
        self._bom_column_map: dict = {}
        self._coord_df: pd.DataFrame | None = None
        self._devices: list[Device] = []
        self._bom_path: str = ""

        self._setup_menu()
        self._setup_ui()
        self._setup_statusbar()
        self._connect_signals()

        logger.info("主窗口初始化完成")

    def _setup_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("文件(&F)")
        file_menu.addAction("导入BOM(&B)", self._on_import_bom)
        file_menu.addAction("导入坐标(&C)", self._on_import_coord)
        file_menu.addSeparator()
        file_menu.addAction("导出结果(&E)", self._on_export)
        file_menu.addSeparator()
        file_menu.addAction("退出(&Q)", self.close)

        edit_menu = mb.addMenu("编辑(&E)")
        edit_menu.addAction("分类规则维护(&R)", self._on_rule_maintain)
        edit_menu.addAction("折算系数维护(&C)", self._on_coef_maintain)
        edit_menu.addAction("强制指定维护(&F)", self._on_force_maintain)
        edit_menu.addAction("管脚数映射维护(&P)", self._on_pin_maintain)
        edit_menu.addSeparator()
        edit_menu.addAction("重新分类(&X)", self._on_parse)

        help_menu = mb.addMenu("帮助(&H)")
        help_menu.addAction("关于(&A)", self._on_about)

    def _setup_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 工具栏
        self._toolbar = MainToolBar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._toolbar)

        # Notebook tab 切换
        self._tabs = QTabWidget()

        # 数据预览 Tab
        self._preview_table = PreviewTable()
        self._tabs.addTab(self._preview_table, "数据预览")

        # 统计 Tab
        self._stats_panel = StatsPanel()
        self._tabs.addTab(self._stats_panel, "分类统计")

        layout.addWidget(self._tabs)

        # 进度条（默认隐藏）
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self.setCentralWidget(central)

    def _setup_statusbar(self):
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._status_label = QLabel("就绪")
        self._statusbar.addWidget(self._status_label)

    def _connect_signals(self):
        self._toolbar.import_bom.connect(self._on_import_bom)
        self._toolbar.import_coord.connect(self._on_import_coord)
        self._toolbar.start_parse.connect(self._on_parse)
        self._toolbar.export_result.connect(self._on_export)
        self._toolbar.rule_maintain.connect(self._on_rule_maintain)
        self._toolbar.clear_data.connect(self._on_clear)
        self._preview_table.data_changed.connect(self._on_data_changed)

    def _set_status(self, msg: str):
        self._status_label.setText(msg)
        logger.info(msg)

    # ---- slots ----

    def _on_import_bom(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入 BOM 文件", "",
            "表格文件 (*.csv *.txt *.xlsx *.xls);;所有文件 (*.*)"
        )
        if not path:
            return

        self._bom_path = path
        self._set_status(f"正在加载 BOM: {os.path.basename(path)}")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)

        self._bom_worker = LoadBomWorker(path)
        self._bom_worker.finished_signal.connect(self._on_bom_loaded)
        self._bom_worker.error_signal.connect(self._on_error)
        self._bom_worker.finished.connect(lambda: self._progress.setVisible(False))
        self._bom_worker.start()

    def _on_bom_loaded(self, devices_raw: list[dict], column_map: dict):
        self._bom_raw = devices_raw
        self._bom_column_map = column_map

        # 获取所有原始列名（已匹配 + 未匹配）
        raw_columns = list(dict.fromkeys(
            k for d in devices_raw for k in d.keys()
        )) if devices_raw else list(column_map.keys())

        # 弹出列映射确认对话框
        dlg = ColumnMapDialog(column_map, raw_columns, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._bom_column_map = dlg.get_column_map()
            self._set_status(
                f"BOM 加载完成: {len(devices_raw)} 条记录, "
                f"匹配列: {list(self._bom_column_map.values())}"
            )
        else:
            # 用户取消，清空数据
            self._bom_raw = []
            self._bom_column_map = {}
            self._set_status("已取消 BOM 导入")

    def _on_import_coord(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入坐标文件", "",
            "文本文件 (*.txt *.csv);;所有文件 (*.*)"
        )
        if not path:
            return

        self._set_status(f"正在加载坐标文件: {os.path.basename(path)}")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)

        self._coord_worker = LoadCoordinateWorker(path)
        self._coord_worker.finished_signal.connect(self._on_coord_loaded)
        self._coord_worker.error_signal.connect(self._on_error)
        self._coord_worker.finished.connect(lambda: self._progress.setVisible(False))
        self._coord_worker.start()

    def _on_coord_loaded(self, df: pd.DataFrame):
        self._coord_df = df
        self._set_status(f"坐标文件加载完成: {len(df)} 行")

    def _on_parse(self):
        if not self._bom_raw:
            QMessageBox.warning(self, "提示", "请先导入 BOM 文件。")
            return

        self._set_status("正在执行分类解析...")
        self._progress.setVisible(True)
        self._progress.setRange(0, len(self._bom_raw))

        self._classify_worker = ClassifyWorker(
            self._bom_raw, self._bom_column_map,
            self._coord_df if self._coord_df is not None else pd.DataFrame()
        )
        self._classify_worker.progress_signal.connect(self._on_progress)
        self._classify_worker.finished_signal.connect(self._on_classified)
        self._classify_worker.error_signal.connect(self._on_error)
        self._classify_worker.finished.connect(lambda: self._progress.setVisible(False))
        self._classify_worker.start()

    def _on_classified(self, devices: list[Device]):
        self._devices = devices
        self._preview_table.set_coefficients(load_coefficients())
        self._preview_table.set_devices(devices)
        self._stats_panel.update_stats(devices)

        unclassified = sum(1 for d in devices if d.classification == "未分类")
        unknown_pins = sum(1 for d in devices if d.pin_count == 0 and d.package.strip())
        self._set_status(
            f"分类完成: {len(devices)} 条, "
            f"未分类: {unclassified}, 管脚数待确认: {unknown_pins}"
        )

        if unknown_pins > 0 or unclassified > 0:
            parts = []
            if unknown_pins > 0:
                parts.append(f"{unknown_pins} 个器件的管脚数无法从封装推导")
            if unclassified > 0:
                parts.append(f"{unclassified} 个器件未能自动分类")
            reply = QMessageBox.question(
                self, "器件待确认",
                f"有{'、'.join(parts)}，是否现在进行人工确认？"
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._on_unified_confirm()

        self._tabs.setCurrentIndex(0)

    def _on_progress(self, current: int, total: int):
        self._progress.setRange(0, total)
        self._progress.setValue(current)

    def _on_unified_confirm(self):
        dlg = UnifiedConfirmDialog(self._devices, self)
        dlg.exec()
        self._preview_table.set_devices(self._devices)
        self._stats_panel.update_stats(self._devices)
        self._set_status("人工确认完成，数据已更新。")

    def _on_export(self):
        if not self._devices:
            QMessageBox.warning(self, "提示", "请先执行分类解析。")
            return

        source = self._bom_path or "未命名"
        self._set_status("正在导出 Excel...")
        self._progress.setVisible(True)
        self._progress.setRange(0, 0)

        self._export_worker = ExportWorker(self._devices, source)
        self._export_worker.finished_signal.connect(self._on_exported)
        self._export_worker.error_signal.connect(self._on_error)
        self._export_worker.finished.connect(lambda: self._progress.setVisible(False))
        self._export_worker.start()

    def _on_exported(self, output_path: str):
        self._set_status(f"导出完成: {output_path}")
        QMessageBox.information(self, "导出成功", f"Excel 已导出到:\n{output_path}")

    def _on_rule_maintain(self):
        dlg = RuleMaintainDialog(self)
        dlg.exec()

    def _on_coef_maintain(self):
        dlg = CoefficientEditorDialog(self)
        dlg.exec()

    def _on_force_maintain(self):
        dlg = ForceEditorDialog(self)
        dlg.exec()

    def _on_pin_maintain(self):
        dlg = PinEditorDialog(self)
        dlg.exec()

    def _on_clear(self):
        reply = QMessageBox.question(self, "确认清除", "确定要清除所有数据吗？")
        if reply == QMessageBox.StandardButton.Yes:
            self._bom_raw = []
            self._bom_column_map = {}
            self._coord_df = None
            self._devices = []
            self._preview_table.setRowCount(0)
            self._stats_panel.update_stats([])
            self._bom_path = ""
            self._set_status("数据已清除")

    def _on_data_changed(self):
        self._stats_panel.update_stats(self._devices)
        self._set_status("数据已修改，统计已更新。")

    def _on_about(self):
        QMessageBox.about(
            self, "关于",
            "BOM 解析分类工具 v1.0\n\n"
            "根据坐标文件自动分类 B/T 面器件数。\n"
            "支持三级匹配策略：强制指定 > 历史记录 > 关键词规则。"
        )

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._set_status(f"错误: {msg}")
        QMessageBox.critical(self, "错误", msg)
