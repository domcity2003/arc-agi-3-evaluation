"""Allocate the remaining play window without starving queued games."""
import math


def per_game_budget(game_count, concurrency, remaining_seconds):
    if game_count <= 0 or concurrency <= 0:
        raise ValueError('Game count and concurrency must be positive.')
    if not math.isfinite(remaining_seconds) or remaining_seconds <= 0:
        raise ValueError('Remaining play time must be positive and finite.')
    waves = math.ceil(game_count / concurrency)
    window = remaining_seconds / waves
    # Leave up to a minute per wave for worker cleanup / queue handoff.
    # The notebook has already excluded its separate 600-second exit reserve.
    return window - min(60.0, window * 0.02)
