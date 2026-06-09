"""分类规则模型"""

from dataclasses import dataclass, field


@dataclass
class ClassificationRule:
    name: str
    keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    category: str
    match_type: str  # "force" | "history" | "keyword" | "manual" | "unmatched"
    matched_keyword: str = ""
