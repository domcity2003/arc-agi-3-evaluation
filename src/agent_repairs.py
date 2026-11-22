"""Small, game-independent repairs applied after the upstream v3 patches.

Only the model's own visible notes are retained. No game identifiers, hidden
state, source code, or prerecorded solutions enter the agent's decisions.
"""


def install_agent_repairs(tool_agent_module, action_names_module):
    agent_class = tool_agent_module.ToolAgent
    if getattr(agent_class, "_arc_audit_repairs", False):
        return {"level_memory": True, "action7_mapping": True}

    original_update = agent_class._update_summarized_knowledge_from_step_summary
    original_lines = agent_class._summarized_knowledge_lines
    saved_key = "previous_level_hypotheses"
    fields = (("world_model", "World"), ("action_model", "Actions"), ("goal_model", "Goal"))

    def update_knowledge(self):
        summary = self._last_step_summary or {}
        knowledge = self._summarized_knowledge
        if summary.get("run_complete"):
            original_update(self)
            knowledge.pop(saved_key, None)
            return
        if summary.get("level_transition") or summary.get("game_over"):
            # Keep a bounded snapshot of the model's hypotheses, explicitly
            # separate from its current-scene notes. They may include stale
            # coordinates, so the prompt requires verification on the new board.
            parts = []
            for key, label in fields:
                value = " ".join(str(knowledge.get(key) or "").split())
                if value:
                    if len(value) > 600:
                        value = value[:597] + "..."
                    parts.append(f"{label}: {value}")
            if parts:
                knowledge[saved_key] = "\n".join(parts)
            original_update(self)
            for key in ("world_model", "action_model", "goal_model", "current_plan",
                        "recent_findings", "open_questions"):
                knowledge[key] = ""
        else:
            original_update(self)

    def knowledge_lines(self):
        lines = original_lines(self)
        previous = self._summarized_knowledge.get(saved_key)
        if previous:
            lines.extend([
                "Hypotheses retained from before the last level change or reset:",
                previous,
                "Check these against the current board. Reuse only confirmed mechanics; "
                "recompute positions, objects, and the move plan for this scene.",
            ])
        return lines

    agent_class._update_summarized_knowledge_from_step_summary = update_knowledge
    agent_class._summarized_knowledge_lines = knowledge_lines
    # Existing functions consult these dictionaries at call time. The game
    # session still enforces the environment's available_actions list.
    action_names_module.ENGINE_TO_MODEL_ACTION["ACTION7"] = "ACTION7"
    action_names_module.MODEL_TO_ENGINE_ACTION["ACTION7"] = "ACTION7"
    agent_class._arc_audit_repairs = True
    return {"level_memory": True, "action7_mapping": True}
