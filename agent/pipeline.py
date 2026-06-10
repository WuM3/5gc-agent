from __future__ import annotations

from pathlib import Path

from agent.analyzer import Analyzer
from agent.report import ReportGenerator
from agent.schemas import AgentReport
from graph.workflow import AgentWorkflow
from llm.llm_client import LLMClient
from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase
from retrieval.vector_store import HybridKnowledgeBase
from rules.log_rules import LogRuleBase


class AgentPipeline:
    def __init__(self, root_dir: str | Path | None = None, llm_client=None):
        self.root_dir = Path(root_dir) if root_dir is not None else Path(__file__).resolve().parents[1]
        keyword_base = KnowledgeBase(self.root_dir / "data" / "docs")
        knowledge_base = HybridKnowledgeBase(
            root_dir=self.root_dir,
            persist_dir=self.root_dir / "vectorstore" / "chroma_db",
            keyword_base=keyword_base,
        )
        self.analyzer = Analyzer(
            knowledge_base=knowledge_base,
            case_base=FaultCaseBase(
                self.root_dir / "data" / "fault_cases" / "fault_cases.json"
            ),
            rule_base=LogRuleBase(self.root_dir / "data" / "rules" / "log_rules.yaml"),
        )
        self.report_generator = ReportGenerator(llm_client or LLMClient())
        self.workflow = AgentWorkflow(self.analyzer, self.report_generator)
        self.knowledge_backend_name = knowledge_base.backend_name

    def run(self, question: str, manual_type: str | None = None) -> AgentReport:
        result = self.workflow.invoke(
            {
                "question": question,
                "manual_type": manual_type,
            }
        )
        return result["report"]
