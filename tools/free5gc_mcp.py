from __future__ import annotations


def query_free5gc_mcp(command: str) -> dict[str, object]:
    return {
        "enabled": False,
        "command": command,
        "message": "free5GC-MCP 接口已预留，第一版未启用。",
        "result": None,
    }
