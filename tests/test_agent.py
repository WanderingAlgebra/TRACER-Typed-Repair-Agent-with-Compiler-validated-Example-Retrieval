import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent import estimate_cost, prompt_api_key, prompt_for, solve_problem
from cache import RequestCache
from compiler import (
    compile_candidate,
    candidate_safety_violation,
    declaration_scope,
    diagnostics_use_sorry,
    find_project_root,
    lean_subprocess_environment,
    lean_command,
)
from provider import Generation, MockProvider
from retriever import Example, find_retrieval_leaks, load_examples


LEAN_TIMEOUT = float(os.environ.get("TRACER_TEST_LEAN_TIMEOUT", "60"))


class SequenceProvider:
    name = "sequence"

    def __init__(self, candidates):
        self.candidates = list(candidates)
        self.calls = 0

    def metadata(self):
        return {"provider": self.name, "test_case": "feedback_repair"}

    def generate(self, prompt):
        candidate = self.candidates[min(self.calls, len(self.candidates) - 1)]
        self.calls += 1
        return Generation(candidate, {"prompt_tokens": len(prompt), "total_tokens": len(prompt)}, self.name)


class BrokenProvider:
    name = "broken"

    def metadata(self):
        return {"provider": self.name, "test_case": "provider_error"}

    def generate(self, prompt):
        raise RuntimeError("simulated provider outage")


class AgentEndToEndTest(unittest.TestCase):
    def setUp(self):
        self.source_path = ROOT / "lean_project" / "Benchmarks" / "Evaluation18.lean"

    def test_success_is_saved_and_original_is_unchanged(self):
        original = self.source_path.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            result = solve_problem(
                self.source_path,
                "Eval18.and_swap_eval",
                "A",
                MockProvider("```lean\nby\n  intro h\n  exact And.intro h.right h.left\n```"),
                1,
                LEAN_TIMEOUT,
                ROOT / "examples",
                base / "cache.sqlite3",
                base / "solutions",
                base / "runs.jsonl",
            )
            self.assertTrue(result["compile_ok"], result)
            self.assertEqual(original, self.source_path.read_text(encoding="utf-8"))
            saved = list((base / "solutions" / "A").glob("*.lean"))
            self.assertEqual(len(saved), 1)
            self.assertNotRegex(saved[0].read_text(encoding="utf-8"), r"\b(sorry|admit)\b")

    def test_bad_candidate_is_retried_and_failure_is_saved(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            result = solve_problem(
                self.source_path,
                "Eval18.and_swap_eval",
                "B",
                MockProvider("by exact rfl"),
                2,
                LEAN_TIMEOUT,
                ROOT / "examples",
                base / "cache.sqlite3",
                base / "solutions",
                base / "runs.jsonl",
            )
            self.assertFalse(result["compile_ok"])
            self.assertTrue((base / "solutions" / "failures").exists())

    def test_same_prompt_is_not_reused_from_cache_within_one_run(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            provider = SequenceProvider(["by exact rfl"])
            solve_problem(
                self.source_path,
                "Eval18.and_swap_eval",
                "A",
                provider,
                2,
                LEAN_TIMEOUT,
                ROOT / "examples",
                base / "cache.sqlite3",
                base / "solutions",
                base / "runs.jsonl",
            )
            rows = [json.loads(line) for line in (base / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(provider.calls, 2)
            self.assertEqual([row["cache_hit"] for row in rows], [False, False])

    def test_second_identical_run_hits_persistent_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            provider = MockProvider("by\n  intro h\n  exact And.intro h.right h.left")
            kwargs = dict(
                source_path=self.source_path,
                theorem_name="Eval18.and_swap_eval",
                condition="A",
                provider=provider,
                max_rounds=1,
                timeout=LEAN_TIMEOUT,
                examples_dir=ROOT / "examples",
                cache_path=base / "cache.sqlite3",
                output_dir=base / "solutions",
                log_path=base / "runs.jsonl",
            )
            self.assertTrue(solve_problem(**kwargs)["compile_ok"])
            self.assertTrue(solve_problem(**kwargs)["compile_ok"])
            rows = [json.loads(line) for line in (base / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(rows[-1]["cache_hit"])

    def test_feedback_failure_then_success_is_logged(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            provider = SequenceProvider(["by exact rfl", "by\n  intro h\n  exact And.intro h.right h.left"])
            result = solve_problem(
                self.source_path,
                "Eval18.and_swap_eval",
                "B",
                provider,
                3,
                LEAN_TIMEOUT,
                ROOT / "examples",
                base / "cache.sqlite3",
                base / "solutions",
                base / "runs.jsonl",
            )
            self.assertTrue(result["compile_ok"], result)
            self.assertEqual(result["round"], 2)
            rows = [json.loads(line) for line in (base / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertNotEqual(rows[0]["diagnostic"]["category"], "ok")
            self.assertTrue(rows[1]["compile_ok"])

    def test_provider_error_is_traceable(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            result = solve_problem(
                self.source_path,
                "Eval18.and_swap_eval",
                "A",
                BrokenProvider(),
                1,
                LEAN_TIMEOUT,
                ROOT / "examples",
                base / "cache.sqlite3",
                base / "solutions",
                base / "runs.jsonl",
            )
            self.assertFalse(result["compile_ok"])
            self.assertEqual(result["diagnostic"]["category"], "provider_error")
            self.assertIn("simulated provider outage", result["provider_error"])

    def test_unique_sorry_placeholder_is_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_path = base / "input.lean"
            source_path.write_text("import Std\nnamespace Demo\ntheorem target (p : Prop) : p → p := sorry\nend Demo\n", encoding="utf-8")
            result = solve_problem(
                source_path,
                "Demo.target",
                "A",
                MockProvider("by\n  intro hp\n  exact hp"),
                1,
                LEAN_TIMEOUT,
                ROOT / "examples",
                base / "cache.sqlite3",
                base / "solutions",
                base / "runs.jsonl",
            )
            self.assertTrue(result["compile_ok"], result)

    def test_candidate_cannot_hide_a_sorryax_placeholder(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            result = solve_problem(
                self.source_path,
                "Eval18.and_swap_eval",
                "A",
                MockProvider("by exact sorryAx _ true"),
                1,
                LEAN_TIMEOUT,
                ROOT / "examples",
                base / "cache.sqlite3",
                base / "solutions",
                base / "runs.jsonl",
            )
            self.assertFalse(result["compile_ok"])
            self.assertEqual(result["diagnostic"]["category"], "placeholder_candidate")

    def test_candidate_cannot_execute_meta_code_or_inject_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            result = solve_problem(
                self.source_path,
                "Eval18.and_swap_eval",
                "A",
                MockProvider('by\n  run_tac IO.println "do not run"'),
                1,
                LEAN_TIMEOUT,
                ROOT / "examples",
                base / "cache.sqlite3",
                base / "solutions",
                base / "runs.jsonl",
            )
            self.assertFalse(result["compile_ok"])
            self.assertEqual(result["diagnostic"]["category"], "unsafe_candidate")
        self.assertIsNotNone(candidate_safety_violation("by trivial\n#eval 1"))

    def test_isolated_target_keeps_valid_local_helpers(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source_path = base / "Helper.lean"
            source = (
                "import Std\n"
                "namespace Demo\n"
                "def helper (p : Prop) (h : p) : p := h\n"
                "theorem target (p : Prop) : p → p := sorry\n"
                "end Demo\n"
            )
            source_path.write_text(source, encoding="utf-8")
            result = compile_candidate(
                source_path,
                source,
                "by\n  intro h\n  exact helper p h",
                "Demo.target",
                timeout=LEAN_TIMEOUT,
            )
            self.assertTrue(result.ok, result.diagnostics)
            self.assertIn("def helper", result.isolated_source)

    def test_external_file_uses_repository_toolchain(self):
        with tempfile.TemporaryDirectory() as temp:
            source_path = Path(temp) / "input.lean"
            source_path.write_text("import Std\nexample : True := by trivial\n", encoding="utf-8")
            with patch("compiler.shutil.which", return_value="elan"):
                command = lean_command(source_path)
            expected_toolchain = (ROOT / "lean-toolchain").read_text(encoding="utf-8").strip()
            self.assertEqual(command[:4], ["elan", "run", expected_toolchain, "lean"])

    def test_lakefile_lean_is_recognized_as_a_project_root(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            (base / "lakefile.lean").write_text("import Lake\n", encoding="utf-8")
            source = base / "Nested" / "Demo.lean"
            source.parent.mkdir()
            source.write_text("example : True := by trivial\n", encoding="utf-8")
            self.assertEqual(find_project_root(source), base.resolve())

    def test_qualified_theorem_selection_never_falls_back(self):
        source = (
            "namespace A\ntheorem target : True := by trivial\nend A\n"
            "namespace B\ntheorem target : True := by trivial\nend B\n"
        )
        start, _ = declaration_scope(source, "B.target")
        self.assertGreater(start, source.index("namespace B"))
        with self.assertRaisesRegex(ValueError, "不唯一"):
            declaration_scope(source, "target")
        with self.assertRaisesRegex(ValueError, "找不到"):
            declaration_scope(source, "Missing.target")

    def test_sorry_warning_variants_are_detected(self):
        self.assertTrue(diagnostics_use_sorry("warning: declaration uses 'sorry'"))
        self.assertTrue(diagnostics_use_sorry("warning: declaration uses axiom `sorryAx` from sorry"))

    def test_lean_subprocess_environment_excludes_parent_secrets(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            os.environ,
            {
                "LEAN_PROOF_API_KEY": "provider-secret-value",
                "GITHUB_TOKEN": "github-secret-value",
                "UNRELATED_SETTING": "must-not-pass",
                "GIT_CONFIG_COUNT": "2",
                "GIT_CONFIG_KEY_0": "safe.directory",
                "GIT_CONFIG_VALUE_0": str(ROOT),
                "GIT_CONFIG_KEY_1": "url.https://secret.example/.insteadOf",
                "GIT_CONFIG_VALUE_1": "https://github.com/",
            },
            clear=False,
        ):
            scratch = Path(temp) / "home"
            environment = lean_subprocess_environment(scratch, ROOT)
        self.assertNotIn("LEAN_PROOF_API_KEY", environment)
        self.assertNotIn("GITHUB_TOKEN", environment)
        self.assertNotIn("UNRELATED_SETTING", environment)
        self.assertEqual(environment["GIT_CONFIG_COUNT"], "1")
        self.assertEqual(environment["GIT_CONFIG_KEY_0"], "safe.directory")
        self.assertNotIn("GIT_CONFIG_KEY_1", environment)
        self.assertEqual(environment["HOME"], str(scratch))
        self.assertEqual(environment["TRACER_CANDIDATE_ENV"], "isolated")


class CacheTest(unittest.TestCase):
    def test_persistent_exact_request_hit(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "requests.sqlite3"
            with RequestCache(path) as cache:
                cache.put("same request", Generation("by rfl", {"total_tokens": 3}, "mock"))
            with RequestCache(path) as cache:
                found = cache.get("same request")
            self.assertIsNotNone(found)
            self.assertEqual(found.candidate, "by rfl")

    def test_condition_b_prompt_contains_feedback(self):
        source = ROOT.joinpath("lean_project", "Benchmarks", "Evaluation18.lean").read_text(encoding="utf-8")
        prompt = prompt_for(source, "Eval18.and_swap_eval", "B", {"feedback": "类别=type_mismatch"}, [])
        self.assertIn("type_mismatch", prompt)

    def test_condition_c_prompt_contains_retrieved_text(self):
        source = ROOT.joinpath("lean_project", "Benchmarks", "Evaluation18.lean").read_text(encoding="utf-8")
        prompt = prompt_for(source, "Eval18.and_swap_eval", "C", {"feedback": "x"}, [{"snippet": "example proof"}])
        self.assertIn("example proof", prompt)

    def test_unknown_usage_does_not_become_zero_cost(self):
        self.assertIsNone(estimate_cost(None, {"input_price_per_1k": 1.0, "output_price_per_1k": 1.0}))

    def test_api_key_prompt_never_echoes_length_or_characters(self):
        output = io.StringIO()
        with patch("agent.getpass.getpass", return_value="sk-secret-lastfour"), contextlib.redirect_stderr(output):
            self.assertEqual(prompt_api_key(), "sk-secret-lastfour")
        confirmation = output.getvalue()
        self.assertNotIn("lastfour", confirmation)
        self.assertNotIn("长度", confirmation)
        self.assertNotIn("末四位", confirmation)

    def test_retrieval_leakage_detector_is_alpha_rename_aware(self):
        benchmark = "theorem target (p q : Prop) : p ∧ q → q ∧ p := by trivial"
        example = Example(
            "leak.lean",
            (),
            "example (left right : Prop) :\n  left ∧ right → right ∧ left := by trivial",
        )
        leaks = find_retrieval_leaks([("target", benchmark)], [example])
        self.assertEqual(leaks[0]["benchmark_id"], "target")

    def test_repository_retrieval_corpus_does_not_duplicate_frozen_tasks(self):
        source = (ROOT / "lean_project" / "Benchmarks" / "Evaluation18.lean").read_text(encoding="utf-8")
        tasks = json.loads((ROOT / "benchmarks" / "manifest.json").read_text(encoding="utf-8"))
        declarations = [
            (task["id"], theorem_scope)
            for task in tasks
            for theorem_scope in [
                source[slice(*declaration_scope(source, task["theorem"]))]
            ]
        ]
        self.assertEqual(find_retrieval_leaks(declarations, load_examples(ROOT / "examples")), [])
