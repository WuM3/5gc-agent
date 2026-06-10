from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import re
from typing import Any

from agent.schemas import KnowledgeHit


_HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
_TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]+", re.IGNORECASE)
_EMBEDDING_DIMENSION = 96


@dataclass(frozen=True)
class VectorDocument:
    doc_id: str
    title: str
    source: str
    source_type: str
    text: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class VectorHit:
    title: str
    source: str
    source_type: str
    text: str
    score: int
    metadata: dict[str, str]


class HashEmbeddingFunction:
    @staticmethod
    def name() -> str:
        return "5gc-hash-embedding"

    @staticmethod
    def is_legacy() -> bool:
        return False

    @staticmethod
    def default_space() -> str:
        return "cosine"

    @staticmethod
    def supported_spaces() -> list[str]:
        return ["cosine"]

    @staticmethod
    def get_config() -> dict[str, str | int]:
        return {
            "name": HashEmbeddingFunction.name(),
            "dimension": _EMBEDDING_DIMENSION,
            "space": HashEmbeddingFunction.default_space(),
        }

    @staticmethod
    def build_from_config(config):
        return HashEmbeddingFunction()

    def __call__(self, input):  # Chroma calls this parameter "input".
        return [_hash_embedding(text) for text in input]

    def embed_query(self, input):
        return self(input)

    def embed_documents(self, input):
        return self(input)


class VectorEvidenceStore:
    def __init__(self, root_dir: str | Path, persist_dir: str | Path):
        self.root_dir = Path(root_dir)
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.documents = _load_documents(self.root_dir)
        self.backend_name = "memory"
        self._collection = None
        self._memory_index = [
            (document, _hash_embedding(_document_text(document)))
            for document in self.documents
        ]
        self._try_init_chroma()

    def search(
        self,
        query: str,
        top_k: int = 3,
        source_types: set[str] | None = None,
    ) -> list[VectorHit]:
        if top_k <= 0:
            return []

        if self._collection is not None:
            hits = self._search_chroma(query, top_k=max(top_k, len(self.documents)))
        else:
            hits = self._search_memory(query, top_k=max(top_k, len(self.documents)))

        if source_types is not None:
            hits = [hit for hit in hits if hit.source_type in source_types]
        return hits[:top_k]

    def _try_init_chroma(self) -> None:
        try:
            import chromadb
        except Exception:
            return

        try:
            client = chromadb.PersistentClient(path=str(self.persist_dir))
            collection = client.get_or_create_collection(
                name="five_gc_evidence",
                embedding_function=HashEmbeddingFunction(),
            )
            if collection.count() != len(self.documents):
                if collection.count() > 0:
                    existing = collection.get(include=[])
                    ids = existing.get("ids", [])
                    if ids:
                        collection.delete(ids=ids)
                collection.add(
                    ids=[document.doc_id for document in self.documents],
                    documents=[_document_text(document) for document in self.documents],
                    metadatas=[document.metadata for document in self.documents],
                )
            self._collection = collection
            self.backend_name = "chroma"
        except Exception:
            self._collection = None
            self.backend_name = "memory"

    def _search_chroma(self, query: str, top_k: int) -> list[VectorHit]:
        assert self._collection is not None
        result = self._collection.query(
            query_texts=[query],
            n_results=min(top_k, len(self.documents)),
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        hits: list[VectorHit] = []
        for text, metadata, distance in zip(documents, metadatas, distances):
            hits.append(
                VectorHit(
                    title=str(metadata.get("title", "")),
                    source=str(metadata.get("source", "")),
                    source_type=str(metadata.get("source_type", "")),
                    text=str(text),
                    score=max(1, int(1000 / (1 + float(distance)))),
                    metadata={key: str(value) for key, value in metadata.items()},
                )
            )
        return hits

    def _search_memory(self, query: str, top_k: int) -> list[VectorHit]:
        query_embedding = _hash_embedding(query)
        scored: list[tuple[float, VectorDocument]] = []
        for document, embedding in self._memory_index:
            scored.append((_cosine_similarity(query_embedding, embedding), document))

        ordered = sorted(scored, key=lambda item: (-item[0], item[1].title))
        return [
            VectorHit(
                title=document.title,
                source=document.source,
                source_type=document.source_type,
                text=_document_text(document),
                score=max(1, int(score * 1000)),
                metadata=document.metadata,
            )
            for score, document in ordered[:top_k]
        ]


class VectorKnowledgeBase:
    def __init__(self, root_dir: str | Path, persist_dir: str | Path):
        self.store = VectorEvidenceStore(root_dir=root_dir, persist_dir=persist_dir)

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeHit]:
        hits = self.store.search(
            query,
            top_k=top_k,
            source_types={"knowledge", "procedure"},
        )
        return [
            KnowledgeHit(
                title=hit.title,
                source=hit.source,
                snippet=_snippet(hit.text),
                score=hit.score,
            )
            for hit in hits
        ]


class HybridKnowledgeBase:
    def __init__(self, root_dir: str | Path, persist_dir: str | Path, keyword_base):
        self.keyword_base = keyword_base
        self.vector_base = VectorKnowledgeBase(root_dir=root_dir, persist_dir=persist_dir)
        self.backend_name = f"hybrid-{self.vector_base.store.backend_name}"

    def search(self, query: str, top_k: int = 3) -> list[KnowledgeHit]:
        if top_k <= 0:
            return []

        keyword_hits = self.keyword_base.search(query, top_k=top_k)
        if _is_precise_interface_query(query):
            return keyword_hits[:top_k]

        vector_hits = self.vector_base.search(query, top_k=top_k)
        merged: list[KnowledgeHit] = []
        seen: set[tuple[str, str]] = set()

        for hit in keyword_hits + vector_hits:
            key = (hit.source, hit.title)
            if key in seen:
                continue
            seen.add(key)
            merged.append(hit)

        return merged[:top_k]


def _load_documents(root_dir: Path) -> list[VectorDocument]:
    documents: list[VectorDocument] = []
    documents.extend(_load_markdown_documents(root_dir / "data" / "docs"))
    documents.extend(_load_fault_case_documents(root_dir / "data" / "fault_cases" / "fault_cases.json"))
    return documents


def _load_markdown_documents(docs_dir: Path) -> list[VectorDocument]:
    documents: list[VectorDocument] = []
    if not docs_dir.exists():
        return documents

    for path in sorted(docs_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        headings = list(_HEADING_RE.finditer(text))
        for index, heading in enumerate(headings):
            start = heading.end()
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            body = text[start:end].strip()
            if not body:
                continue
            title = heading.group(1).strip()
            source_type = "procedure" if path.name == "procedures.md" else "knowledge"
            doc_id = _stable_id(f"{source_type}:{path.name}:{title}")
            metadata = {
                "title": title,
                "source": path.name,
                "source_type": source_type,
            }
            documents.append(
                VectorDocument(
                    doc_id=doc_id,
                    title=title,
                    source=path.name,
                    source_type=source_type,
                    text=body,
                    metadata=metadata,
                )
            )
    return documents


def _load_fault_case_documents(cases_path: Path) -> list[VectorDocument]:
    if not cases_path.exists():
        return []

    with cases_path.open(encoding="utf-8") as file:
        cases = json.load(file)

    documents: list[VectorDocument] = []
    for item in cases:
        case_id = str(item.get("case_id", ""))
        title = str(item.get("title", ""))
        text = _flatten(
            [
                title,
                item.get("issue_type", ""),
                item.get("keywords", []),
                item.get("symptoms", []),
                item.get("network_functions", []),
                item.get("interfaces", []),
                item.get("possible_causes", []),
                item.get("next_steps", []),
                item.get("evidence", ""),
            ]
        )
        metadata = {
            "title": title,
            "source": case_id,
            "source_type": "fault_case",
            "case_id": case_id,
        }
        documents.append(
            VectorDocument(
                doc_id=_stable_id(f"fault_case:{case_id}:{title}"),
                title=title,
                source=case_id,
                source_type="fault_case",
                text=text,
                metadata=metadata,
            )
        )
    return documents


def _document_text(document: VectorDocument) -> str:
    return f"{document.title}\n{document.text}"


def _hash_embedding(text: str) -> list[float]:
    vector = [0.0] * _EMBEDDING_DIMENSION
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % _EMBEDDING_DIMENSION
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(left_value * right_value for left_value, right_value in zip(left, right))


def _tokens(text: str) -> list[str]:
    normalized = text.casefold()
    tokens = [match.group(0).casefold() for match in _TOKEN_RE.finditer(normalized)]
    domain_terms = (
        "核心网",
        "5g核心网",
        "控制面",
        "用户面",
        "移动性管理",
        "会话管理",
        "服务注册",
        "服务发现",
        "故障诊断",
        "日志分析",
    )
    tokens.extend(term for term in domain_terms if term in normalized)
    return tokens


def _is_precise_interface_query(query: str) -> bool:
    tokens = [token.casefold() for token in _TOKEN_RE.findall(query)]
    return bool(tokens) and all(re.fullmatch(r"n\d+", token) for token in tokens)


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value)


def _snippet(text: str, limit: int = 280) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
