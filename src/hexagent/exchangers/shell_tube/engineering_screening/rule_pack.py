"""Adapter-side checks for the existing TASK-012/TASK-020 rule-pack authority."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.models import EvaluatedRulePackAuthority

from .errors import BlockerCode
from .models import Task167Request


def validate_approved_rule_pack(request: Task167Request) -> tuple[tuple[BlockerCode, str], ...]:
    if request.task020_configuration.authority_mode.value != "APPROVED_RULE_PACK":
        return ()
    value = request.approved_rule_pack_authority
    if type(value) is not EvaluatedRulePackAuthority:
        return ((BlockerCode.RULE_PACK_REQUIRED, "approved_rule_pack_authority"),)
    binding_value = request.task020_configuration.authority_binding.evaluated_rule_pack_authority
    if binding_value != value:
        return ((BlockerCode.RULE_PACK_INVALID, "approved_rule_pack_authority"),)
    if value.validation_status != "ok" or not value.selected_rule_authorities:
        return ((BlockerCode.RULE_PACK_INVALID, "approved_rule_pack_authority.validation_status"),)
    failures: list[tuple[BlockerCode, str]] = []
    for index, rule in enumerate(value.selected_rule_authorities):
        if rule.approval_status != "approved":
            failures.append((BlockerCode.RULE_NOT_APPROVED, f"selected_rule_authorities[{index}]"))
        if rule.license_evidence is None:
            failures.append(
                (BlockerCode.RULE_LICENSE_BLOCKED, f"selected_rule_authorities[{index}]")
            )
        if not rule.rule_artifact_canonical_hash:
            failures.append((BlockerCode.RULE_PACK_INVALID, f"selected_rule_authorities[{index}]"))
    return tuple(failures)


__all__ = ["validate_approved_rule_pack"]
