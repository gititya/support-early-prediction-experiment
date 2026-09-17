# Can the opening of a support call reveal the cause?

I wanted to test an idea: could an LLM work out the cause of a customer's problem early enough to help the support rep get ahead of the call, during the call itself?

A customer saying “three people cannot get into the workspace after a migration” tells me where to begin the investigation. It does not yet tell me whether the cause is permissions, a login problem, or something that went wrong in the migration.

This experiment asked whether a model could make that more specific diagnosis from only the first six conversation turns.

## What I built

I used fictional support conversations with a known cause for each case.
1. One model created the conversations and their answer keys.
2. A separate model read only the conversation text and predicted the cause; it could not see the answer key.
3. A third model compared its prediction with the intended answer.

I checked three things:
1. Could it identify the **specific cause** at the beginning of the call?
2. Could it at least identify the **broad category of problem**?
3. Could it identify the cause after reading the **whole conversation**, once more evidence was available?

The target for early specific diagnosis was 60% correct.

## What happened

| Check | First set: 51 fictional calls | Second, harder set: 48 fictional calls |
| --- | --- | --- |
| Specific cause from the first six turns | 7 correct — 14% | 1 correct — 2% |
| Broad type of problem from the first six turns | 46 correct — 90% | 45 correct — 94% |
| Specific cause from the whole conversation | 47 correct — 92% | 44 correct — 92% |

The opening usually gave the model enough to recognise the kind of problem. It rarely gave it enough to identify the actual cause, and reading the rest of the conversation changed that substantially.

The two sets are shown separately because they contain different cases. Neither reached the target for early diagnosis.

## What changed when I gave it the whole call?

This was the important comparison - when I removed the six-turn constraint and gave the model the complete conversation, it identified the intended cause in **47 of 51 cases (92%)** in the first set and **44 of 48 (92%)** in the harder set.

So, the model could usually work out the intended cause once it had the full conversation. The early failures did not mean it was incapable of identifying those causes; its answers improved substantially with more context.

## The lesson

**Recognising the type of problem and having enough evidence to diagnose it are two different milestones. A copilot should help a rep move from the first to the second.**

The contrast mattered: roughly 92% correct with the whole call, but only 2–14% from the opening. Asking for the diagnosis earlier did not give the rep the same answer sooner. It usually gave them a wrong answer to work around.

That changed the question I wanted to test. Given what the customer has said so far, what is still unknown, and which question or check would help distinguish the possible causes? As new evidence arrives, can the system change its view instead of defending its first guess?

## Where this led

That is the direction of Copilot Lab: private assistance for the human rep during an investigation. It should keep track of facts, competing explanations and the evidence needed before recommending a fix or a transfer. The rep remains in control of what to ask and whether the proposed fix worked.

This experiment explains the choice to pursue that direction. It does not establish that the copilot can do it well; that needs its own assessment.

## Some limitations:

1. These were fictional conversations, and a model judged whether predictions matched their intended causes. That makes this a controlled experiment, not a measurement of real support calls.
2. The results do not prove that early diagnosis always fails. These diagnosis scores do not establish that a copilot can ask consistently useful questions or help a real rep resolve a case. That needs its own assessment.
