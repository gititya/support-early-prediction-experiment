# VoiceAgent Architecture Note

This note maps the LTS-VoiceAgent paper onto the support-call copilot MVP in `PRD_1st.md`, after a full-source adversarial review against:

- `PRD_1st.md`
- `initial_research/first_proposal.md`
- `initial_research/MARS-adverserial.md`
- `initial_research/LTS-VoiceAgent- A Listen-Think-Speak Framework for Efficient Streaming Voice Interaction via Semantic Triggering and Incremental Reasoning.pdf`
- the extractable arXiv HTML/text version of the same paper

## Architecture Decision

Use LTS-VoiceAgent as inspiration, not as a blueprint.

The paper solves a customer-facing voice-agent latency problem: how to answer quickly when the user stops speaking. This product is different. The support-call copilot is not in the customer turn-taking loop. It sits beside a human agent, tracks operational state, and surfaces sparse nudges.

What transfers:

- semantic gating of expensive reasoning calls
- compact reusable state instead of repeated transcript summarization
- correction-aware state updates
- pause-and-repair evaluation
- efficiency metrics for avoided reasoning calls and avoided interruptions

What does not transfer:

- customer-facing speech generation
- Answer-First response generation
- a literal Thinker/Speaker dual-LLM orchestrator
- millisecond-level TTFS goals
- GSM8K/MMLU-style spoken reasoning benchmarks
- learned semantic-trigger training as a first prototype requirement

The first prototype should be a validation-led support-state tracker, not a voice-agent clone.

## What To Borrow

### Semantic Gating

The paper's useful trigger idea is not "look for keywords." It is: call expensive reasoning only when the stream contains a meaningful information increment.

For this product, semantic gating means the slow state updater should run when the conversation adds support-relevant information:

- new symptom
- affected scope
- account, workspace, role, user, plan, or billing entity
- recent operational change such as migration, invite, role change, workspace switch, or plan change
- troubleshooting instruction
- customer-reported outcome of a troubleshooting step
- correction such as "actually", "wait", or "not that account"
- escalation marker
- workaround acceptance while a blocker remains unresolved
- unresolved objection

Fast keyword rules can detect candidate events. They are not the semantic trigger by themselves.

### Compact State Reuse

Keep a structured Live Interaction State and pass it into every reasoning call. Do not repeatedly ask the model to summarize the whole call.

The state should preserve:

- active facts
- superseded facts
- unknowns
- attempted steps and outcomes
- ranked hypotheses
- evidence for and against hypotheses
- current investigation status
- nudge history
- state version history

### Correction-Aware Updates

Support calls contain repairs:

> "Three users lost access after the migration. Wait, actually it might be the whole workspace."

The state must not keep both scopes as equally active facts. It should mark the first scope as superseded by the correction and preserve both in history.

### Pause-And-Repair Evaluation

The validation set must include:

- hesitations
- interrupted explanations
- self-corrections
- late scope changes
- repeated failed steps
- ambiguous customer language
- ASR-like transcript noise
- speaker-overlap cases once live audio is tested

### Efficiency Metrics

Replace the paper's NFE/NIT metrics with support-copilot equivalents:

- slow reasoner calls per call
- suppressed candidate-trigger count
- stale patch rejection count
- nudge count
- nudge retraction count
- hypothesis flip count
- time from triggering utterance to visible nudge

## What To Reject

Reject customer-facing voice behavior.

The MVP should not include TTS, voice response, autonomous support, or Answer-First customer replies.

Reject a literal Thinker/Speaker mapping.

In the paper, the Speaker is a foreground LLM that speculatively generates a user-facing answer. In this product, the foreground path should not become a speculative answer generator. The closest analog is the nudge queue, but that is product-specific and should not be described as the same mechanism.

Reject keyword rules as semantic triggering.

Keyword rules are useful for event capture. They are too brittle to be treated as semantic completeness detection.

Reject uncalibrated confidence math.

Do not build product behavior around fake precision such as `0.70` confidence or `0.15` margin unless the values are calibrated against labeled replay data. Until then, use ranked hypotheses plus evidence dominance.

Reject five self-authored scripts as validation.

Five scripts are enough to test plumbing. They are not enough to validate the product premise.

## Validation Gate Before Prototype Expansion

The PRD's validation-first discipline remains the controlling plan.

Before treating realtime architecture as product-valid, create 30-50 realistic support interactions in the narrow permissions/access/workspace setup domain.

Validation requirements:

- separate scenario authorship and scoring as much as possible
- blind-score from transcript/audio where possible
- include at least 5-10 out-of-distribution or more realistic calls if available
- annotate final issue category
- annotate earliest point where issue category became identifiable
- annotate earliest useful next diagnostic question
- annotate escalation markers
- annotate emotional or trust signals only when directly evidenced
- annotate troubleshooting steps and outcomes

Gate:

- If early issue prediction from the first 60-90 seconds is below roughly 60 percent on realistic/blind-scored calls, narrow the domain before building a live copilot.
- If useful next diagnostic questions are not identifiable before the agent naturally asks them, the live nudge premise is weak.

The first 5 scripted replays are engineering fixtures only. They do not replace this validation gate.

## First Prototype Architecture

Start with a replay-based pipeline that proves state tracking and event handling before live STT.

```text
Scripted/replayed transcript
        |
        v
Utterance replay adapter
        |
        v
Diarized utterance event
        |
        v
ASR/speaker quality checks
        |
        v
Candidate event detector
        |
        v
Semantic batcher
        |
        v
Slow state updater
        |
        v
Versioned state reconciler
        |
        v
Nudge gate + retraction logic
        |
        +------------------+
        |                  |
        v                  v
Live copilot panel   Post-call record
```

The first prototype has one LLM state updater, not a paper-style dual-LLM orchestrator. Add a separate fast speculative path only if validation shows the slow updater cannot meet useful timing.

## Runtime Objects

### Utterance

```json
{
  "id": "utt_042",
  "call_id": "call_001",
  "sequence": 42,
  "speaker": "customer",
  "speaker_confidence": 0.82,
  "start_ms": 84200,
  "end_ms": 88400,
  "text": "Three users lost access after the migration, wait, actually it might be the whole workspace.",
  "is_final": true,
  "asr_confidence": 0.91
}
```

### Event

```json
{
  "id": "evt_089",
  "utterance_id": "utt_042",
  "sequence": 89,
  "type": "scope_correction",
  "actor": "customer",
  "value": {
    "old_scope": "three users",
    "new_scope": "whole workspace"
  },
  "source": "candidate_rule",
  "needs_slow_validation": true,
  "created_ms": 88700
}
```

Initial event types:

- `customer_symptom`
- `affected_scope`
- `recent_change`
- `entity_mention`
- `agent_question`
- `troubleshooting_instruction`
- `step_outcome`
- `scope_correction`
- `repeated_failure_candidate`
- `repeated_loop_candidate`
- `escalation_marker`
- `policy_or_billing_constraint`
- `workaround_acceptance`
- `unresolved_objection`

Repeated loops and repeated failures are candidates at first. Treating two differently worded troubleshooting steps as the same step usually requires semantic matching, not regex.

### Live Interaction State

```json
{
  "call_id": "call_001",
  "state_version": 17,
  "last_event_sequence": 89,
  "updated_ms": 91200,
  "facts": [
    {
      "id": "fact_012",
      "text": "Customer reports access loss after migration.",
      "source_event_ids": ["evt_081"],
      "status": "active"
    },
    {
      "id": "fact_013",
      "text": "Customer initially described scope as three users.",
      "source_event_ids": ["evt_086"],
      "status": "superseded",
      "superseded_by_event_id": "evt_089"
    }
  ],
  "unknowns": [
    "Whether affected users are assigned to the migrated workspace group",
    "Whether admin roles changed during migration"
  ],
  "steps_attempted": [
    {
      "canonical_step": "password reset",
      "utterance_variants": ["reset your password", "try the reset again"],
      "outcome": "failed",
      "source_event_ids": ["evt_071", "evt_074"]
    }
  ],
  "hypotheses": [
    {
      "id": "hyp_004",
      "label": "workspace role inheritance issue",
      "rank": 1,
      "status": "active",
      "display_status": "investigating",
      "evidence_strength": "moderate",
      "supporting_event_ids": ["evt_081", "evt_089"],
      "contradicting_event_ids": [],
      "next_verification_question": "Can you check whether the affected users are assigned to the migrated workspace group?"
    }
  ],
  "resolution_status": "investigating",
  "repeat_contact_risk": "medium",
  "escalation_risk": {
    "level": "low",
    "evidence_event_ids": []
  }
}
```

### State Patch

```json
{
  "patch_id": "patch_014",
  "call_id": "call_001",
  "based_on_state_version": 16,
  "covers_event_sequences": [86, 87, 88, 89],
  "fact_patches": [],
  "hypothesis_patches": [],
  "nudge_candidates": []
}
```

The reconciler must reject or rebase a patch if `based_on_state_version` is stale and the patch conflicts with a newer correction.

### Nudge

```json
{
  "id": "nudge_006",
  "priority": "high",
  "type": "next_question",
  "title": "Verify migrated workspace group",
  "body": "Access loss after migration may be workspace-wide. Ask whether affected users are assigned to the migrated workspace group.",
  "reason": "The customer corrected scope from three users to the whole workspace after mentioning migration.",
  "source_event_ids": ["evt_081", "evt_089"],
  "state_version": 17,
  "expires_ms": 150000,
  "status": "queued"
}
```

Nudges must support retraction:

```json
{
  "id": "retract_002",
  "nudge_id": "nudge_006",
  "reason": "Later customer correction narrowed the affected scope to one invited user.",
  "source_event_ids": ["evt_101"],
  "state_version": 21
}
```

## Exact Event Pipeline

### 1. Transcript Ingestion

Input: finalized transcript utterance from replay or streaming STT.

Prototype shortcut:

- use transcript replay first
- simulate streaming sequence and timestamps
- mark all replay speaker labels as clean test inputs

Live-STT caveat:

- live audio requires explicit handling for ASR confidence, interim text churn, speaker confidence, and speaker overlap
- do not judge live readiness from clean transcript replay latency alone

### 2. ASR And Speaker Quality Checks

Input: utterance.

Action:

- suppress filler-only text
- flag low `asr_confidence`
- flag low `speaker_confidence`
- avoid high-impact event creation when speaker attribution is uncertain
- preserve raw text and cleaned text separately

The paper's Thinker includes input sanitization. The prototype should at least reserve a slot for support-domain cleanup of product names, roles, plans, and account/workspace terms before rules rely on the transcript.

### 3. Candidate Event Detector

Input: latest utterance plus recent state.

Target latency: 0.5-2 seconds for candidate creation.

Rules can create candidate events for:

- explicit correction language
- explicit escalation language
- affected-scope phrases
- recent-change phrases
- policy/billing mentions
- unresolved-objection phrases
- workaround-acceptance phrases

Rules should not directly promote hypotheses.

Rules should not directly show speculative diagnosis nudges.

Only very high-precision urgent awareness nudges may bypass slow validation, for example:

- explicit escalation phrase from the customer
- explicit "we are blocked" severity marker

Everything else goes through the slow state updater and nudge gate.

### 4. Semantic Batcher

Input: candidate event stream plus utterance stream.

Trigger the slow state updater when:

- at least 2 new operational candidate events arrived
- a symptom plus affected scope are present
- a troubleshooting step outcome arrived
- a correction changes a currently active fact
- a repeated-loop or repeated-failure candidate appears
- 10 seconds elapsed and transcript changed materially

Suppress slow updates when:

- only filler/social text changed
- only ASR interim text changed
- event was already processed
- speaker attribution is too uncertain for a high-impact claim

### 5. Slow State Updater

Input:

- current Live Interaction State
- state version
- new event batch
- short transcript window around source utterances
- narrow domain playbook for permissions/access/workspace setup

Target latency:

- 5-10 seconds for state updates
- do not promise 2-4 second speculative hypothesis nudges until measured

Output:

- JSON state patch
- ranked hypotheses
- evidence dominance
- next verification question
- nudge candidates
- retractions if earlier nudges became wrong

Prompt contract:

```text
Given the current state and new events, return JSON only:
1. based_on_state_version
2. covered_event_sequences
3. fact_patches
4. unknown_patches
5. step_patches
6. hypothesis_patches
7. resolution_status_patch
8. nudge_candidates
9. nudge_retractions

Do not summarize the call. Do not produce final answers. Do not infer emotion unless directly evidenced.
Use ranked hypotheses and evidence strength, not calibrated numeric confidence.
```

### 6. Versioned State Reconciler

Input: state patch.

Required behavior:

- apply patches in event-sequence order
- reject duplicate event processing
- reject stale patches that conflict with newer state
- rebase non-conflicting stale patches where safe
- preserve superseded facts
- keep hypothesis transition history
- keep nudge and retraction history

This replaces the paper's in-flight Speaker termination with a simpler correctness guarantee suitable for this product.

### 7. Hypothesis Display Rules

Until confidence is calibrated, avoid numeric thresholds.

Show a leading hypothesis only when:

- it is ranked first
- it has multiple supporting events or one verified support event
- there is no active contradiction
- the next verification question is concrete
- it has remained stable across at least 2 relevant events or one state update after correction

Show `investigating` when:

- top hypotheses are close in evidence
- support is only lexical
- a correction occurred recently
- ASR or speaker confidence is low

### 8. Nudge Gate

Input: nudge candidates and retractions.

Surfacing rule:

A nudge can be shown only if it:

- implies a concrete agent action or awareness shift
- is not already handled by the agent
- is based on active facts/events
- is meaningfully different from the last visible nudge
- fits the nudge budget
- is attached to the current state version

Budget:

- average max: 1 visible nudge per 90 seconds
- hard cap: 5 visible nudges per normal call
- no manual "critical" override in the first prototype

Retraction rule:

- if a visible nudge is invalidated by a later correction, mark it retracted and remove or visually downgrade it in the panel

### 9. Live Panel

The panel reads from Live Interaction State, not directly from the model.

Initial sections:

- current state: `investigating`, `leading hypothesis`, or `resolving`
- ranked hypothesis if stable enough to display
- evidence and contradicting evidence
- next best verification question
- steps tried and outcomes
- unresolved unknowns
- active nudge or retraction

No chat input is needed for the prototype.

### 10. Post-Call Record

After call end:

- freeze final state
- include active and superseded facts
- include hypothesis history
- include troubleshooting timeline
- include nudge and retraction history
- include unresolved risk and repeat-contact risk
- include evidence event ids for every major claim

## First Prototype Build Order

1. Build the validation dataset plan and annotation schema.
2. Create 5 scripted replay fixtures only for plumbing.
3. Implement transcript replay into finalized utterance events.
4. Implement ASR/speaker quality fields in the event model, even if replay values are clean.
5. Implement candidate event detection for corrections, scope, recent change, step outcomes, explicit escalation, and unresolved objection.
6. Implement Live Interaction State with versions, superseded facts, and event sequences.
7. Implement semantic batcher for slow state updates.
8. Implement slow state updater as JSON patch generation over state plus event batch.
9. Implement versioned reconciler with stale-patch rejection.
10. Implement nudge gate, budget, and retraction support.
11. Implement minimal live panel reading from state.
12. Implement post-call operational record.
13. Run replay metrics on fixtures.
14. Run the 30-50 call validation gate before expanding live STT work.

## First Prototype Non-Goals

- no live STT dependency until replay pipeline works
- no TTS
- no autonomous customer response
- no learned semantic trigger
- no dual-LLM Thinker/Speaker orchestrator
- no aggregate organizational analytics
- no soft emotional scoring beyond explicit escalation or unresolved objection markers
- no broad support domain

## MVP Success Gate

Engineering fixture gate:

- state patches apply in order
- stale patches are rejected or safely rebased
- visible nudges stay below 5 per call
- visible nudges can be retracted
- post-call records preserve facts, hypotheses, recommendations, and supersessions separately

Product validation gate:

- 30-50 realistic calls are annotated
- early issue category is identifiable from the first 60-90 seconds in roughly 60 percent or more of realistic/blind-scored cases
- useful next diagnostic questions are identifiable before the agent naturally asks them
- false-positive nudge rate is low enough that the panel would not become noise
- hypothesis display remains stable after corrections

The product should not advance to a live STT copilot based only on five self-authored replay scripts.

## Full-Source Review Procedure

For future reviews, do not ask Claude to inspect only the PDF. Provide an extractable paper source.

Working review packet:

1. Include the original PDF.
2. Include the arXiv HTML or a plain-text extraction of the arXiv HTML.
3. Include `PRD_1st.md`, `initial_research/first_proposal.md`, and `initial_research/MARS-adverserial.md`.
4. Ask the reviewer to verify paper-specific claims against the extractable paper text, not just the architecture note.

This avoids the failure mode where a reviewer can see the PDF file but cannot extract its contents.
