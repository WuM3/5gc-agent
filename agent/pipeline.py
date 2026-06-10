from __future__ import annotations

from pathlib import Path

from agent.analyzer import Analyzer
from agent.report import ReportGenerator
from agent.router import route_question
from agent.schemas import AgentReport
from llm.llm_client import LLMClient
from retrieval.case_base import FaultCaseBase
from retrieval.knowledge_base import KnowledgeBase
from rules.log_rules import LogRuleBase


class AgentPipeline:
    def __init__(self, root_dir: str | Path | None = None, llm_client=None):
        self.root_dir = Path(root_dir) if root_dir is not None else Path(__file__).resolve().parents[1]
        self.analyzer = Analyzer(
            knowledge_base=KnowledgeBase(self.root_dir / "data" / "docs"),
            case_base=FaultCaseBase(
                self.root_dir / "data" / "fault_cases" / "fault_cases.json"
            ),
            rule_base=LogRuleBase(self.root_dir / "data" / "rules" / "log_rules.yaml"),
        )
        self.report_generator = ReportGenerator(llm_client or LLMClient())

    def run(self, question: str, manual_type: str | None = None) -> AgentReport:
        question_type = route_question(question, manual_type=manual_type)
        context = self.analyzer.analyze(question, question_type)
        return self.report_generator.generate(context)
