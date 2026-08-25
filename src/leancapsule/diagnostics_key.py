"""把 Lean 诊断规范化为可读、可比较的诊断键。"""

from __future__ import annotations

import re


def diagnostic_key(diagnostic: dict) -> str:
    """返回稳定的规范化文本，不生成任何派生摘要。"""

    category = str(diagnostic.get("category", "unknown"))
    summary = str(diagnostic.get("summary", ""))
    summary = re.sub(r"[A-Za-z]:[\\/][^:]+(?=:\d+:\d+)", "<path>", summary)
    summary = re.sub(r"/(?:[^\s:]+/)+[^\s:]+(?=:\d+:\d+)", "<path>", summary)
    summary = re.sub(r"\b\d+:\d+\b", "<loc>", summary)
    summary = re.sub(r"\b(?:mvar| metavariable)\.?\d+\b", "<mvar>", summary, flags=re.IGNORECASE)
    summary = re.sub(r"\s+", " ", summary).strip()
    return f"{category} | {summary[:700]}".strip()
