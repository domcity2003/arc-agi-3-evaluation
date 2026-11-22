# Evaluation protocol

What I would run before believing that a change helps, written after the experiments in the log.

1. **Freeze a control.** One archived notebook, with its dependency versions and a hash of the embedded harness. Never rebuild the control from a builder script that has since been edited.
2. **Pair by game.** Run candidate and control on the same 25 games and compare per-game differences with `scripts/compare_evaluations.py`. Aggregate means hide which games moved.
3. **Report the aggregate with and without the game whose score changed the most.** If the sign flips, the direction of the result depends on that game. The comparison script reports this under `excluding_largest_game`.
4. **Repeat.** At least three interleaved candidate and control pairs at the full time budget. Two unchanged controls already differed by 7.6 points, so a single pair cannot carry a conclusion.
5. **Match the resource regime.** Practice should use the per-game compute the real run will have, or the result should be labelled as not transferable.
6. **Change one thing.** A bundle of changes cannot be explained afterwards, whichever way it goes.
7. **Check the mechanism on traces.** Count what the change was supposed to reduce (for example rediscovery of a rule the agent already found) in sampled trajectories. A score movement with no mechanism behind it is treated as noise.
8. **Save provenance with every run.** Notebook hash, harness hash, model and runtime versions, server telemetry, and the full per-game record.
9. **Check the score bound before optimising a component.** Recomputing the scoring formula on saved runs showed that perfect action efficiency was worth at most 0.84 points, so work on action counts was the wrong place to spend effort.
