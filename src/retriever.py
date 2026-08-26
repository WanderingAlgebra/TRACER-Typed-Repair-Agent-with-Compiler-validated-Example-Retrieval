"""为条件 C 提供本地示例检索。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*|[0-9]+")
DECLARATION_HEADER_RE = re.compile(
    r"(?ms)^[ \t]*(?:(?:theorem|lemma)[ \t]+[A-Za-z_][A-Za-z0-9_'.]*|example)"
    r"(?P<header>.*?)[ \t]*:="
)
IDENTIFIER_RE = re.compile(r"[^\W\d][\w']*", re.UNICODE)
LEAN_TOKEN_RE = re.compile(r"[^\W\d][\w']*|:=|=>|→|←|↔|∧|∨|¬|≤|≥|≠|\S", re.UNICODE)


@dataclass(frozen=True)
class Example:
    path: str
    tags: tuple[str, ...]
    text: str


def statement_fingerprints(text: str) -> set[str]:
    """为 Lean 声明头生成忽略 binder 名称和空白的稳定指纹。"""

    fingerprints: set[str] = set()
    for declaration in DECLARATION_HEADER_RE.finditer(text):
        header = declaration.group("header").strip()
        binder_names: list[str] = []
        for binder in re.finditer(r"[({][ \t]*([^:(){}]+?)[ \t]*:", header):
            binder_names.extend(IDENTIFIER_RE.findall(binder.group(1)))
        replacements = {name: f"_v{index}" for index, name in enumerate(binder_names)}
        tokens = LEAN_TOKEN_RE.findall(header)
        fingerprints.add("".join(replacements.get(token, token) for token in tokens))
    return fingerprints


def find_retrieval_leaks(
    benchmarks: list[tuple[str, str]], examples: list[Example]
) -> list[dict[str, str]]:
    """返回与冻结题目声明相同（允许变量改名）的检索示例。"""

    benchmark_by_fingerprint: dict[str, set[str]] = {}
    for benchmark_id, declaration in benchmarks:
        for fingerprint in statement_fingerprints(declaration):
            benchmark_by_fingerprint.setdefault(fingerprint, set()).add(benchmark_id)
    leaks: list[dict[str, str]] = []
    for example in examples:
        for fingerprint in statement_fingerprints(example.text):
            for benchmark_id in sorted(benchmark_by_fingerprint.get(fingerprint, set())):
                leaks.append({"benchmark_id": benchmark_id, "example_path": example.path})
    return leaks


def tokenize(text: str) -> set[str]:
    tokens: set[str] = set()
    for match in TOKEN_RE.finditer(text.lower()):
        token = match.group(0)
        tokens.add(token)
        tokens.update(part for part in token.split("_") if part)
    return tokens


def load_examples(root: Path) -> list[Example]:
    examples: list[Example] = []
    for path in sorted(root.glob("*.lean")):
        text = path.read_text(encoding="utf-8")
        tag_line = next((line for line in text.splitlines() if line.startswith("-- tags:")), "")
        tags = tuple(tag_line.removeprefix("-- tags:").strip().split())
        examples.append(Example(str(path), tags, text))
    return examples


def retrieve(query: str, examples: list[Example], top_k: int = 2) -> list[dict[str, object]]:
    query_tokens = tokenize(query)
    ranked: list[tuple[float, Example]] = []
    for example in examples:
        candidate_tokens = tokenize(" ".join(example.tags) + " " + example.text)
        overlap = query_tokens & candidate_tokens
        score = len(overlap) / max(1, len(query_tokens))
        if score > 0:
            ranked.append((score, example))
    ranked.sort(key=lambda item: (-item[0], item[1].path))
    return [
        {
            "path": example.path,
            "score": round(score, 4),
            "tags": list(example.tags),
            "snippet": example.text[:500],
        }
        for score, example in ranked[:top_k]
    ]
