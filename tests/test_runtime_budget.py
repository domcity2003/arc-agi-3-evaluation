"""Guard against starving the final wave or leaving hours unused."""
import pytest
from src.runtime_budget import per_game_budget


def test_55_games_use_the_available_two_waves():
    allowance = per_game_budget(55, 28, 30000)
    assert 14500 <= allowance <= 15000


def test_partial_last_wave_still_gets_time():
    allowance = per_game_budget(57, 28, 30000)
    assert 9500 <= allowance <= 10000


def test_late_setup_cannot_overbook_the_deadline():
    assert 0 < per_game_budget(110, 28, 12000) <= 3000


@pytest.mark.parametrize('args', [(0, 28, 30000), (55, 0, 30000), (55, 28, 0), (55, 28, float('nan'))])
def test_invalid_budget_fails_before_starting_games(args):
    with pytest.raises(ValueError):
        per_game_budget(*args)
