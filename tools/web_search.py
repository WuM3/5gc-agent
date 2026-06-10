from __future__ import annotations


def search_web(query: str) -> dict[str, object]:
    return {
        "enabled": False,
        "query": query,
        "message": "在线检索接口已预留，第一版未启用。",
        "results": [],
    }
