# ARC-AGI-3 evaluation study

I ran the same agent four times on the same held-out games and got 28.22, 25.76, 27.94 and 25.38. The spread across identical runs (a range of 2.84 points, standard deviation 1.46) was larger than the effect of almost every change I tested. Most of this repository is the tooling I built to find that out, and the patches that survived it.

ARC-AGI-3 is an interactive reasoning benchmark. Each game is a small grid world with no instructions: the agent sees the board, takes actions, and has to work out the rules and the goal from what happens. Score rewards completing levels, weights later levels more heavily, and penalises wasted actions.

## Try the evaluation locally

From the repository root, run this with Python. The example uses three synthetic game records and needs only the standard library.

```bash
python scripts/compare_evaluations.py examples/paired-eval/candidate examples/paired-eval/control
```

The candidate leads by **2 points** overall. Excluding `sample-a`, its largest per-game change, it trails by **3 points** on the other two games. See `score_delta` and `excluding_largest_game` in the output. These are example scores for demonstrating the analysis. The benchmark runs are described below.

## The agent

The agent is an LLM that reasons for a long time, writes Python to inspect the board, and acts. It runs offline: a quantized open-weight Qwen model served locally with SGLang, inside a single notebook on one GPU, with a fixed runtime budget shared across all games. The serving stack and the base game harness are an openly published Apache-2.0 configuration (see `NOTICE`). Everything in `src/` is a patch or add-on on top of that base, written to be applied without reading the base source.

| module | what it changes |
|---|---|
| `agent_repairs.py` | Keeps the model's own notes across level changes (the stock updater cleared them) and maps ACTION7, which the prompt offered but the dispatcher dropped |
| `observation_tools.py`, `observation_tool_repairs.py` | Sandbox helpers (`inspect_objects`, `crop`, `inspect_transition`) and fixes for two interface errors found in saved traces |
| `python_memory.py` | A bounded JSON dictionary the model writes itself and that survives resumes, history trimming and level changes within one game |
| `stagnation_recovery.py` | One context restart per expensive unfinished level, triggered at 49,152 tokens |
| `runtime_budget.py` | Splits the remaining time across waves of concurrent games so late games are not starved |
| `context_config.py` | Sets the effective context after serving setup, because the harness caches its default at import |
| `local_eval.py` | Runs the 25 public games locally with a random agent, as a floor |

`scripts/compare_evaluations.py` pairs two completed 25-game runs by game, checks that every game finished, and reports per-game differences and request timing.

## What I found

**Identical runs differ by more than my improvements did.** Four runs of one frozen notebook averaged 26.83. Two unchanged 50-minute practice controls scored 25.67 and 18.04, a 7.6-point swing, while the candidate I was testing at the time led its control by 2.4. The runs share a solver but not a random stream, so this is an estimate of noise from four and two samples. It is enough to say that a single run cannot rank two variants whose true difference is under a few points.

**Practice gains were usually one game.** In the first paired test of a shorter resume prompt, the candidate led by 5.04 points, and one game (`cd82`) contributed 100 of the 126 summed points behind that gap. Without it the lead was 1.09. Later pairs showed the same shape: one game's gain was larger than the whole aggregate gain, and removing it flipped the sign. After that I reported every comparison with and without its largest game.

**Action efficiency is not where the points are.** I recomputed all 125 game scores from five saved full practice runs from the scoring formula and matched the recorded values to 1e-8. Then I scored the same completed levels with a perfect action count. The gain was 0.11 to 0.84 points. The measured bottleneck is reaching deeper levels, not playing the early ones tighter.

**Real bugs moved the score; prompt tweaks did not.** An audit of saved traces found that the level-transition updater erased the model's world and goal notes at every level change (all 43 observed transitions), and that ACTION7 was advertised but never reached the game engine. The first stack scored 6.4 in practice before the fixes and 10.5 after, though different seeds and budgets mean I cannot attribute the whole change to them. Changing the serving and harness configuration to the published one moved the held-out score from 4.87 to about 27. After that, resume prompts, yield thresholds, scheduling, recovery restarts and observation helpers all landed inside the noise band.

**Provenance has to be recorded.** I decoded the embedded harness from ten frozen notebooks and found the same hash in all ten, which ruled out silent drift as the explanation for score changes. I also found gaps that cannot be recovered afterwards: several early practice artifacts were gone, and token accounting omitted generation after the last action. Runs now need dependency fingerprints and server telemetry saved with them.

The full list of variants, with the evidence for each, is in [`docs/experiment-log.md`](docs/experiment-log.md). The evaluation protocol I settled on is in [`docs/evaluation-protocol.md`](docs/evaluation-protocol.md).

## Running it

```bash
pip install -r requirements.txt
python -m pytest -q
python -m src.local_eval --games ls20 --max-actions 150    # needs the public game files in data/environment_files
```

Ten tests pass on a bare checkout, covering budget allocation and the recovery logic. Two more files (`test_agent_repairs.py`, `test_context_config.py`) exercise the real harness classes and are collected only when the upstream agent checkout is on `PYTHONPATH`. One recovery test is skipped for the same reason.

## Scope of this public edition

This public edition contains the evaluation tools, the study write-up, and selected patches. The full benchmark setup requires the separately distributed base harness, serving stack, model weights, and game files. The synthetic comparison above runs independently.

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
