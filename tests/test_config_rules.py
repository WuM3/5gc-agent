from pathlib import Path

from rules.config_rules import ConfigRuleBase


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_config_rule_base_flags_smf_without_user_plane_topology():
    rule_base = ConfigRuleBase(PROJECT_ROOT / "data" / "rules" / "config_rules.yaml")

    hits = rule_base.check(
        """
上传文件：smfcfg.yaml
configuration:
  smfName: SMF
  snssaiInfos:
    - sNssai:
        sst: 1
      dnnInfos:
        - dnn: internet
"""
    )

    assert hits
    assert hits[0].rule_id == "CFG-SMF-001"
    assert hits[0].nf == "SMF"
    assert "N4" in hits[0].interface
    assert any("UPF" in item for item in hits[0].missing_items)


def test_config_rule_base_flags_upf_without_gtpu_or_ue_subnet():
    rule_base = ConfigRuleBase(PROJECT_ROOT / "data" / "rules" / "config_rules.yaml")

    hits = rule_base.check(
        """
上传文件：upfcfg.yaml
pfcp:
  addr: 127.0.0.8
"""
    )

    rule_ids = [hit.rule_id for hit in hits]
    assert "CFG-UPF-001" in rule_ids
    assert "CFG-UPF-002" in rule_ids


def test_config_rule_base_ignores_complete_minimal_smf_config():
    rule_base = ConfigRuleBase(PROJECT_ROOT / "data" / "rules" / "config_rules.yaml")

    hits = rule_base.check(
        """
上传文件：smfcfg.yaml
configuration:
  smfName: SMF
  userplaneInformation:
    upNodes:
      gNB1:
        type: AN
      UPF:
        type: UPF
        nodeID: 127.0.0.8
    links:
      - A: gNB1
        B: UPF
  snssaiInfos:
    - sNssai:
        sst: 1
      dnnInfos:
        - dnn: internet
"""
    )

    assert [hit.rule_id for hit in hits] == []


def test_config_rule_base_returns_parse_error_for_uploaded_config_syntax_error():
    rule_base = ConfigRuleBase(PROJECT_ROOT / "data" / "rules" / "config_rules.yaml")

    hits = rule_base.check(
        """
上传文件：amfcfg.yaml
configuration:
  amfName: AMF
    bad_indent: true
"""
    )

    assert hits
    assert hits[0].rule_id == "CFG-PARSE-001"
    assert hits[0].severity == "warning"
