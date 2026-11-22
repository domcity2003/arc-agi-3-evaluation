"""Play the 25 public ARC-AGI-3 games offline and print a score.

This is a local practice harness. It runs on a laptop, no GPU,
no internet. Swap RandomAgent for a real agent to compare approaches.

Usage:
    .venv/bin/python -m src.local_eval                 # all 25 games, 200 actions each
    .venv/bin/python -m src.local_eval --games ls20 --max-actions 500
"""

import argparse
import logging
import random
import time

import arc_agi
from arcengine import GameAction, GameState

logging.disable(logging.INFO)  # hide per-game load messages

ENV_DIR = "data/environment_files"


class RandomAgent:
    """Baseline: picks a random valid action. Anything we build must beat this."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def choose_action(self, frame):
        actions = [GameAction.from_id(a) for a in frame.available_actions if a != 0]
        action = self.rng.choice(actions)
        data = None
        if action.is_complex():  # ACTION6 = click at (x, y)
            data = {"x": self.rng.randrange(64), "y": self.rng.randrange(64)}
        return action, data


def play(arcade, game_id, agent, max_actions, scorecard_id):
    env = arcade.make(game_id, scorecard_id=scorecard_id)
    frame = env.reset()
    for _ in range(max_actions):
        if frame.state == GameState.WIN:
            break
        if frame.state == GameState.GAME_OVER:
            frame = env.step(GameAction.RESET)
            continue
        action, data = agent.choose_action(frame)
        frame = env.step(action, data=data)
    return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", nargs="*", help="game prefixes, e.g. ls20 ft09 (default: all)")
    parser.add_argument("--max-actions", type=int, default=200)
    args = parser.parse_args()

    arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=ENV_DIR)
    games = [e for e in arcade.available_environments
             if not args.games or e.game_id.split("-")[0] in args.games]
    scorecard_id = arcade.open_scorecard()
    agent = RandomAgent()

    start = time.time()
    for info in games:
        frame = play(arcade, info.game_id, agent, args.max_actions, scorecard_id)
        print(f"{info.game_id:16s} levels={frame.levels_completed}/{len(info.baseline_actions or [])} "
              f"state={frame.state.name}")

    card = arcade.close_scorecard(scorecard_id)
    score = getattr(card, "score", None)
    print(f"\n{len(games)} games in {time.time() - start:.0f}s — scorecard score: {score}")


if __name__ == "__main__":
    main()
