"""Explicit, bounded JSON memory for a single game's Python tool calls.

The model writes this memory itself. No summaries, game-specific facts, game
actions or cross-game sharing are added by the harness.
"""
from __future__ import annotations

import ast
import textwrap

GUIDE = """

Explicit Python memory:
- `memory` is a dictionary that starts empty for each game. Its JSON-compatible
  contents persist across Python calls, yield resumptions, history trimming and
  level changes within that game. It is cleared when a different game starts.
- Use `memory` to keep useful observations, tested mechanics, rejected hypotheses,
  compact geometry or search results rather than rebuilding them each call.
  For example: `memory['mechanics'] = {'tested_rule': '...','evidence': '...'}`;
  retrieve it later with `print(memory.get('mechanics'))`.
- Distinguish verified observations from guesses. Tag layout-specific data with
  current_frame.level and check it against the current board before reuse.
- Values must be JSON-compatible (dict/list/str/number/bool/None), with string
  dictionary keys, at most 32 KiB
  serialized for the entire dictionary. Store derived data, not frame objects,
  functions or imports. Invalid or oversized updates are rejected with a notice;
  the previously committed dictionary survives. No file access is involved.
- Ordinary variables still reset, eligible functions are retained as before,
  and provided game-state globals still refresh after action(). No automatic
  summary is written for you. Inspect `memory` when earlier context is missing.
"""

COLLECT = '''
def _collect_python_memory():
    try:
        value = runtime_globals.get("memory")
        if not isinstance(value, dict):
            raise ValueError("memory must remain a dictionary")
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode("utf8")) > 32768:
            raise ValueError("memory exceeds its 32 KiB serialized limit")
        decoded = json.loads(encoded)
        if decoded != value:
            raise ValueError("memory requires string dictionary keys and JSON-native values")
        return {"memory": decoded}
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        return {"memory": None, "memory_notice": "Memory update rejected: " + str(exc) + ". Previously committed memory retained."}
'''


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError("Python-memory anchor mismatch: " + before[:85])
    return source.replace(before, after, 1)


def patch_sandbox(source):
    source = replace_once(source,
        '        runtime_globals["__builtins__"]["__import__"] = _safe_import\n',
        '        runtime_globals["memory"] = dict((initial.get("state") or {}).get("memory") or {})\n'
        '        runtime_globals["__builtins__"]["__import__"] = _safe_import\n')
    source = replace_once(source, '        def _collect_retention_payload():\n',
                          textwrap.indent(COLLECT, "        ") + '\n        def _collect_retention_payload():\n')
    anchor = '                    **_collect_retention_payload(),\n'
    if source.count(anchor) != 2:
        raise ValueError("Expected final and error result collection anchors")
    source = source.replace(anchor, anchor + '                    **_collect_python_memory(),\n')
    source = replace_once(source,
        '                    "keepable_functions": list(message.get("keepable_functions") or []),\n',
        '                    "keepable_functions": list(message.get("keepable_functions") or []),\n'
        '                    "memory": message.get("memory"),\n'
        '                    "memory_notice": message.get("memory_notice"),\n')
    ast.parse(source)
    return source


def record_memory(agent, sandbox_result, payload):
    value = sandbox_result.get("memory")
    if isinstance(value, dict):
        agent._python_memory = value
    notice = sandbox_result.get("memory_notice")
    if notice:
        payload["memory_notice"] = notice


def patch_agent(source):
    source = replace_once(source,
        'from inference.agent.python_tool_sandbox import run_sandboxed_python\n',
        'from inference.agent.python_tool_sandbox import run_sandboxed_python\n'
        'from inference.utils.python_memory import record_memory\n')
    source = replace_once(source,
        '            self._history_messages = []\n            self._session_total_tokens = 0\n',
        '            self._python_memory = {}\n'
        '            self._history_messages = []\n            self._session_total_tokens = 0\n')
    source = replace_once(source,
        '                "history": _ascii_history_view_payload(refreshed_history),\n',
        '                "history": _ascii_history_view_payload(refreshed_history),\n'
        '                "memory": getattr(self, "_python_memory", {}),\n')
    source = replace_once(source,
        '        payload: dict[str, Any] = {"tool": "python"}\n',
        '        payload: dict[str, Any] = {"tool": "python"}\n'
        '        record_memory(self, sandbox_result, payload)\n')
    anchor = '    if _level_transfer_guidance_enabled():\n        prompt = apply_level_transfer_system_guidance(prompt)\n    return prompt\n'
    source = replace_once(source, anchor, anchor.replace('    return prompt\n', f'    prompt += {GUIDE!r}\n    return prompt\n'))
    ast.parse(source)
    return source


def install(bundle):
    from pathlib import Path
    base = Path(bundle) / "src/ARC3-Inference/inference"
    for name, transform in [("python_tool_sandbox.py", patch_sandbox), ("tool_agent.py", patch_agent)]:
        path = base / "agent" / name
        path.write_text(transform(path.read_text(encoding="utf8")), encoding="utf8")
