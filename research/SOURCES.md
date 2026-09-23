# Research sources

## LTS-VoiceAgent: A Listen-Think-Speak Framework for Efficient Streaming Voice Interaction via Semantic Triggering and Incremental Reasoning

- **Relationship:** architectural inspiration, not a blueprint.
- **Canonical PDF:** `/Users/aditya/Documents/docs/research/lts-voiceagent-listen-think-speak.pdf`
- **Full reading note:** `[[LTS-VoiceAgent - A Listen-Think-Speak Framework]]`
- **Source:** Zou et al., 2026.

### Applied

- The architecture note used the paper to examine when a support system should trigger work before a caller finishes.
- It separates cheap candidate-event detection from a semantic trigger and rejects keyword rules as semantic triggering by themselves.

### Not adopted or not supported

- The project does not claim to reproduce the paper's model, training, latency, or benchmark result.
- It does not implement a learned semantic trigger.

### Project evidence

- `VOICEAGENT_ARCHITECTURE_NOTE.md` - full paper-to-MVP mapping and explicit boundary.
