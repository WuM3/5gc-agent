from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

import yaml

from agent.schemas import ConfigRuleHit


_UPLOAD_BLOCK_RE = re.compile(
    r"(?:^|\n)上传文件：(?P<filename>[^\n]+)\n(?P<body>.*?)(?=\n\n上传文件：|\Z)",
    re.DOTALL,
)
_CONFIG_EXTENSIONS = {".json", ".yaml", ".yml"}
_CONFIG_FILE_KEYWORDS = ("amf", "smf", "upf", "cfg", "config", "open5gs", "free5gc")


@dataclass(frozen=True)
class _UploadedConfig:
    filename: str
    body: str
    parsed: Any
    haystack: str
    nf: str


class ConfigRuleBase:
    def __init__(self, rules_path: str | Path):
        self.rules_path = Path(rules_path)
        self._rules = self._load_rules()

    def check(self, text: str, top_k: int = 5) -> list[ConfigRuleHit]:
        if top_k <= 0:
            return []

        hits: list[tuple[int, ConfigRuleHit]] = []
        for block_index, filename, body in _extract_uploaded_blocks(text):
            if not _is_config_candidate(filename, body):
                continue

            parsed, error = _parse_config(filename, body)
            nf = _detect_nf(filename, body)
            if error:
                hits.append((block_index, _parse_error_hit(filename, nf, error)))
                continue

            config = _UploadedConfig(
                filename=filename,
                body=body,
                parsed=parsed,
                haystack=_build_haystack(filename, body, parsed),
                nf=nf,
            )
            for rule_index, rule in enumerate(self._rules, start=1):
                hit = _check_rule(config, rule, rule_index)
                if hit:
                    hits.append((block_index * 1000 + rule_index, hit))

        ordered = sorted(hits, key=lambda item: (-item[1].score, item[0]))
        return [hit for _, hit in ordered[:top_k]]

    def _load_rules(self) -> list[dict[str, Any]]:
        if not self.rules_path.exists():
            return []

        with self.rules_path.open(encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        rules = data.get("rules", []) if isinstance(data, dict) else []
        return [rule for rule in rules if isinstance(rule, dict)]


def _extract_uploaded_blocks(text: str) -> list[tuple[int, str, str]]:
    blocks: list[tuple[int, str, str]] = []
    for index, match in enumerate(_UPLOAD_BLOCK_RE.finditer(text)):
        filename = match.group("filename").strip()
        body = match.group("body").strip()
        if filename and body:
            blocks.append((index, filename, body))
    return blocks


def _is_config_candidate(filename: str, body: str) -> bool:
    suffix = Path(filename).suffix.casefold()
    if suffix not in _CONFIG_EXTENSIONS:
        return False

    filename_norm = _normalize(filename)
    body_norm = _normalize(body)
    if any(keyword in filename_norm for keyword in _CONFIG_FILE_KEYWORDS):
        return True
    return any(keyword in body_norm for keyword in ("ngap", "pfcp", "gtpu", "snssai", "dnn"))


def _parse_config(filename: str, body: str) -> tuple[Any, str | None]:
    try:
        if Path(filename).suffix.casefold() == ".json":
            return json.loads(body), None
        return yaml.safe_load(body), None
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        return None, str(exc).splitlines()[0]


def _detect_nf(filename: str, body: str) -> str:
    combined = _normalize(f"{filename}\n{body}")
    for nf in ("AMF", "SMF", "UPF"):
        if nf.casefold() in combined:
            return nf
    return "UNKNOWN"


def _build_haystack(filename: str, body: str, parsed: Any) -> str:
    return _normalize(
        "\n".join(
            [
                filename,
                body,
                _flatten_keys_and_values(parsed),
            ]
        )
    )


def _check_rule(
    config: _UploadedConfig,
    rule: dict[str, Any],
    rule_index: int,
) -> ConfigRuleHit | None:
    if not _rule_applies(config, rule):
        return None

    missing_items: list[str] = []
    for group in rule.get("required_any_groups", []):
        label, terms = _group_label_and_terms(group)
        if not any(_normalize(term) in config.haystack for term in terms):
            missing_items.append(label)

    if not missing_items:
        return None

    return ConfigRuleHit(
        rule_id=str(rule.get("rule_id", "")),
        title=str(rule.get("title", "")),
        nf=str(rule.get("nf", config.nf)),
        interface=str(rule.get("interface", "")),
        severity=str(rule.get("severity", "medium")),
        missing_items=missing_items,
        possible_causes=list(rule.get("possible_causes", [])),
        next_steps=list(rule.get("next_steps", [])),
        evidence=f"{config.filename} 缺少：{'、'.join(missing_items)}",
        score=int(rule.get("score", 80)) - rule_index,
    )


def _rule_applies(config: _UploadedConfig, rule: dict[str, Any]) -> bool:
    target_nf = str(rule.get("nf", "")).upper()
    if target_nf and target_nf != config.nf:
        return False

    keywords = [_normalize(keyword) for keyword in rule.get("file_keywords", [])]
    if not keywords:
        return True

    filename_norm = _normalize(config.filename)
    return any(keyword and keyword in filename_norm for keyword in keywords)


def _group_label_and_terms(group: Any) -> tuple[str, list[str]]:
    if isinstance(group, dict):
        label = str(group.get("label", "必需配置项"))
        terms = [str(term) for term in group.get("terms", [])]
        return label, terms
    if isinstance(group, list):
        return "必需配置项", [str(term) for term in group]
    return str(group), [str(group)]


def _parse_error_hit(filename: str, nf: str, error: str) -> ConfigRuleHit:
    return ConfigRuleHit(
        rule_id="CFG-PARSE-001",
        title="配置文件解析失败",
        nf=nf,
        interface="配置文件",
        severity="warning",
        missing_items=["合法 YAML/JSON 语法"],
        possible_causes=["上传内容不是合法 YAML/JSON，或缩进、冒号、列表符号存在错误"],
        next_steps=["先修复配置文件语法，再继续检查 AMF、SMF、UPF 字段一致性"],
        evidence=f"{filename} 解析失败：{error}",
        score=100,
    )


def _flatten_keys_and_values(value: Any, prefix: str = "") -> str:
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            parts.append(path)
            parts.append(_flatten_keys_and_values(item, path))
        return " ".join(parts)
    if isinstance(value, list):
        return " ".join(_flatten_keys_and_values(item, prefix) for item in value)
    return str(value)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(value).casefold())
