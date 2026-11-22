import unittest
from pathlib import Path
from types import SimpleNamespace

from src.stagnation_recovery import LEVEL_TOKEN_LIMIT, maybe_restart, patch_source


class RecoveryTests(unittest.TestCase):
    def agent(self, tokens=LEVEL_TOKEN_LIMIT):
        a = SimpleNamespace(
            _session_generated_tokens=tokens, _tokens_at_level_start=0,
            _history_messages=[{"role": "user", "content": "old"}],
            _kept_functions={"helper": "old"}, _last_step_summary={},
            _session_total_tokens=123456, _resume_after_yield=True,
            _resume_reason="yield_bare", _retained_clear_notice="old",
            _text_chars_per_token=4, evicted=False,
        )
        a._note_history_evicted = lambda: setattr(a, "evicted", True)
        return a

    def test_boundary_and_immutable_accounting(self):
        a = self.agent(LEVEL_TOKEN_LIMIT - 1)
        f = SimpleNamespace(level=1, step=40)
        self.assertEqual(maybe_restart(a, f), "")
        a._session_generated_tokens += 1
        notice = maybe_restart(a, f)
        self.assertIn("Fresh review", notice)
        self.assertEqual(a._history_messages, [])
        self.assertEqual(a._kept_functions, {})
        self.assertEqual(a._session_generated_tokens, LEVEL_TOKEN_LIMIT)
        self.assertEqual(a._session_total_tokens, 123456)
        self.assertEqual(a._tokens_at_level_start, 0)
        self.assertEqual(f.step, 40)
        self.assertFalse(a._resume_after_yield)
        self.assertTrue(a.evicted)

    def test_retry_and_once_per_level(self):
        a = self.agent()
        f = SimpleNamespace(level=1, step=40)
        notice = maybe_restart(a, f)
        self.assertEqual(maybe_restart(a, f), notice)
        a._session_generated_tokens += 2048
        a._history_messages = ["successful new reasoning"]
        self.assertEqual(maybe_restart(a, f), "")
        self.assertEqual(a._history_messages, ["successful new reasoning"])
        a._tokens_at_level_start = a._session_generated_tokens
        f.level = 2
        self.assertEqual(maybe_restart(a, f), "")
        a._session_generated_tokens += LEVEL_TOKEN_LIMIT
        self.assertIn("Fresh review", maybe_restart(a, f))

    def test_finished_game_is_untouched(self):
        a = self.agent()
        a._last_step_summary = {"run_complete": True}
        self.assertEqual(maybe_restart(a, SimpleNamespace(level=6, step=50)), "")
        self.assertTrue(a._history_messages)
        self.assertEqual(maybe_restart(a, None), "")

    @unittest.skipUnless(Path("data/ref-2026-10-14/upstream/ARC3-Inference/inference/agent/tool_agent.py").exists(), "needs upstream harness checkout")
    def test_patch_real_harness(self):
        path = Path("data/ref-2026-10-14/upstream/ARC3-Inference/inference/agent/tool_agent.py")
        source = path.read_text(encoding="utf8")
        patched = patch_source(source)
        self.assertIn("recovery_notice + self._build_user_prompt", patched)
        with self.assertRaises(RuntimeError):
            patch_source(patched)


if __name__ == "__main__":
    unittest.main()
