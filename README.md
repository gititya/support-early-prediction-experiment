[EXPERIMENT] Real-Time Support Copilot
==============================

I wanted to build an AI copilot that listens to a support call and starts
solving the problem before the human agent does. Before building any of it,
I tested the one thing the whole idea depends on: can an AI hear the first
minute of a call and predict what's actually wrong?

This repo is that test. I built the first version using the transcripts of support call, and if the results were satisfactory, move into voice. 

The answer was no.

What I built and ran
--------------------

The pass bar was simple: predict the specific root cause from the opening of
the call, blind, on at least 60% of calls. The idea wasn't to get the theme, like "this is a permissions problem" right, it was to to find the specific cause, because that's what human agent would need early for the copilot to be worth anything. 

I ran it on 48 synthetic B2B support call transcripts and scored every prediction blind. For this, I gave the LLM the first 6 turns of each transcript (the "first 60-90 seconds") and asked it to name the specific root cause; not the topic or the theme, but the actual root cause. 

Result: **2%.**

I checked it a few ways and it held up:

1. First, I ran it on transcripts written by a weaker model — got 14%. Then I rewrote
   the transcripts with a stronger model and it dropped to 2%. The early signal was
   just the weak model making it obvious in the script.
2. I swept the window to find where prediction actually gets reliable. It
   crosses 60% around turn 12-13 — well into the transcript, not the opening.
3. The one bright spot (use case with "migration related" looked predictable around turn 10)
   vanished with the stronger model: 0% early. It was never real.
4. I gave it the entire transcript and it got 92% right; so the AI pipeline is fine, just that the information isn't there early enough. 


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
1. Actual (and live) product telemetry into the copilot; I don't have access to that right now.
2. Real support calls - transcripts or voice. These are "synthetic" support call transcripts that were generated from a tool I built:  [support-call-generator](https://github.com/gititya/support-call-generator). It _could_ work with production grade support calls. 

How to run
----------

    source .venv/bin/activate
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
    FINDINGS_phase1.md    — the full writeup, every number and how I got it
    tests/                — boundary test + scorer test

Results
-------

    Calls written by        | Predict from first 6 turns | Given the whole call
    weaker model (n=51)     | 14%                        | 92%
    stronger model (n=48)   | 2%                         | 92%

