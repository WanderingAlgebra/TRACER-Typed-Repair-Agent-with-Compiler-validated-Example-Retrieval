"""LeanCapsule manifest 的轻量校验与版本定义。"""

from __future__ import annotations

from typing import Any


SCHEMA_VERSION = "leancapsule.v0.1"


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """返回缺失或类型错误字段；空列表表示通过基础校验。"""

    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version 必须为 leancapsule.v0.1")
    for field in ("capsule_id", "target", "environment", "expected", "provenance"):
        if field not in manifest:
            errors.append(f"缺少字段: {field}")
    target = manifest.get("target")
    if not isinstance(target, dict) or not target.get("source_file"):
        errors.append("target.source_file 必须存在")
    expected = manifest.get("expected")
    if not isinstance(expected, dict) or not expected.get("category"):
        errors.append("expected.category 必须存在")
    if not isinstance(expected, dict) or not isinstance(expected.get("diagnostic_key"), str):
        errors.append("expected.diagnostic_key 必须是文本")
    return errors
