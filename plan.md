# 坐标文件解析分类软件 - 实现计划

## Context
根据 readme.md 需求，设计一款带 GUI 的解析软件，用于解析 BOM/坐标文件，自动将器件分类为 SMT/插件/压接等类别，判断器件位于 B/T 面，并导出 Excel 报表。

---

## 技术选型

| 层级 | 技术 | 原因 |
|------|------|------|
| GUI | tkinter + ttk | Python 内置库，无需额外安装，Treeview 满足表格需求 |
| 数据处理 | pandas | CSV/TXT/Excel 读写高效 |
| Excel 导出 | openpyxl | 支持样式、多 Sheet、公式 |
| 配置持久化 | JSON | classification_rules.json + force_rules.json + coefficients.json |
| 日志 | 内置 logging | 单例 Logger，控制台 INFO + 文件 DEBUG |
| 并发 | threading.Thread | 后台执行耗时操作，`root.after()` 回主线程更新 UI |

---

## 项目结构

```
prase/
├── main.py                         # 入口，启动 GUI
├── requirements.txt                # 依赖（pandas, openpyxl）
├── plan.md                         # 本计划文档
├── readme.md                       # 需求文档
├── classification_rules.json       # 主配置：分类规则 + 字段别名 + 分类历史
├── config/
│   ├── force_rules.json            # 强制指定规则（器件编码 → 分类）
│   └── coefficients.json           # 折算系数（封装 → 系数值）
├── log/                            # 日志输出目录
├── src/
│   ├── __init__.py
│   ├── logger.py                   # 单例日志系统
│   ├── models/
│   │   ├── __init__.py
│   │   ├── device.py               # 器件数据模型 (dataclass)
│   │   └── config_models.py        # 配置相关模型
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── bom_parser.py           # BOM 文件解析器（含模糊列名匹配）
│   │   ├── coordinate_parser.py    # 坐标文件(.txt)解析器
│   │   └── encoding_detector.py    # 编码自动检测
│   ├── classifiers/
│   │   ├── __init__.py
│   │   ├── rule_engine.py          # 三级匹配引擎（强制 > 历史 > 关键词）
│   │   └── side_detector.py        # B/T 面检测（SYM_MIRROR: YES→B, NO→T）
│   ├── services/
│   │   ├── __init__.py
│   │   ├── config_service.py       # 读写所有 JSON 配置文件
│   │   └── export_service.py       # Excel 导出服务
│   └── ui/
│       ├── __init__.py
│       ├── app.py                  # 主窗口（菜单、工具栏、Notebook、状态栏）
│       ├── dialogs.py              # 全部对话框
│       └── workers.py              # 后台线程
```

---

## 配置文件说明

### 1. classification_rules.json（已提供，根目录）

```json
{
  "version": "1.0",
  "classifications": {
    "SMT器件": { "keywords": [...], "exclude_keywords": [...] },
    "插件器件": { "keywords": [...], "exclude_keywords": [...] },
    "压接器件": { "keywords": [...], "exclude_keywords": [...] },
    "装配器件": { "keywords": [...], "exclude_keywords": [...] },
    "通孔回流": { "keywords": [...], "exclude_keywords": [...] },
    "辅料":     { "keywords": [...], "exclude_keywords": [...] },
    "测试分类": { "keywords": [...], "exclude_keywords": [...] }
  },
  "field_aliases": {
    "器件编码": ["器件编码", "Part Number", "PN", "料号", ...],
    "器件描述": ["器件描述", "Description", "规格", ...],
    "位号":     ["位号", "Reference", "Ref Des", ...],
    "数量":     ["数量", "Qty", "Quantity", ...],
    "单位":     ["单位", "Unit", "Uom", ...],
    "封装":     ["封装", "Package", "Footprint", ...]
  },
  "classification_history": [
    { "part_number": "...", "description": "...", "classification": "SMT器件" }
  ],
  "last_updated": "2026-06-08T20:54:03"
}
```

### 2. config/force_rules.json（程序自动创建）

```json
{
  "ADC12345": "SMT器件",
  "CONN-B-01": "插件器件"
}
```

### 3. config/coefficients.json（程序自动创建）

```json
{
  "SOT-23": 1.0,
  "BGA400": 1.5
}
```

---

## 核心模块设计

### 1. 数据模型

**Device** (`models/device.py`)
```python
@dataclass
class Device:
    code: str              # 器件编码
    description: str       # 器件描述
    refdes: str            # 位号
    quantity: int          # 数量
    classification: str    # 分类结果
    t_side_count: int      # T面数量
    b_side_count: int      # B面数量
    total_pads: int        # 总焊点数
    converted_qty: float   # 折算后件数
    package: str           # 封装类型
```

**配置模型** (`models/config_models.py`)
```python
@dataclass
class ClassificationRule:
    keywords: list[str]
    exclude_keywords: list[str]
```

### 2. 三级匹配引擎 (`classifiers/rule_engine.py`)

```
输入: Device(code, description, ...)
              │
              ▼
    ┌─────────────────────┐
    │ 1. 强制指定          │  code 精确匹配 force_rules → 直接返回
    │    (最高优先级)       │
    └─────────┬───────────┘
              │ 未命中
              ▼
    ┌─────────────────────┐
    │ 2. 历史记录          │  匹配 classification_history 中的 (code, description)
    └─────────┬───────────┘
              │ 未命中
              ▼
    ┌─────────────────────┐
    │ 3. 关键词规则        │  遍历 classifications，先 exclude 后 keywords
    │    (最低优先级)       │  匹配文本 = f"{code} {description}".lower()
    └─────────┬───────────┘
              │ 未命中
              ▼
         "未分类"
```

### 3. B/T 面检测 (`classifiers/side_detector.py`)

- 从坐标文件中读取 `SYM_MIRROR` 列
- `YES` → B面，`NO` → T面
- 无此列或值不明确时人工指定

### 4. 编码检测 (`parsers/encoding_detector.py`)

依次尝试 `['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']`，解码成功则返回。

### 5. 模糊字段匹配 (`parsers/bom_parser.py` 内)

基于 `field_aliases` 匹配 CSV 列名，策略：
- 精确匹配 → 包含匹配 → 同义词匹配 → 去空格 → 分隔符归一化

### 6. 单例日志 (`src/logger.py`)

控制台 INFO + 文件 DEBUG → `log/app.log`

### 7. 多线程 (`ui/workers.py`)

`threading.Thread` + `root.after(0, callback)` 回主线程更新 UI

### 8. UI 布局 (`ui/app.py`)

```
┌──────────────────────────────────────────────────────┐
│ 菜单: 文件 | 编辑 | 帮助                              │
├──────────────────────────────────────────────────────┤
│ 工具栏: [导入BOM] [导入坐标] [解析] [导出] [规则] ...   │
├──────────────────────────────────────────────────────┤
│ ttk.Notebook                                         │
│ ┌─[数据预览]──────────────[分类统计]─────────────────┐│
│ │ ttk.Treeview(9列)       各分类 种类数/总件数        ││
│ └───────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────┤
│ 状态栏: 就绪                                          │
└──────────────────────────────────────────────────────┘
```

### 9. 对话框 (`ui/dialogs.py`)

| 对话框 | 编辑对象 | 保存到 |
|--------|---------|--------|
| RuleEditorDialog | 分类 → keywords / exclude_keywords | `classification_rules.json` → `classifications` |
| CoefficientEditorDialog | 封装 → 系数值 | `config/coefficients.json` |
| ForceEditorDialog | 器件编码 → 分类 | `config/force_rules.json` |
| ConfirmDialog | 未分类器件下拉选分类 | `classification_rules.json` → `classification_history` |

---

## 实现步骤

### Step 1: 基础框架
- 创建目录结构
- 编写 `requirements.txt`（pandas, openpyxl）
- 实现 `logger.py`
- 实现 `models/`

### Step 2: 文件解析
- `encoding_detector.py`
- `bom_parser.py`（含 field_aliases 模糊匹配）
- `coordinate_parser.py`

### Step 3: 分类引擎 + 配置服务
- `config_service.py`
- `rule_engine.py`
- `side_detector.py`
- 创建 `config/force_rules.json`、`config/coefficients.json` 空模板

### Step 4: Excel 导出
- `export_service.py`，命名 `{源文件名}_解析.xlsx`，两个 Sheet：分类明细 + 统计汇总

### Step 5: GUI
- `app.py`（主窗口）
- `dialogs.py`（4个对话框）
- `workers.py`（3个后台线程）

### Step 6: 入口 + 集成
- `main.py`
- 端到端测试

---

## 验证方式

1. 准备 BOM.csv 和 coordinate.txt 测试数据
2. `python main.py` 启动
3. 导入 BOM → 导入坐标 → 解析 → 查看分类 → 导出 Excel
4. 规则维护增删改查，确认 JSON 文件更新
5. 人工确认未分类器件，确认历史记录写入
6. 大文件测试 UI 不卡顿
7. 检查 `log/app.log`
