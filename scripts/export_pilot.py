"""Export a reviewed pilot as a sanitized, checksummed handoff directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

try:
    from validate_pilot import (
        DEFAULT_MANIFEST,
        DEFAULT_REVIEW,
        DEFAULT_RUNS,
        EXPECTED_CANDIDATE_POLICY,
        expected_pairs,
        load_runs,
        validate_review,
        validate_runs,
    )
except ModuleNotFoundError:  # Imported as scripts.export_pilot by tests or another module.
    from scripts.validate_pilot import (
        DEFAULT_MANIFEST,
        DEFAULT_REVIEW,
        DEFAULT_RUNS,
        EXPECTED_CANDIDATE_POLICY,
        expected_pairs,
        load_runs,
        validate_review,
        validate_runs,
    )


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
COPY_FILES = (
    "pilot_summary.csv",
    "pilot_failure_types.csv",
    "pilot_topic_summary.csv",
    "pilot_report.json",
    "pass_at_1.svg",
    "pass_at_3.svg",
)
SECRET_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}", re.IGNORECASE),
    re.compile(
        r"(?:api[_ -]?key|authorization|access[_ -]?token|refresh[_ -]?token|id[_ -]?token)"
        r"\s*[:=]\s*[\"']?[A-Za-z0-9._~+/=-]{12,}",
        re.IGNORECASE,
    ),
)
SECRET_KEY = re.compile(
    r"(?:api[_ -]?key|authorization|access[_ -]?token|refresh[_ -]?token|id[_ -]?token)",
    re.IGNORECASE,
)


def replacements() -> list[tuple[str, str]]:
    values = [
        (str(ROOT.resolve()), "<repo>"),
        (str(Path.home().resolve()), "<home>"),
        (str(Path(tempfile.gettempdir()).resolve()), "<temp>"),
    ]
    expanded: list[tuple[str, str]] = []
    for source, target in values:
        expanded.append((source, target))
        expanded.append((source.replace("\\", "/"), target))
    return sorted(set(expanded), key=lambda item: len(item[0]), reverse=True)


def sanitize(value: Any, path_replacements: list[tuple[str, str]]) -> Any:
    if isinstance(value, dict):
        return {key: sanitize(item, path_replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize(item, path_replacements) for item in value]
    if isinstance(value, str):
        cleaned = value
        for source, target in path_replacements:
            cleaned = cleaned.replace(source, target)
        return cleaned
    return value


def reject_secrets(value: Any, location: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEY.search(str(key)) and isinstance(item, str) and len(item.strip()) >= 12:
                raise ValueError(f"possible credential in {location}.{key}")
            reject_secrets(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_secrets(item, f"{location}[{index}]")
    elif isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise ValueError(f"possible credential in {location}")


def sanitize_text_file(path: Path, path_replacements: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8-sig")
    cleaned = sanitize(text, path_replacements)
    reject_secrets(cleaned, path.as_posix())
    path.write_text(cleaned, encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision() -> str:
    process = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return process.stdout.strip() if process.returncode == 0 else "unknown"


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def validate_artifacts(
    rows: list[dict],
    *,
    results: Path = RESULTS,
    report_path: Path | None = None,
) -> list[str]:
    """Require a matching formal report and every successful proof before export."""

    report_path = report_path or ROOT / "REPORT.md"
    required = [report_path, *(results / name for name in COPY_FILES)]
    errors = [f"missing report artifact: {path}" for path in required if not path.is_file()]
    experiment_ids = {str(row.get("experiment_id") or "").strip() for row in rows}
    report_json = results / "pilot_report.json"
    if report_json.is_file():
        try:
            report = json.loads(report_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid pilot_report.json: {exc}")
        else:
            if not isinstance(report, dict):
                errors.append("pilot_report.json must contain a JSON object")
            else:
                if str(report.get("status", "")).lower() != "formal":
                    errors.append("pilot_report.json is not a formal report")
                if len(experiment_ids) != 1 or report.get("experiment_id") not in experiment_ids:
                    errors.append("pilot_report.json experiment_id does not match the run log")
                if report.get("candidate_policy") != EXPECTED_CANDIDATE_POLICY:
                    errors.append("pilot_report.json does not record the current candidate security policy")

    successful: dict[tuple[str, str], dict] = {}
    for row in rows:
        if bool(row.get("compile_ok")):
            pair = (str(row.get("condition", "")), str(row.get("problem_id", "")))
            successful.setdefault(pair, row)
    for pair, row in sorted(successful.items()):
        source_file = str(row.get("source_file") or "").replace("\\", "/")
        theorem = str(row.get("theorem") or "").strip()
        source_stem = Path(source_file).stem
        if not source_stem or not theorem:
            errors.append(f"successful row is missing source_file/theorem metadata: {pair}")
            continue
        proof = results / "solutions" / pair[0] / f"{safe_name(source_stem)}__{safe_name(theorem)}.lean"
        if not proof.is_file():
            errors.append(f"missing successful proof artifact for {pair}: {proof}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--allow-cache-hits", action="store_true")
    args = parser.parse_args()

    rows = load_runs(args.runs)
    expected = expected_pairs(args.manifest)
    errors = validate_runs(rows, expected, args.allow_cache_hits)
    errors.extend(validate_review(args.review, expected, rows))
    errors.extend(validate_artifacts(rows))
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=True))
        return 1

    out = args.out.resolve()
    if out.exists():
        raise SystemExit(f"output already exists: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)

    path_replacements = replacements()
    cleaned_rows = sanitize(rows, path_replacements)
    reject_secrets(cleaned_rows)
    staging = Path(tempfile.mkdtemp(prefix=f".{out.name}-", dir=out.parent))
    try:
        with (staging / "real_pilot_runs.sanitized.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for row in cleaned_rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

        shutil.copy2(args.manifest, staging / "benchmark_manifest.json")
        shutil.copy2(args.review, staging / "manual_review.csv")
        report = ROOT / "REPORT.md"
        shutil.copy2(report, staging / report.name)
        for name in COPY_FILES:
            shutil.copy2(RESULTS / name, staging / name)
        solutions = RESULTS / "solutions"
        if solutions.exists():
            shutil.copytree(solutions, staging / "solutions")

        for path in sorted(item for item in staging.rglob("*") if item.is_file()):
            sanitize_text_file(path, path_replacements)

        files = sorted(path for path in staging.rglob("*") if path.is_file())
        manifest = {
            "format": "tracer-pilot-handoff-v1",
            "git_revision": git_revision(),
            "task_condition_pairs": len(expected),
            "records": len(rows),
            "cache_hits_allowed": bool(args.allow_cache_hits),
            "files": [
                {"path": path.relative_to(staging).as_posix(), "sha256": sha256(path)} for path in files
            ],
        }
        (staging / "handoff.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        staging.replace(out)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(json.dumps({"ok": True, "out": str(out), "files": len(files) + 1}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
