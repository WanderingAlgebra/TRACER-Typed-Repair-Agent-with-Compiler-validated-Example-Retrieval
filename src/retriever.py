"""Small local example retriever for condition C."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*|[0-9]+")


@dataclass(frozen=True)
class Example:
    path: str
    tags: tuple[str, ...]
    text: str


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
