"""器件数据模型"""

from dataclasses import dataclass, field


@dataclass
class Device:
    code: str                           # 器件编码
    description: str = ""               # 器件描述
    refdes: str = ""                    # 位号
    quantity: int = 0                   # 数量
    classification: str = "未分类"       # 分类结果
    t_side_count: int = 0               # T面数量
    b_side_count: int = 0               # B面数量
    total_pads: int = 0                 # 总焊点数
    converted_qty: float = 0.0          # 折算后件数
    package: str = ""                   # 封装类型
    _raw: dict = field(default_factory=dict, repr=False)  # 原始行数据
