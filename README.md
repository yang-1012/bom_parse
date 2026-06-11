# BOM 解析分类工具

根据 BOM 文件和坐标文件(.txt)，通过关键词匹配、历史记录学习和强制指定规则，将器件自动分入 SMT器件、插件器件、压接器件等类别，并根据坐标文件确认器件位于 B 面还是 T 面，最终导出分层后的 Excel 报表。

## 环境要求

- Python 3.8+
- 依赖包见 [requirements.txt](requirements.txt)

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 使用流程

1. **导入 BOM 文件** — 点击工具栏"导入BOM"，选择 CSV / TXT / Excel 格式的 BOM 文件
2. **导入坐标文件** — 点击工具栏"导入txt坐标文件"，选择 PCB 设计软件导出的坐标文件(.txt)
3. **开始解析** — 点击"开始解析"，系统按三级匹配策略自动分类器件
4. **人工确认** — 对未能自动分类的器件，弹出确认对话框供手动指定分类
5. **导出结果** — 点击"导出结果"，生成 Excel 报表，包含"全部分类"、"统计汇总"两个汇总 Sheet，以及"SMT器件"、"插件器件"、"压接器件"等各分类的独立 Sheet

## 配置文件

| 文件 | 用途 |
|------|------|
| [classification_rules.json](classification_rules.json) | 分类规则：各类别的关键词、排除关键词，以及分类历史记录 |
| [config/force_rules.json](config/force_rules.json) | 强制指定规则：器件编码 → 分类的精确映射，优先级最高 |
| [config/coefficients.json](config/coefficients.json) | 折算系数：封装类型 → 折算系数的映射，未匹配时默认等于管脚数，折算后件数 = 总焊点数 // 系数 |
| [config/pin_count_rules.json](config/pin_count_rules.json) | 管脚数映射：封装类型 → 管脚数的映射，未匹配时默认 0 |

也可以在 GUI 中通过"规则维护"对话框统一管理以上配置。

## 列名映射规则

导入文件时，程序自动识别 BOM 和坐标文件的列名，支持中英文，匹配时不区分大小写、忽略空格/下划线/横线等分隔符。

### BOM 文件列名

1. **`field_aliases` 别名匹配** — `classification_rules.json` 中可配置 `field_aliases`，定义标准字段的自定义别名列表，优先匹配
2. **内置近义词匹配** — 别名未命中时，使用以下近义词自动识别：

| 标准字段 | 近义词 |
|---|---|
| 器件编码 | `partnumber`, `partno`, `partnum`, `pn`, `mpn`, `part-no`, `part-number` |
| 器件描述 | `description`, `desc`, `spec`, `specification` |
| 位号 | `refdes`, `designator`, `ref`, `reference`, `position`, `positions`, `pad` |
| 数量 | `qty`, `quantity`, `count`, `pcs`, `pc`, `units`, `pieces`, `ea`, `sum` |
| 封装 | `package`, `packagetype`, `footprint`, `pkg`, `封装`, `封装形式`, `元件封装`, `包装`, `bodysize`, `case`, `mountingtype`, `安装方式`, `smt/tht` |
| 管脚数 | `pincount`, `pins`, `pin`, `管脚数`, `引脚数`, `numberofpins`, `pin数量`, `leadcount`, `脚数`, `焊盘数` |

### 坐标文件列名

| 目标字段 | 关键词 |
|---|---|
| 位号 | `refdes`, `ref`, `reference`, `位号`, `designator`, `ref des` |
| 封装 | `comp_device_type`, `comp device type`, `device_type`, `component_type`, `devicetype`, `package`, `footprint`, `pkg`, `封装`, `package_type`, `foot_print` |
| 面别 | `sym_mirror`, `mirror`, `side`, `layer`, `面` |

## 项目结构

```
├── main.py                 # 程序入口
├── requirements.txt        # Python 依赖
├── classification_rules.json  # 主配置文件
├── config/                 # 其他配置文件
│   ├── force_rules.json
│   ├── coefficients.json
│   └── pin_count_rules.json
├── src/
│   ├── logger.py           # 日志模块（单例，控制台 + 文件双输出）
│   ├── models/             # 数据模型（Device、ClassificationRule 等）
│   ├── parsers/            # 文件解析器（BOM、坐标文件、编码检测）
│   ├── classifiers/        # 分类引擎（三级匹配策略、B/T 面识别）
│   ├── services/           # 业务服务（配置读写、Excel 导出）
│   └── ui/                 # GUI 界面（主窗口、工具栏、对话框、后台线程）
└── log/                    # 日志文件
```
