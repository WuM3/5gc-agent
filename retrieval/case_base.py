from __future__ import annotations

from pathlib import Path
import json
import re
from typing import Any

from agent.schemas import FaultCaseHit


_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)
_ASCII_PHRASE_RE = re.compile(
    r"[a-z0-9]+(?:\s+[a-z0-9]+)+", re.IGNORECASE
)


class FaultCaseBase:
    def __init__(self, cases_path: str | Path):
        self.cases_path = Path(cases_path)
        self._cases = self._load_cases()

    def search(self, query: str, top_k: int = 3) -> list[FaultCaseHit]:
        if top_k <= 0:
            return []

        hits: list[FaultCaseHit] = []
        for case in self._cases:
            score = _score_case(query, case)
            if score > 0:
                hits.append(_to_hit(case, score))

        return sorted(hits, key=lambda hit: (-hit.score, hit.case_id))[:top_k]

    def _load_cases(self) -> list[dict[str, Any]]:
        if not self.cases_path.exists():
            return []
        with self.cases_path.open(encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
        return data.get("cases", [])


def _score_case(query: str, case: dict[str, Any]) -> int:
    query_norm = query.casefold()
    query_tokens = set(_tokens(query))
    title = str(case.get("title", ""))
    title_tokens = set(_tokens(title))
    text_norm = _flatten(case).casefold()
    text_tokens = set(_tokens(text_norm))
    score = 0

    if (
        query_norm
        and not any(_is_domain_identifier(token) for token in query_tokens)
        and query_norm in text_norm
    ):
        score += 20

    for keyword in case.get("keywords", []):
        keyword_norm = str(keyword).casefold()
        keyword_tokens = set(_tokens(keyword_norm))
        if keyword_tokens and keyword_tokens.issubset(query_tokens):
            score += 12
        for phrase in _ascii_phrases(keyword_norm):
            if phrase in query_norm:
                score += 12
        score += 4 * len(keyword_tokens & query_tokens)

    for token in query_tokens:
        if token in title_tokens:
            score += 8
        if token in text_tokens:
            score += 2

    for nf in case.get("network_functions", []):
        if set(_tokens(str(nf))).issubset(query_tokens):
            score += 8

    for interface in case.get("interfaces", []):
        if set(_tokens(str(interface))).issubset(query_tokens):
            score += 6

    return score


def _to_hit(case: dict[str, Any], score: int) -> FaultCaseHit:
    return FaultCaseHit(
        case_id=str(case.get("case_id", "")),
        title=str(case.get("title", "")),
        issue_type=str(case.get("issue_type", "")),
        symptoms=list(case.get("symptoms", [])),
        network_functions=list(case.get("network_functions", [])),
        interfaces=list(case.get("interfaces", [])),
        possible_causes=list(case.get("possible_causes", [])),
        next_steps=list(case.get("next_steps", [])),
        evidence=str(case.get("evidence", "")),
        score=score,
    )


def _tokens(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]


def _ascii_phrases(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _ASCII_PHRASE_RE.finditer(text)]


def _is_domain_identifier(token: str) -> bool:
    return bool(re.fullmatch(r"n\d+", token))


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value)
