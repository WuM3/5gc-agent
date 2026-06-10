from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent.schemas import LogRuleHit


class LogRuleBase:
    def __init__(self, rules_path: str | Path):
        self.rules_path = Path(rules_path)
        self._rules = self._load_rules()

    def match(self, text: str, top_k: int = 3) -> list[LogRuleHit]:
        text_norm = text.casefold()
        hits: list[tuple[int, LogRuleHit]] = []

        for index, rule in enumerate(self._rules):
            score = _score_rule(text_norm, rule)
            if score <= 0:
                continue

            hits.append(
                (
                    index,
                    LogRuleHit(
                        keyword=str(rule.get("keyword", "")),
                        nf=str(rule.get("nf", "")),
                        interface=str(rule.get("interface", "")),
                        possible_causes=list(rule.get("possible_causes", [])),
                        next_steps=list(rule.get("next_steps", [])),
                        severity=str(rule.get("severity", "")),
                        score=score,
                    ),
                )
            )

        ordered = sorted(hits, key=lambda item: (-item[1].score, item[0]))
        return [hit for _, hit in ordered[:top_k]]

    def _load_rules(self) -> list[dict[str, Any]]:
        if not self.rules_path.exists():
            return []

        with self.rules_path.open(encoding="utf-8") as file:
            data = yaml.safe_load(file) or []

        if isinstance(data, list):
            return [rule for rule in data if isinstance(rule, dict)]
        rules = data.get("rules", []) if isinstance(data, dict) else []
        return [rule for rule in rules if isinstance(rule, dict)]


def _score_rule(text_norm: str, rule: dict[str, Any]) -> int:
    score = 0
    for pattern in rule.get("patterns", []):
        pattern_norm = str(pattern).casefold().strip()
        if pattern_norm and pattern_norm in text_norm:
            score += 10 + len(pattern_norm)
    return score
