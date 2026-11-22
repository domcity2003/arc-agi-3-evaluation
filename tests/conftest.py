"""Tests that exercise the real harness classes need the upstream agent
checkout on PYTHONPATH (see README, "Running the tests"). Without it, only
the self-contained tests are collected."""
import importlib.util

collect_ignore = []
if importlib.util.find_spec("inference") is None:
    collect_ignore += ["test_agent_repairs.py", "test_context_config.py"]
