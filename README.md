[EXPERIMENT] Early prediction experiment
========================================

**Support calls do not reveal the specific cause early. I got 14% on 51 calls and 2% on 48 harder ones, against a 60% bar. I killed the speculative copilot idea.**

The product idea was an AI copilot that listens to a support call and starts solving the problem before the human agent does: a realtime speculative assistant. The entire idea rests on one assumption: that support calls reveal the _specific root cause_ early enough to act on. Instead of building the copilot, I built a cheap, blind test of that assumption.

This repo is that test. I started with transcripts; I would only have moved into voice if the result supported it.

The answer was **no**.

What I built and ran
--------------------

For the first run (n=51) and the harder rerun (n=48), the pass bar was **60%**: predict the specific root cause from the opening of the call, blind. The test was not about the broad _category_ of the call. It asked for the specific cause a support person would need before an early copilot could be useful.

I first ran it on 51 synthetic B2B support-call transcripts, then on 48 harder transcripts written by a stronger model. I scored every prediction blind. The LLM saw the first six turns of each transcript and had to name the specific root cause.

Result on the harder set: **2% on 48 calls.**

I checked it a few ways and it held up:

1. First, I ran it on 51 transcripts written by a weaker model and got 14%. Then I used 48 transcripts written by a stronger model and it dropped to 2%. The early signal was
   just the weak model making it obvious in the script.
2. I swept the window to find where prediction actually gets reliable. It
   crosses the 60% bar around turn 12–13 on the first 51 calls—well into the transcript, not the opening.
3. Migration calls looked predictable around turn 10 in the first set. That result vanished in the harder set: 0% on 16 migration calls. It was a feature of the synthetic scripts, not a reliable signal.
4. Given the whole transcript, it got 92% right on all 48 harder calls. The pipeline could find the cause when the evidence existed; the opening did not contain it.


Why I trust the result
-----------------------

Used a Dual model pipeline for this: 

- GPT writes the calls (each with a hidden answer key).
- Claude reads the call and makes the prediction — it never sees the answer.
- GPT compares the prediction to the answer key.

The predictor and the judge are never the same model. A boundary test enforces
that the predictor can't read the answer key. There's also a leakage check that
flags calls where the customer accidentally says the answer too early, so I can
report the clean calls separately.


What would probably help pivot this
----------------
1. Actual product evidence. I do not have access to it.
2. Real support calls, as transcripts or voice. These tests use synthetic calls from a tool I built: [support-call-generator](https://github.com/gititya/support-call-generator).


The harness that made this possible
----------------

| Module                   | What it is                                                                                                                                                                    |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `loader.py`              | Resolves the generator's export dir; loads transcripts, `ground_truth`, leakage reports, manifest. Defines the 3 scenario categories.                                         |
| `windows.py`             | The "how much of the call does the model see" abstraction. `early_window` = first N turns (the gate's 6-turn proxy); `full_window` = whole call. `render_turns` formats them. |
| `annotator.py`           | The **blind predictor**. System prompt = "you read only an early fragment, you have NOT seen the rest, any answer key, or hidden notes." This is Claude.                      |
| `scorer.py`              | The **judge**. Strict GPT prompt: "only call it a match if the prediction captures the same operational root cause." Compares prediction vs hidden key.                       |
| `metrics.py`             | Aggregation + `GATE_THRESHOLD = 0.60`. Excludes leakage=FAIL calls from the gate set; computes early vs full accuracy.                                                        |
| `report.py`              | Writes `scores.csv` + `summary.md` artifacts.                                                                                                                                 |
| `cli.py`                 | `python -m voice_eval run` → predict → score → report into `runs/latest`.                                                                                                     |
| `llmio.py`               | Tolerant JSON parser for model output (strips markdown fences etc.).                                                                                                          |
| `tests/test_boundary.py` | **The integrity guarantee** — proves the predictor can't reach the answer key.                                                                                                |
| `tests/test_scorer.py`   | Tests the judge logic.                                                                                                                                                        |


How to run
----------

    export OPENAI_API_KEY="..."      # the judge
    export ANTHROPIC_API_KEY="..."   # the predictor
    python -m voice_eval run         # predict -> score -> report into runs/latest
    pytest -q                        # boundary + scorer tests

Config is via env vars (`VE_EARLY_TURNS`, `VE_ANNOTATOR_MODEL`,
`VE_JUDGE_MODEL`, `VE_EXPORTS_DIR`). See `.env.example`.

Files
-----

    voice_eval/          — loader, windows, annotator, scorer, metrics, report, cli
    curve.py             — sweeps the window size to find where prediction works
    escalation_probe.py  — can it predict an escalation early? (no)
    postcall_probe.py    — the post-call summary fallback probe
    tests/                — boundary test + scorer test

Results
-------

    Calls written by        | Predict from first 6 turns | Given the whole call
    weaker model (n=51)     | 14% (n=51)                 | 92% (n=51)
    stronger model (n=48)   | 2% (n=48)                  | 92% (n=48)
