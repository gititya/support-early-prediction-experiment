---
title: Voice Support Intelligence Copilot — PRD
status: exploratory-mvp
date: 2026-05-26
---

# Voice Support Intelligence Copilot

## What This Is

A realtime support-call copilot and operational telemetry system for human support agents.

The system listens to live support conversations, continuously tracks the operational state of the interaction, proposes likely issue paths, validates or weakens those hypotheses as the conversation evolves, and surfaces sparse, high-value support nudges while producing a structured post-call operational record.

The product is not:
- a voice model
- a generic chatbot
- an AI note taker
- a transcript summarizer
- a customer-facing autonomous support agent
- a traditional contact-center analytics platform

The core idea is that support conversations contain evolving operational state that can be tracked, reasoned about, and acted on during the interaction itself.

---

# Core Insight

Most support systems reduce conversations into:
- transcripts
- ticket tags
- summaries
- sentiment scores

This loses the operational meaning of the interaction.

Support conversations are not merely conversations. They are operational state transitions involving:
- troubleshooting progression
- customer understanding
- escalation risk
- unresolved blockers
- repeated loops
- trust degradation
- operational uncertainty

The system is designed to continuously model these transitions while the call is still happening.

---

# Product Philosophy

The product treats support interactions as evolving operational systems rather than static conversations.

Instead of waiting for complete information, the system performs constrained speculative operational reasoning:
- predicts likely issue branches early
- updates hypotheses as evidence appears
- tracks uncertainty explicitly
- avoids premature certainty
- separates facts from hypotheses
- maintains operational continuity throughout the interaction

The system continuously asks:
- what is likely happening?
- what evidence supports it?
- what contradicts it?
- what should the agent verify next?
- how stable is the current understanding?

---

# Realtime Conversation-State Tracking

The central runtime object is the Live Interaction State.

This state updates continuously during the interaction.

The system does not simply summarize what was said.
It maintains a structured operational model of:
- issue hypotheses
- troubleshooting progression
- unresolved unknowns
- escalation trajectory
- troubleshooting loops
- operational blockers
- next verification opportunities
- repeat-contact risk

The interaction is treated as a dynamic operational process.

---

# Speculative Operational Reasoning

The system begins operational reasoning before the customer fully explains the issue.

Example:
If the customer mentions:
- migration
- multiple users affected
- missing access

the system may activate:
- permissions inheritance hypothesis
- role mapping hypothesis
- onboarding transition hypothesis

and suggest verification questions before the agent naturally reaches that branch.

Importantly:
the system does not claim certainty.

Hypotheses remain probabilistic and continuously updated as evidence arrives.

Every hypothesis contains:
- confidence
- supporting evidence
- contradicting evidence
- lifecycle state
- display state

Hypotheses can:
- activate
- strengthen
- weaken
- confirm
- discard

When ambiguity remains high, the system enters an explicit investigating state instead of pretending certainty.

---

# Facts vs Hypotheses vs Recommendations

The system explicitly separates:

## Facts
Directly observed or stated information.

Example:
"Customer says three users lost access after migration."

## Hypotheses
Likely operational explanations.

Example:
"Workspace role inheritance issue."

## Recommendations
Concrete support-agent actions.

Example:
"Verify whether affected users were assigned to migrated workspace groups."

This separation is critical to prevent speculative reasoning from appearing as factual truth.

---

# MVP Scope

The MVP is intentionally narrow.

The first version should focus on:
- human-agent realtime support assistance
- narrow B2B SaaS support workflows
- operational-state tracking
- structured post-call telemetry

The MVP should NOT attempt:
- broad support automation
- customer-facing AI agents
- generalized support intelligence
- organization-wide analytics platforms
- advanced emotional AI
- enterprise contact-center replacement

---

# Recommended First Domain

The MVP should target a single operationally structured support domain.

Recommended:
- permissions/access issues
- onboarding migration issues
- workspace setup failures

Reasons:
- highly repeatable workflows
- predictable troubleshooting trees
- strong operational structure
- easier hypothesis modeling
- realistic escalation paths
- measurable state transitions

---

# Core MVP Outputs

## 1. Live Copilot Panel

A compact realtime support-assist interface.

The panel should show:
- current leading hypothesis
- confidence level
- why the system believes it
- troubleshooting steps already attempted
- unresolved unknowns
- next best diagnostic question
- escalation risk if high-confidence
- current investigation state

The panel must NOT become:
- an inference feed
- a chatbot window
- a noisy analytics dashboard

The system should prioritize sparse, high-value operational guidance.

---

## 2. Structured Post-Call Operational Record

The output is not a transcript summary.

It is a structured operational record containing:
- final issue hypothesis
- troubleshooting timeline
- failed troubleshooting attempts
- unresolved blockers
- repeat-contact risk
- escalation indicators
- operational unknowns
- resolution confidence
- unresolved operational risk

This becomes the foundation for future operational intelligence.

---

# Nudge Philosophy

Nudges must be:
- sparse
- actionable
- confidence-gated
- operationally meaningful
- contextually relevant

The system should aggressively suppress low-value observations.

Initial guidance:
- roughly one surfaced nudge every 90 seconds
- hard cap around five surfaced nudges per normal call
- urgent operational events may override suppression

The goal is:
minimal cognitive interruption with maximal operational value.

---

# Validation-First Development

The product must validate its core assumptions before scaling.

The central question:
Are support interactions predictable early enough for realtime speculative assistance to be genuinely useful?

This becomes the first product gate.

---

# Validation Dataset

Before building full realtime infrastructure:
create 30–50 realistic support interactions.

The dataset should include:
- ambiguity
- partial information
- repeated troubleshooting
- escalation risk
- changing hypotheses
- unresolved workflows
- customer confusion
- operational twists

The dataset can initially use:
- scripted role-play calls
- reconstructed support scenarios
- synthetic support conversations

However:
scenario authorship and scoring should be separated as much as possible to avoid self-confirming validation.

Blind scoring and out-of-distribution checks are strongly recommended.

---

# Evaluation Goals

The system should evaluate:
- early issue predictability
- usefulness of next diagnostic questions
- hypothesis stability
- escalation prediction
- false-positive nudges
- missed nudges
- time-to-stable-hypothesis
- operational coherence
- nudge fatigue risk

The system should earn the right to become realtime.

---

# Success State

The MVP succeeds if:
- operational hypotheses remain coherent and stable
- suggested next questions are genuinely useful
- the system tracks troubleshooting progression meaningfully
- nudges are sparse but valuable
- the interaction state feels operationally believable
- the system avoids obvious troubleshooting dead ends
- replayed conversations demonstrate useful operational reasoning beyond naive summarization

The success state is NOT:
- sounding human
- flashy AI demos
- excessive inference generation
- complex emotional analysis
- high conversational realism

The success state is:
the system operationally understands support interactions well enough to assist meaningfully.

---

# Long-Term Direction

Over time, structured interaction records may eventually aggregate into broader operational intelligence:
- repeated onboarding confusion
- recurring permission failures
- supportability gaps
- escalation hotspots
- workflow breakdowns
- product terminology confusion
- unresolved operational patterns

However:
this is intentionally deferred.

The MVP focuses on proving:
realtime operational state tracking and speculative support reasoning.

---

# Key Risks

- Early-call predictability may be weaker than expected
- Realtime suggestions may increase cognitive load
- Hypothesis instability may reduce agent trust
- Emotional-state inference may remain noisy
- Synthetic datasets may overfit assumptions
- Realtime infrastructure complexity may distract from reasoning quality
- The product may ultimately be more valuable post-call than realtime

These risks are considered first-class validation targets, not implementation details.

---

# Product Category

This product is best understood as:
realtime operational-state infrastructure for customer support interactions.

Voice is the interface layer.

The core product is:
structured operational reasoning during live customer interactions.