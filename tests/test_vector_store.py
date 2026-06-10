from pathlib import Path
import importlib.util

from agent.schemas import KnowledgeHit
from retrieval.knowledge_base import KnowledgeBase
from retrieval.vector_store import HybridKnowledgeBase, VectorEvidenceStore, VectorKnowledgeBase


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_vector_knowledge_base_finds_procedure_snippet(tmp_path):
    kb = VectorKnowledgeBase(
        root_dir=PROJECT_ROOT,
        persist_dir=tmp_path / "chroma_db",
    )

    hits = kb.search("PDU Session 建立流程经过哪些网元？", top_k=3)

    assert hits
    assert all(isinstance(hit, KnowledgeHit) for hit in hits)
    assert hits[0].title == "PDU Session Establishment"
    assert "N11" in hits[0].snippet


def test_vector_store_indexes_fault_cases_and_markdown(tmp_path):
    store = VectorEvidenceStore(
        root_dir=PROJECT_ROOT,
        persist_dir=tmp_path / "chroma_db",
    )

    hits = store.search("MongoDB subscriber data not found", top_k=5)
    titles = [hit.title for hit in hits]

    assert "MongoDB subscriber data is missing" in titles
    assert any(hit.source_type == "fault_case" for hit in hits)
    assert any(hit.source_type in {"knowledge", "procedure"} for hit in hits)


def test_vector_store_creates_persist_directory(tmp_path):
    persist_dir = tmp_path / "chroma_db"

    store = VectorEvidenceStore(root_dir=PROJECT_ROOT, persist_dir=persist_dir)

    assert persist_dir.exists()
    assert store.backend_name in {"chroma", "memory"}


def test_vector_store_uses_chroma_when_dependency_is_available(tmp_path):
    if importlib.util.find_spec("chromadb") is None:
        return

    store = VectorEvidenceStore(
        root_dir=PROJECT_ROOT,
        persist_dir=tmp_path / "chroma_db",
    )

    assert store.backend_name == "chroma"


def test_hybrid_knowledge_base_preserves_keyword_precision(tmp_path):
    keyword_base = KnowledgeBase(PROJECT_ROOT / "data" / "docs")
    hybrid_base = HybridKnowledgeBase(
        root_dir=PROJECT_ROOT,
        persist_dir=tmp_path / "chroma_db",
        keyword_base=keyword_base,
    )

    hits = hybrid_base.search("N1", top_k=5)

    assert "PDU Session Establishment" not in [hit.title for hit in hits]
    assert hybrid_base.backend_name.startswith("hybrid-")
