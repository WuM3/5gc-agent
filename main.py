from __future__ import annotations

import argparse

from agent.pipeline import AgentPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="5G Core 问答与故障诊断助手")
    parser.add_argument("question", nargs="+", help="用户问题")
    parser.add_argument("--type", dest="manual_type", help="手动指定问题类型")
    args = parser.parse_args()

    question = " ".join(args.question)
    report = AgentPipeline().run(question, manual_type=args.manual_type)
    print(report.content)


if __name__ == "__main__":
    main()
