"""Configure the Duck analyzer after bundled serving setup."""
import os


def configure_context(tool_agent_module, context_tokens):
    os.environ['LOCAL_ANALYZER_CONTEXT_WINDOW'] = str(context_tokens)
    # ToolAgent reads this module constant, not the environment at construction.
    # Setup may already have imported the module with its 32K default.
    tool_agent_module._LOCAL_ANALYZER_CONTEXT_WINDOW = context_tokens
