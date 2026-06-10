from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.vector_store import VectorEvidenceStore


def main() -> None:
    store = VectorEvidenceStore(
        root_dir=PROJECT_ROOT,
        persist_dir=PROJECT_ROOT / "vectorstore" / "chroma_db",
    )
    print(f"backend={store.backend_name}")
    print(f"documents={len(store.documents)}")
    print(f"persist_dir={PROJECT_ROOT / 'vectorstore' / 'chroma_db'}")


if __name__ == "__main__":
    main()
