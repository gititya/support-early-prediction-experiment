[EXPERIMENT] Real-Time Support
==============================

I wanted to build an AI copilot that listens to a support call and starts
solving the problem before the human agent does. Before building any of it,
I tested the one thing the whole idea depends on: can an AI hear the first
minute of a call and predict what's actually wrong?

This repo is that test. The answer was no.

The one finding
---------------

Support calls don't tell you what's wrong early enough to predict the fix.

I gave the AI the first 6 turns of each call (the "first 60-90 seconds") and
asked it to name the specific root cause — not the topic, the actual mechanism
(a SCIM sync delay, a stale entitlement cache, a missing write scope). It got
2% right.

Give it the whole call and it gets 92% right. So the AI is fine. The
information just isn't there early. By the time the cause is clear, the call
is mostly over and there's nothing left to predict.

That gap is the result. It killed the product before I built it.

What I built and ran
--------------------

The pass bar was simple: predict the specific root cause from the opening of
the call, blind, on at least 60% of calls. Topic doesn't count — anyone can
tell "this is a permissions problem" from turn one. The bet was on the
specific cause, because that's what an agent would need early for the copilot
to be worth anything.

I ran it on 48 synthetic B2B support calls and scored every prediction blind.

Result: 2%.

I checked it three ways and it held up:

1. First I ran it on calls written by a weaker model — got 14%. Then I rewrote
   the calls with a stronger model and it dropped to 2%. The early signal was
   just the weak model leaving tells in the script.
2. I swept the window to find where prediction actually gets reliable. It
   crosses 60% around turn 12-13 — well into the call, not the opening.
3. The one bright spot (migration calls looked predictable around turn 10)
   vanished with the stronger model: 0% early. It was never real.

Why I trust the result
-----------------------

The easy way to fool yourself here is to let one model grade its own homework.
So nobody plays two roles:

- GPT writes the calls (each with a hidden answer key).
- Claude reads the call and makes the prediction — it never sees the answer.
- GPT compares the prediction to the answer key.

The predictor and the judge are never the same model. A boundary test enforces
that the predictor can't read the answer key. There's also a leakage check that
flags calls where the customer accidentally says the answer too early, so I can
report the clean calls separately.

What this is not
----------------

1. NOT a working copilot. It's the experiment that decided I shouldn't build
   one yet.
2. NOT the call generator. The calls come from a separate repo
   (gititya/support-call-generator). This repo only reads its output.
3. NOT real calls. Everything is synthetic. That's exactly why the stronger
   model mattered — and why I won't claim anything until I can run it on real
   transcripts.

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

The takeaway: for ~$10 of API calls, this told me a realtime support copilot
won't work on the thing it was supposed to be good at. The reusable part isn't
the finding — it's the method: a cheap blind test you run before building, to
kill an idea before it costs you months.
