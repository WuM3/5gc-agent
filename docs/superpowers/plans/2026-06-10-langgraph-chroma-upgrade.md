# LangGraph Chroma Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the 5GC Agent from a sequential keyword pipeline to a LangGraph-orchestrated hybrid RAG workflow with Chroma-backed vector retrieval and mode mismatch correction.

**Architecture:** Keep the existing deterministic data loaders and offline fallback, then add a graph workflow around routing, mismatch handling, retrieval, analysis, and report generation. Add a Chroma vector store for knowledge/procedure retrieval with an in-memory fallback so the project remains runnable before optional dependencies are installed.

**Tech Stack:** Python, Streamlit, LangGraph, ChromaDB, local markdown/json/yaml data, pytest.

---

### Task 1: Route Decision and Mode Mismatch

**Files:**
- Modify: `agent/schemas.py`
- Modify: `agent/router.py`
- Modify: `agent/analyzer.py`
- Test: `tests/test_router.py`
- Test: `tests/test_pipeline.py`

- [ ] Add a `RouteDecision` dataclass carrying selected, detected, final type, mismatch flag, and warning.
- [ ] Add `detect_question_type()` and `resolve_question_type()` while keeping `route_question()` backward compatible.
- [ ] Store route metadata on `AnalysisContext`.
- [ ] Verify a selected knowledge mode with a fault question is corrected to fault diagnosis.

### Task 2: Vector Store Retrieval

**Files:**
- Create: `retrieval/vector_store.py`
- Create: `scripts/build_vector_index.py`
- Modify: `requirements.txt`
- Test: `tests/test_vector_store.py`

- [ ] Add a hash-based embedding function to avoid model downloads.
- [ ] Load markdown sections and fault cases into vector documents.
- [ ] Use Chroma `PersistentClient` when `chromadb` is installed.
- [ ] Fall back to in-memory cosine search when Chroma is unavailable.
- [ ] Add `VectorKnowledgeBase.search()` with the same return shape as the current knowledge base.

### Task 3: LangGraph Workflow

**Files:**
- Create: `graph/__init__.py`
- Create: `graph/state.py`
- Create: `graph/workflow.py`
- Modify: `agent/pipeline.py`
- Test: `tests/test_graph_workflow.py`

- [ ] Define graph state for question, route decision, analysis context, and final report.
- [ ] Add node functions for route, analyze, and report.
- [ ] Build a `StateGraph` and compile it when LangGraph is installed.
- [ ] Use a sequential fallback workflow when LangGraph is unavailable.
- [ ] Make `AgentPipeline.run()` invoke the graph workflow.

### Task 4: UI and Documentation

**Files:**
- Modify: `app.py`
- Modify: `README.md`
- Test: `tests/test_app_labels.py`

- [ ] Show selected type, detected type, final type, and mismatch warning in Streamlit.
- [ ] Include route metadata in exported Markdown.
- [ ] Document LangGraph, Chroma, index rebuilding, and mismatch correction.
- [ ] Run the complete pytest suite.
