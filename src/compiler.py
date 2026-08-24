"""Generic Lean source patching and kernel compilation."""

from __future__ import annotations

import re
import subprocess
import tempfile
import time
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CompileResult:
    ok: bool
    elapsed_ms: float
    diagnostics: str
    isolated_source: str
    timed_out: bool = False
    returncode: int | None = None
    compiler_command: list[str] | None = None


def _namespace_before(source: str, position: int) -> str | None:
    matches = list(re.finditer(r"(?m)^namespace\s+([A-Za-z_][A-Za-z0-9_.]*)\s*$", source[:position]))
    return matches[-1].group(1) if matches else None


def declaration_scope(source: str, theorem_name: str) -> tuple[int, int]:
    short_name = theorem_name.rsplit(".", 1)[-1]
    matches = list(re.finditer(rf"(?m)^\s*(?:theorem|lemma)\s+{re.escape(short_name)}\b", source))
    match = None
    requested_namespace = theorem_name.rsplit(".", 1)[0] if "." in theorem_name else None
    for candidate in matches:
        if requested_namespace is None or _namespace_before(source, candidate.start()) == requested_namespace:
            match = candidate
            break
    if match is None and matches:
        match = matches[0]
    if match is None:
        raise ValueError(f"找不到目标定理: {theorem_name}")
    next_declaration = re.search(r"(?m)^\s*(?:theorem|lemma)\s+", source[match.end():])
    if next_declaration:
        return match.start(), match.end() + next_declaration.start()
    namespace_name = _namespace_before(source, match.start())
    namespace = re.search(rf"(?m)^namespace\s+{re.escape(namespace_name)}\s*$", source) if namespace_name else None
    if namespace:
        namespace_end = source.find(f"\nend {namespace_name}", match.end())
        if namespace_end >= 0:
            return match.start(), namespace_end
    return match.start(), len(source)


_declaration_scope = declaration_scope


def patch_proof_region(source: str, candidate: str, theorem_name: str, start: str, end: str, placeholder: str = "sorry") -> str:
    scope_start, scope_end = declaration_scope(source, theorem_name)
    scope = source[scope_start:scope_end]
    if start in candidate or end in candidate:
        raise ValueError("候选证明不能包含证明区域标记")
    if scope.count(start) == 1 and scope.count(end) == 1:
        left = scope_start + scope.index(start) + len(start)
        right = scope_start + scope.index(end)
    else:
        placeholders = list(re.finditer(rf"(?<![A-Za-z0-9_]){re.escape(placeholder)}(?![A-Za-z0-9_])", scope))
        if len(placeholders) != 1:
            raise ValueError("目标定理必须包含唯一证明区域标记，或唯一占位符")
        left = scope_start + placeholders[0].start()
        right = scope_start + placeholders[0].end()
    if left > right:
        raise ValueError("证明区域标记顺序错误")
    return source[:left] + "\n  " + candidate.strip() + "\n  " + source[right:]


def isolate_target(source: str, patched: str, theorem_name: str) -> str:
    scope_start, scope_end = declaration_scope(patched, theorem_name)
    namespace_name = _namespace_before(source, scope_start)
    namespace = re.search(rf"(?m)^namespace\s+{re.escape(namespace_name)}\s*$", source) if namespace_name else None
    if namespace is None:
        return source[:scope_start] + patched[scope_start:scope_end] + "\n"
    return (
        source[: namespace.end()]
        + "\n\n"
        + patched[scope_start:scope_end]
        + f"\n\nend {namespace_name}\n"
    )


def compile_candidate(
    source_path: Path,
    source: str,
    candidate: str,
    theorem_name: str,
    start_marker: str = "-- PROOF_START",
    end_marker: str = "-- PROOF_END",
    timeout: float = 20.0,
    placeholder: str = "sorry",
) -> CompileResult:
    patched = patch_proof_region(source, candidate, theorem_name, start_marker, end_marker, placeholder)
    isolated = isolate_target(source, patched, theorem_name)
    with tempfile.TemporaryDirectory(prefix="lean-proof-repair-") as temp_dir:
        temp_path = Path(temp_dir) / source_path.name
        temp_path.write_text(isolated, encoding="utf-8")
        started = time.perf_counter()
        try:
            environment = os.environ.copy()
            if not environment.get("ELAN_HOME"):
                user_profile = environment.get("USERPROFILE")
                if user_profile and (Path(user_profile) / ".elan").exists():
                    environment["ELAN_HOME"] = str(Path(user_profile) / ".elan")
            project_root = next((parent for parent in (source_path.parent, *source_path.parent.parents) if (parent / "lakefile.toml").exists()), None)
            command = ["lake", "env", "lean", str(temp_path)] if project_root else ["lean", str(temp_path)]
            process = subprocess.run(
                command,
                cwd=project_root or source_path.parent,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
                check=False,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""
            diagnostics = f"Lean 编译超时（{timeout:g}s）\n{stdout}\n{stderr}".strip()
            return CompileResult(False, elapsed_ms, diagnostics, isolated, True, None, command)
        except FileNotFoundError as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            return CompileResult(False, elapsed_ms, f"编译器不可用: {exc}", isolated, False, None, command)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    diagnostics = "\n".join(part for part in [process.stdout, process.stderr] if part).strip()
    return CompileResult(process.returncode == 0, elapsed_ms, diagnostics, isolated, False, process.returncode, command)
