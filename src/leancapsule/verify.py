"""批量验证 capsule 目录。"""

from __future__ import annotations

from pathlib import Path

from .replay import replay_capsule


def verify_directory(root: Path, timeout: float = 180.0) -> dict:
    """递归寻找 capsule.json，返回逐项与汇总状态。"""

    root = root.resolve()
    if not root.is_dir():
        return {"ok": False, "total": 0, "passed": 0, "failed": 0, "error": "验证目录不存在", "results": []}
    capsules = sorted({path.parent for path in root.rglob("capsule.json")})
    if not capsules:
        return {"ok": False, "total": 0, "passed": 0, "failed": 0, "error": "未找到 capsule.json", "results": []}
    results: list[dict] = []
    for path in capsules:
        try:
            results.append(replay_capsule(path, timeout=timeout))
        except Exception as exc:
            results.append({"ok": False, "capsule": path.name, "error": f"回放异常: {type(exc).__name__}: {exc}"})
    passed = sum(1 for result in results if result.get("ok"))
    return {"ok": passed == len(results), "total": len(results), "passed": passed, "failed": len(results) - passed, "results": results}
