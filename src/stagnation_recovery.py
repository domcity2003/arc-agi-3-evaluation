"""One context restart per expensive, unfinished level; no game actions.

Inspired by heliosli's public fresh-review experiment. Threshold selected from
our v7 practice trace: 3/57 completed levels exceeded 49,152 tokens, while ten
unfinished attempts spent roughly 48K or more. This is a hypothesis, not a
calibrated completion model.
"""
import logging

LEVEL_TOKEN_LIMIT = 49_152
log = logging.getLogger(__name__)


def maybe_restart(agent, frame):
    if frame is None or int(frame.level) <= 0:
        return ""
    level = int(frame.level)
    generated = int(agent._session_generated_tokens)
    pending = getattr(agent, "_recovery_pending", None)
    if pending:
        pending_level, at_tokens, notice = pending
        if pending_level == level and generated <= at_tokens:
            # The analyzer rolls back tokens/history on failed HTTP requests.
            # Keep the fresh opener until one request actually succeeds.
            agent._resume_after_yield = False
            agent._resume_reason = ""
            return notice
        agent._recovery_pending = None
    seen = getattr(agent, "_recovery_levels", set())
    if level in seen or (agent._last_step_summary or {}).get("run_complete"):
        return ""
    spent = max(0, generated - int(agent._tokens_at_level_start))
    if spent < LEVEL_TOKEN_LIMIT:
        return ""
    old_messages = len(agent._history_messages)
    agent._history_messages = []
    agent._kept_functions = {}
    agent._retained_clear_notice = ""
    agent._resume_after_yield = False
    agent._resume_reason = ""
    agent._text_chars_per_token = None
    agent._note_history_evicted()
    agent._recovery_levels = seen | {level}
    notice = (
        f"Fresh review: {spent} generated tokens have not completed this level. "
        "Earlier conversation and your retained Python functions were cleared once. "
        "The current board and actual recorded observations are unchanged. "
        "No action or game reset occurred. Inspect history, transitions, and "
        "death_ledger in Python to recover useful evidence. Reconsider the goal "
        "and mechanics from observations; earlier interpretations may be wrong. "
        "Test a concrete prediction before another long search.\n\n"
    )
    agent._recovery_pending = (level, generated, notice)
    log.warning("V12_CONTEXT_RECOVERY level=%d step=%d tokens=%d messages=%d",
                level, int(frame.step), spent, old_messages)
    return notice


def patch_source(source):
    """Patch between analyzer invocations, with exact anchors and syntax check."""
    import ast
    replacements = [
        ("from inference.agent.python_tool_sandbox import run_sandboxed_python\n",
         "from inference.agent.python_tool_sandbox import run_sandboxed_python\n"
         "from inference.utils.stagnation_recovery import maybe_restart\n"),
        ("            self._history_messages = []\n            self._session_total_tokens = 0\n",
         "            self._recovery_levels = set()\n"
         "            self._recovery_pending = None\n"
         "            self._history_messages = []\n            self._session_total_tokens = 0\n"),
        ("        current_frame, history_entries = load_runtime_state(state_path)\n"
         "        user_prompt = self._build_user_prompt(\n",
         "        current_frame, history_entries = load_runtime_state(state_path)\n"
         "        recovery_notice = maybe_restart(self, current_frame)\n"
         "        user_prompt = recovery_notice + self._build_user_prompt(\n"),
    ]
    for before, after in replacements:
        if source.count(before) != 1:
            raise RuntimeError("Stagnation recovery anchor mismatch: " + before[:90])
        source = source.replace(before, after, 1)
    ast.parse(source)
    return source
