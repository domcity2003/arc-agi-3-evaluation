"""Pure observation helpers embedded inside the existing Python sandbox.

No game IDs, game implementations, actions, or new state persistence.
"""
from __future__ import annotations

import ast
import textwrap


GUIDE = """

Built-in observation helpers inside Python (no game actions):
- `inspect_objects(colors=None, min_pixels=1, frame=None)` returns compact objects
  with id, color, pixels, bbox, rotation, hash and children. bbox is inclusive
  [top_row, left_col, bottom_row, right_col]. Defaults to current_frame;
  colors='Rb' filters red and blue. Components are not guaranteed game entities.
- `crop(r0, c0, r1, c1, frame=None)` returns a letter-coded rectangle, with the
  bottom/right bounds EXCLUDED. Maximum 256 cells; use for a specific local area.
- `inspect_transition(index=-1)` returns action, before/after level and step,
  plus the recorded result and no_op. None means unavailable, not false.
  This inspects actual transitions, not refused action calls; use
  last_action_call_result for the latter. `transitions[i].level` does not exist.
Use these helpers instead of rebuilding their functionality. For example:
`print(inspect_objects(colors='Rb')); print(inspect_transition())`.
They are available afresh in every Python call and see updated state after action().
Ordinary variables still reset between calls. File access and imports such as
pickle and time remain unavailable. Use .get(key) for optional result fields.
"""


HELPERS = '''
def inspect_objects(colors=None, min_pixels=1, frame=None):
    if frame is None:
        frame = runtime_globals.get("current_frame")
    if frame is None:
        return []
    selected = None if colors is None else set(colors)
    answer = []
    for node in frame.segmentation.get("nodes", []):
        if node.get("pixels", 0) < min_pixels:
            continue
        if selected is not None and node.get("color") not in selected:
            continue
        boundary = node.get("boundary", [])
        bbox = ([min(p[0] for p in boundary), min(p[1] for p in boundary),
                 max(p[0] for p in boundary), max(p[1] for p in boundary)]
                if boundary else None)
        answer.append({"id": node.get("id"), "color": node.get("color"),
                       "pixels": node.get("pixels"), "bbox": bbox,
                       "rotation": node.get("rotation"), "hash": node.get("hash"),
                       "children": list(node.get("children", []))})
    return answer

def crop(r0, c0, r1, c1, frame=None):
    if frame is None:
        frame = runtime_globals.get("current_frame")
    if frame is None:
        return ""
    rows, cols = frame.shape
    if not (0 <= r0 < r1 <= rows and 0 <= c0 < c1 <= cols):
        raise ValueError("crop bounds must be within frame.shape; end bounds are excluded")
    if (r1-r0)*(c1-c0) > 256:
        raise ValueError("crop is limited to 256 cells; select a smaller region")
    lines = frame.ascii.splitlines()
    return "\\n".join(line[c0:c1] for line in lines[r0:r1])

def inspect_transition(index=-1):
    transitions = runtime_globals.get("transitions", [])
    if not transitions or not -len(transitions) <= index < len(transitions):
        return None
    transition = transitions[index]
    before, after = transition.before_frame, transition.after_frame
    result = dict(transition.result)
    no_op = result.get("no_op")
    if no_op is None and result.get("gameplay_changed") is not None:
        no_op = not result["gameplay_changed"]
    return {"action": transition.action,
            "before_level": before.level if before is not None else None,
            "after_level": after.level if after is not None else None,
            "before_step": before.step if before is not None else None,
            "after_step": after.step if after is not None else None,
            "no_op": no_op, "result": result}

runtime_globals["inspect_objects"] = inspect_objects
runtime_globals["crop"] = crop
runtime_globals["inspect_transition"] = inspect_transition
'''


def patch_sandbox(source: str) -> str:
    anchor = '        def _refresh_state(state_payload):\n'
    if source.count(anchor) != 1:
        raise ValueError("Expected one sandbox state-refresh anchor")
    source = source.replace(anchor, textwrap.indent(HELPERS, "        ") + "\n" + anchor)
    ast.parse(source)
    return source


def patch_agent(source: str) -> str:
    anchor = "    if _level_transfer_guidance_enabled():\n        prompt = apply_level_transfer_system_guidance(prompt)\n    return prompt\n"
    if source.count(anchor) != 1:
        raise ValueError("Expected one system-prompt return anchor")
    source = source.replace(anchor, anchor.replace("    return prompt\n", f"    prompt += {GUIDE!r}\n    return prompt\n"))
    ast.parse(source)
    return source


def install(bundle):
    from pathlib import Path
    agent = Path(bundle) / "src/ARC3-Inference/inference/agent"
    for name, transform in [("python_tool_sandbox.py", patch_sandbox), ("tool_agent.py", patch_agent)]:
        path = agent / name
        path.write_text(transform(path.read_text(encoding="utf8")), encoding="utf8")
