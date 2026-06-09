"""折算系数模型"""

from dataclasses import dataclass


@dataclass
class Coefficient:
    package: str
    value: float = 1.0
