# Master's Thesis: Building Code Cities using the Language Server Protocol

This is the $\LaTeX$ code for my master's thesis. Its style is based mainly on [cleanthesis](https://github.com/derric/cleanthesis), but it adds some stylistic changes.

## Building

> [!NOTE]
> There are (at least) two reasons why following the instructions below wouldn't work:
>
> 1. The full results from the user study aren't publicly available.[^1]
> 2. My fork of tikzviolinplots isn't locally available.[^2]

To build it, you'll first need to run the analysis script, which needs the results from the user study[^1] to exist in the same directory:

```sh
cd analysis
uv run python3 analyze.py
cd ..
```

Then, do the same for the benchmarks (whose data _has_ been included):

```sh
cd benchmark
uv run python3 benchmark.py
cd ..
```

And finally, build the master's thesis itself (parallelization here really helps speed up the TikZ compilations):

```
make -j $(nproc)
```

[^1]: These results have not been included here for privacy reasons. Anonymized results are available at `digital/Eval-*.xlsx`, but those won't immediately work due to the redacted fields, so you'd need to fill in some dummy data first (or modify the scripts).

[^2]: To make the violin plots more readable, I added jittering functionality to tikzviolinplots in [this PR](https://github.com/pedro-callil/tikzviolinplots/pull/3). This has been merged by now, but it's not released as part of the package. My thesis still assumes a local version is available, so you need to clone the tikzviolinplots repository and put it in `../tikzviolinplots/` relative to the thesis.

## Folder Structure

We have the following directories:

- `analysis`: Contains scripts and data related to the analysis of the user study.
- `benchmark`: Contains scripts and data related to the technical evaluation.
- `content`: Contains the actual $\LaTeX$ content of the individual chapters.
- `digital`: Contains the contents of the digital appendix.
- `exposé`: Contains the source and PDF of the original Exposé.
- `figures`: Contains all figures for the thesis, including individual TikZ drawings.
