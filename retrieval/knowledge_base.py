from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from agent.schemas import KnowledgeHit


_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)
_ASCII_PHRASE_RE = re.compile(
    r"[a-z0-9]+(?:\s+[a-z0-9]+)+", re.IGNORECASE
)


@dataclass(frozen=True)
class _Section:
    title: str
    source: str
    body: str


class KnowledgeBase:
    def __init__(self, docs_dir: str | Path):
        self.docs_dir = Path(docs_dir)
        self._sections = self._load_sections()

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeHit]:
        if top_k <= 0:
            return []

        hits: list[KnowledgeHit] = []
        for section in self._sections:
            score = _score(query, section.title, section.body)
            score += _source_boost(query, section.source)
            if score > 0:
                hits.append(
                    KnowledgeHit(
                        title=section.title,
                        source=section.source,
                        snippet=_snippet(section.body),
                        score=score,
                    )
                )

        return sorted(hits, key=lambda hit: (-hit.score, hit.title))[:top_k]

    def _load_sections(self) -> list[_Section]:
        sections: list[_Section] = []
        if not self.docs_dir.exists():
            return sections

        for path in sorted(self.docs_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            headings = list(_HEADING_RE.finditer(text))
            for index, heading in enumerate(headings):
                start = heading.end()
                end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
                body = text[start:end].strip()
                if body:
                    sections.append(
                        _Section(
                            title=heading.group(1).strip(),
                            source=path.name,
                            body=body,
                        )
                    )
        return sections


def _score(query: str, title: str, body: str) -> int:
    query_norm = query.casefold()
    query_tokens = set(_tokens(query))
    title_norm = title.casefold()
    title_tokens = set(_tokens(title))
    text_norm = f"{title}\n{body}".casefold()
    text_tokens = set(_tokens(text_norm))
    score = 0

    for token in query_tokens:
        if token in title_tokens:
            score += 10
        if token in text_tokens:
            score += 3

    for phrase in _ascii_phrases(query):
        if phrase in title_norm:
            score += 16
        if phrase in text_norm:
            score += 6

    if (
        query_norm
        and not any(_is_domain_identifier(token) for token in query_tokens)
        and query_norm in text_norm
    ):
        score += 20

    return score


def _source_boost(query: str, source: str) -> int:
    if source != "core_network.md":
        return 0

    query_norm = query.casefold()
    if any(term in query_norm for term in ("是什么", "区别", "作用", "职责")):
        return 4
    return 0


def _tokens(text: str) -> list[str]:
    normalized = text.casefold()
    tokens = [match.group(0).casefold() for match in _TOKEN_RE.finditer(text)]
    domain_terms = (
        "核心网",
        "5g核心网",
        "控制面",
        "用户面",
        "移动性管理",
        "会话管理",
        "服务注册",
        "服务发现",
    )
    tokens.extend(term for term in domain_terms if term in normalized)
    return tokens


def _ascii_phrases(text: str) -> list[str]:
    return [match.group(0).casefold() for match in _ASCII_PHRASE_RE.finditer(text)]


def _is_domain_identifier(token: str) -> bool:
    return bool(re.fullmatch(r"n\d+", token))


def _snippet(text: str, limit: int = 280) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
