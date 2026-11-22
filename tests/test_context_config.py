"""Exercise context settings against the actual bundled ToolAgent."""
import os

import pytest
import inference.agent.tool_agent as ta

from src.context_config import configure_context


@pytest.mark.parametrize('context_tokens', [16384, 32768])
def test_context_survives_setup_and_already_imported_module(monkeypatch, context_tokens):
    # Setup restores 32768 and the module caches it at import. An env-only
    # change after that point does not change the real constructor's budget.
    monkeypatch.setenv('LOCAL_ANALYZER_CONTEXT_WINDOW', '32768')
    monkeypatch.setattr(ta, '_LOCAL_ANALYZER_CONTEXT_WINDOW', 32768)
    monkeypatch.setattr(ta, '_LOCAL_ANALYZER_MAX_OUTPUT', 0)
    monkeypatch.setattr(ta, '_REQUEST_SAFETY_MARGIN_TOKENS', 6144)
    configure_context(ta, context_tokens)
    agent = ta.ToolAgent(model='context-regression')
    assert agent._context_budget_tokens == context_tokens - 512 - 6144
    assert os.environ['LOCAL_ANALYZER_CONTEXT_WINDOW'] == str(context_tokens)


def test_short_context_drops_old_blocks_but_keeps_current_observation(monkeypatch):
    monkeypatch.setenv('LOCAL_ANALYZER_CONTEXT_WINDOW', '32768')
    monkeypatch.setattr(ta, '_LOCAL_ANALYZER_CONTEXT_WINDOW', 32768)
    monkeypatch.setattr(ta, '_LOCAL_ANALYZER_MAX_OUTPUT', 0)
    monkeypatch.setattr(ta, '_REQUEST_SAFETY_MARGIN_TOKENS', 6144)
    configure_context(ta, 16384)
    agent = ta.ToolAgent(model='context-regression')
    messages = [{'role': 'system', 'content': 'Game instructions'}]
    for i in range(12):
        messages += [
            {'role': 'user', 'content': f'Old observation {i}: ' + 'tile ' * 1100},
            {'role': 'assistant', 'content': f'Hypothesis {i}'},
        ]
    messages.append({'role': 'user', 'content': 'Current observation: level 3'})
    trimmed = agent._trim_messages_for_context(messages)
    assert trimmed[0] == messages[0]
    assert trimmed[-1] == messages[-1]
    assert agent._estimate_request_input_tokens(trimmed) <= 9728
