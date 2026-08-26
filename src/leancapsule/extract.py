"""从 Lean 文件中提取可尝试独立编译的定理片段。"""

from __future__ import annotations

import re

from compiler import declaration_scope


IMPORT_RE = re.compile(r"(?m)^\s*import\s+[^\r\n]+$")
BLOCK_RE = re.compile(
    r"(?m)^\s*(?:(?P<namespace>namespace)\s+(?P<namespace_name>[A-Za-z_][A-Za-z0-9_.]*)"
    r"|(?P<section>section)(?:\s+(?P<section_name>[A-Za-z_][A-Za-z0-9_]*))?"
    r"|(?P<end>end)(?:\s+(?P<end_name>[A-Za-z_][A-Za-z0-9_.]*))?)\s*$"
)


def _namespace_stack(source: str, position: int) -> list[str]:
    """返回 position 处仍打开的 namespace，忽略已经结束的块。"""

    blocks: list[tuple[str, str | None]] = []
    for match in BLOCK_RE.finditer(source[:position]):
        if match.group("namespace"):
            blocks.append(("namespace", match.group("namespace_name")))
        elif match.group("section"):
            blocks.append(("section", match.group("section_name")))
        elif blocks:
            end_name = match.group("end_name")
            if end_name is None:
                blocks.pop()
                continue
            matching = next((index for index in range(len(blocks) - 1, -1, -1) if blocks[index][1] == end_name), None)
            if matching is not None:
                del blocks[matching:]
            else:
                blocks.pop()
    return [name for kind, name in blocks if kind == "namespace" and name]


def extract_theorem(source: str, theorem: str) -> str:
    """保留 imports、目标定理和外层 namespace，供后续编译验证。"""

    start, end = declaration_scope(source, theorem)
    imports = "\n".join(match.group(0).strip() for match in IMPORT_RE.finditer(source))
    namespaces = _namespace_stack(source, start)
    body = source[start:end].strip()
    openings = "\n".join(f"namespace {namespace}" for namespace in namespaces)
    closings = "\n".join(f"end {namespace}" for namespace in reversed(namespaces))
    parts = [part for part in (imports, openings, body, closings) if part]
    return "\n\n".join(parts) + "\n"
