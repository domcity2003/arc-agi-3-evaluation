"""Compare completed public-game evaluations and their request timings.

Usage: python scripts/compare_evaluations.py CANDIDATE_DIR CONTROL_DIR
One paired run does not estimate run-to-run uncertainty or hidden-game scores.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import statistics


def read_run(directory):
    directory = Path(directory)
    score = json.loads((directory / 'score.json').read_text())
    benchmark = json.loads((directory / 'benchmark.json').read_text())
    runs = benchmark['game_runs']
    by_id = {run['game_id']: run for run in runs}
    if len(by_id) != len(runs) or set(by_id) != set(score['games']):
        raise ValueError(f'{directory}: duplicate or mismatched game coverage')
    scores = {key: value['score'] for key, value in score['games'].items()}
    if not scores or not all(math.isfinite(value) for value in scores.values()):
        raise ValueError(f'{directory}: missing or nonfinite scores')
    if not math.isclose(statistics.mean(scores.values()), score['score'], abs_tol=1e-6):
        raise ValueError(f'{directory}: aggregate does not match per-game scores')
    for key, run in by_id.items():
        if run['state'] not in {'gave_up', 'won', 'cancelled'} or run['final_score'] is None:
            raise ValueError(f'{directory}: game {key} not finalized successfully: {run["state"]}')
        if not math.isclose(run['final_score'], scores[key], abs_tol=1e-6):
            raise ValueError(f'{directory}: benchmark/score mismatch for {key}')
    timing = {}
    logs = sorted(p for p in directory.glob('*.log') if p.name not in {'live.log', 'vllm-openai-server.log'})
    if not logs and (directory / 'live.log').exists():
        logs = [directory / 'live.log']
    if logs:
        raw = logs[0].read_text()
        try:
            events = json.loads(raw)
            raw = '\n'.join(event['data'] for event in events)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        records = re.findall(r'AGENTFIX_TIMING chat[^\n]*?dt=([\d.]+)[^\n]*?ptok=(\d+) ctok=(\d+) finish=(\w+)', raw)
        if records:
            timing['requests'] = len(records)
            for i, label in enumerate(['request_seconds', 'input_tokens', 'output_tokens']):
                values = [float(row[i]) for row in records]
                timing[f'median_{label}'] = statistics.median(values)
                timing[f'total_{label}'] = sum(values)
            timing['length_limited_replies'] = sum(row[3] == 'length' for row in records)
    serving = directory / 'vllm-openai-server.log'
    if serving.exists():
        records = re.findall(
            r'Avg prompt throughput: ([\d.]+) tokens/s, Avg generation throughput: ([\d.]+) tokens/s, '
            r'Running: (\d+) reqs, Waiting: (\d+) reqs, GPU KV cache usage: ([\d.]+)%',
            serving.read_text(),
        )
        active = [row for row in records if int(row[2]) > 0]
        if active:
            for i, label in enumerate(['prompt_tokens_per_second', 'output_tokens_per_second',
                                       'running_requests', 'waiting_requests', 'kv_cache_percent']):
                timing[f'mean_server_{label}'] = statistics.mean(float(row[i]) for row in active)
    return {'directory': str(directory), 'score': score['score'], 'game_count': len(scores),
            'states': dict(Counter(run['state'] for run in runs)),
            'median_wallclock_seconds': statistics.median(run['final_wallclock_seconds'] for run in runs),
            'levels': sum(run['levels_completed'] for run in runs),
            'actions': sum(sum(run['actions_per_level']) for run in runs),
            'timing': timing, 'scores': scores,
            'levels_by_game': {key: run['levels_completed'] for key, run in by_id.items()}}


def compare(candidate, control):
    if set(candidate['scores']) != set(control['scores']):
        raise ValueError('Candidate and control contain different games')
    rows = []
    for game in sorted(candidate['scores']):
        rows.append({'game': game, 'candidate': candidate['scores'][game],
                     'control': control['scores'][game],
                     'delta': candidate['scores'][game] - control['scores'][game],
                     'candidate_levels': candidate['levels_by_game'][game],
                     'control_levels': control['levels_by_game'][game]})
    stable = [row for row in rows if row['game'].split('-')[0] not in {'sb26', 'ft09'}]
    largest = max(rows, key=lambda row: abs(row['delta']))
    remaining = [row['delta'] for row in rows if row['game'] != largest['game']]
    return {'candidate': candidate, 'control': control,
            'score_delta': candidate['score'] - control['score'],
            'wins': sum(row['delta'] > 1e-8 for row in rows),
            'losses': sum(row['delta'] < -1e-8 for row in rows),
            'ties': sum(abs(row['delta']) <= 1e-8 for row in rows),
            'excluding_largest_game': {
                'game': largest['game'], 'game_delta': largest['delta'],
                'score_delta': statistics.mean(remaining) if remaining else None},
            'excluding_sb26_ft09': {
                'candidate': statistics.mean(row['candidate'] for row in stable),
                'control': statistics.mean(row['control'] for row in stable)} if stable else None,
            'games': sorted(rows, key=lambda row: row['delta'], reverse=True)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate')
    parser.add_argument('control')
    args = parser.parse_args()
    print(json.dumps(compare(read_run(args.candidate), read_run(args.control)), indent=2))
