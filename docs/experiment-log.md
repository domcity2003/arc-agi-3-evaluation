# Experiment log

Each row is one variant of the agent. "Practice" is a full or partial run of the 25 public games on the same hardware; "held-out" is the score on the hidden games. Practice runs are noisy and use a shorter, narrower resource budget than the held-out run, so a practice gain is a reason to look closer, not a result.

## First stack (own configuration)

| version | change | practice | held-out | outcome |
|---|---|---|---|---|
| baseline | stock harness, default settings | 6.41 | 2.85 | reference |
| v2 | first prompt and budget changes | 4.44 | 2.70 | worse |
| v3 | patched level-transition notes, ACTION7 mapping | 10.45 | 4.87 | kept; both fixes came from a trace audit |
| v4 | per-game runtime allocation (`runtime_budget.py`) | 12.35 | 2.69 | practice did not predict the held-out result |
| v5 | 16K vs 32K effective context (`context_config.py`) | 0.99 vs 8.68 | 2.82 (32K control) | 16K rejected |

## Published serving and harness configuration

Moving to the openly published configuration (larger context, prefix-cache-aware scheduling, animation and difference images, retained Python functions) changed the held-out score by more than every later change combined.

| version | change | practice | held-out | outcome |
|---|---|---|---|---|
| v6 | published configuration, reproduced | 39.36 (10 games, not comparable) | 27.69 | new reference |
| v7 | shorter continuation after a yield (`state_only`) | 22.26 vs 18.00 (two runs per arm) | 28.22; repeats 25.76, 27.94, 25.38 | mean of four exact repeats 26.83; effect not distinguishable from v6 |
| v8 | neutral continuation wording | rejected in first pass | 27.86 | no gain |
| v9 | yield after 1,024 tokens instead of 2,048 | readiness run only | 27.01 | no gain |
| v10 | slot priority scheduling | readiness run only | 25.54 | no gain |
| v11 | expose RESET to the model | readiness run only | 24.08 | no gain |
| v12 | one fresh review on stalled levels (`stagnation_recovery.py`) | 22.25 vs 25.67 | not run | rejected |
| v13 | yield after 4,096 tokens | 20.45 vs 18.04, driven by one game | 20.74 | rejected |
| v14 | observation helpers (`observation_tools.py`) | 45.17 vs 41.48 (120 min), 22.17 vs 20.36 (50 min) | 26.18 | gain concentrated in one game; inside the v7 range |
| v16 | repaired two helper interface errors found in v14 traces | 62 levels, same as parent and control | not run | tracebacks fell from 111 to 77 with no change in levels |
| v15 | explicit per-game memory (`python_memory.py`) | local checks only | not run | never paired against its control |
| v18 | repair of a zero-score infrastructure failure | 19.40 on a 5-minute readiness run | n/a | startup and output checks only |

## Reading the table

- Four exact repeats of v7 span 25.38 to 28.22. Any held-out difference under about 3 points is inside that range.
- v4 and v5 show practice moving in the opposite direction to the held-out score. Practice runs 25 games for 50 minutes; the held-out run allows roughly 110 games and about 9 hours, so the nominal compute per game differs by a factor of about 2.4.
- Readiness runs (5 minutes) confirm the notebook starts and writes output. In the saved v10 and v11 readiness artifacts, 15 of 25 games had no recorded action, so they say nothing about solving quality.
