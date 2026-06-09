"""三级匹配引擎：强制指定 > 历史记录 > 关键词规则"""

import logging
from typing import Optional

from src.models.classification import ClassificationResult, ClassificationRule

logger = logging.getLogger("ParseApp")


class RuleEngine:
    def __init__(
        self,
        force_rules: dict[str, str],
        history: list[dict],
        classifications: dict[str, ClassificationRule],
    ):
        self._force_rules = force_rules
        self._history_index: dict[str, str] = self._build_history_index(history)
        self._classifications = classifications

    @staticmethod
    def _build_history_index(history: list[dict]) -> dict[str, str]:
        index = {}
        for entry in history:
            key = f"{entry.get('part_number', '')}||{entry.get('description', '')}"
            index[key] = entry.get("classification", "未分类")
        return index

    def classify(self, code: str, description: str) -> ClassificationResult:
        # 1. 强制指定（精确匹配器件编码）
        force_key = code.strip()
        if force_key in self._force_rules:
            return ClassificationResult(
                category=self._force_rules[force_key],
                match_type="force",
            )

        # 2. 历史记录
        history_key = f"{code.strip()}||{description.strip()}"
        if history_key in self._history_index:
            return ClassificationResult(
                category=self._history_index[history_key],
                match_type="history",
            )

        # 3. 关键词规则
        match_text = f"{code} {description}".lower()
        return self._match_keywords(match_text)

    def _match_keywords(self, match_text: str) -> ClassificationResult:
        for name, rule in self._classifications.items():
            # 先检查排除关键词
            excluded = False
            for ek in rule.exclude_keywords:
                if ek.lower() in match_text:
                    excluded = True
                    break
            if excluded:
                continue

            # 再检查包含关键词
            for kw in rule.keywords:
                if kw.lower() in match_text:
                    return ClassificationResult(
                        category=name,
                        match_type="keyword",
                        matched_keyword=kw,
                    )

        return ClassificationResult(category="未分类", match_type="unmatched")

    def reclassify_with_manual(
        self, code: str, description: str, new_category: str
    ) -> ClassificationResult:
        """手动指定新分类"""
        return ClassificationResult(
            category=new_category,
            match_type="manual",
        )
