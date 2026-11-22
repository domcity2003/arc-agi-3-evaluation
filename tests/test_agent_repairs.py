from pathlib import Path

from arcengine import GameAction
import pytest

from inference.agent.tool_agent import ToolAgent
from inference.framework.solver import _HarnessGameSession


@pytest.fixture
def agent(tmp_path):
    result = ToolAgent(model="audit-model")
    result._ensure_session(tmp_path / "game-one" / "state.json")
    result._update_summarized_knowledge_from_assistant(
        "World model: Buttons rotate adjacent tiles.\n"
        "Goal model: Connect the two endpoints.\n"
        "Action model: A click rotates clockwise.\n"
        "Plan: Click row 10 column 12 next.\n"
        "Recent findings: Player is at row 7."
    )
    return result


def transition(agent, **overrides):
    agent._last_step_summary = {
        "level_transition": True, "run_complete": False, "game_over": False,
        "level": 2, "executed_count": 1, **overrides,
    }
    agent._update_summarized_knowledge_from_step_summary()


def test_completed_level_keeps_learned_rules_but_discards_old_plan(agent):
    # Deleting all learned rules at a level transition causes this regression.
    transition(agent)
    notes = "\n".join(agent._summarized_knowledge_lines())
    assert "Buttons rotate adjacent tiles" in notes
    assert "A click rotates clockwise" in notes
    assert "Connect the two endpoints" in notes
    assert "Click row 10 column 12 next" not in notes
    assert "Player is at row 7" not in notes
    assert "hypothes" in notes.lower()


def test_retry_keeps_rules_but_discards_position_specific_plan(agent):
    transition(agent, level_transition=False, game_over=True, level=1)
    notes = "\n".join(agent._summarized_knowledge_lines())
    assert "Buttons rotate adjacent tiles" in notes
    assert "Click row 10 column 12 next" not in notes


def test_new_game_cannot_receive_previous_game_notes(agent, tmp_path):
    transition(agent)
    agent._ensure_session(tmp_path / "game-two" / "state.json")
    assert not agent._summarized_knowledge_lines()


def test_repeated_transition_does_not_erase_or_duplicate_saved_rules(agent):
    transition(agent)
    before = agent._summarized_knowledge_lines()
    transition(agent)
    assert agent._summarized_knowledge_lines() == before
    assert "Buttons rotate adjacent tiles" in "\n".join(before)


def test_cross_level_memory_has_a_bounded_prompt_cost(agent):
    agent._summarized_knowledge["world_model"] = "mechanic " * 3000
    agent._summarized_knowledge["action_model"] = "control " * 3000
    transition(agent)
    notes = "\n".join(agent._summarized_knowledge_lines())
    assert "mechanic" in notes and "control" in notes
    assert len(notes) < 2400


def test_undo_action_reaches_the_engine_action_parser():
    # The old map advertised ACTION7 but rejected it before the game saw it.
    session = object.__new__(_HarnessGameSession)
    actions, error = session._normalize_actions({"actions": [{"action": "ACTION7"}]})
    assert error is None
    assert len(actions) == 1
    assert actions[0].id == GameAction.ACTION7


def test_unknown_action_still_rejected():
    session = object.__new__(_HarnessGameSession)
    actions, error = session._normalize_actions({"actions": [{"action": "BOGUS"}]})
    assert actions is None
    assert "Unknown action" in error
