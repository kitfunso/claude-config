---
type: llm
weight: 2
---

The draft is loaded with AI-slop patterns: a throat-clearing opener ("Here's the thing"), two binary-contrast sentences ("wasn't just X, it was Y" / "didn't just X, we Y"), a colon-reveal ("The key detail that makes it work:"), banned words ("paradigm shift", "robust", "streamlined"), weasel attribution ("Experts agree", "studies show"), importance puffery ("stands as a testament"), an empty phrase ("At the end of the day"), and a summary-recap ending ("In conclusion"). Pass only if all of the following hold:

1. The edited draft removes or rewrites at least five of these patterns (banned words, weasel attribution, importance puffery, the colon-reveal, the binary contrasts, and the recap ending count individually).
2. It does not invent new facts, stats, or attributions to replace the vague ones (for example it does not make up a specific failure-rate number that was not given); it either states the claim plainly without a source or flags that no source was given.
3. The core meaning survives: the old pipeline was slow and fragile, a single retry helper is now shared across every loader.
4. The reply includes the full edited draft plus a short **What changed** section.
5. The edit is not turned into generic, equally-tidy corporate prose; it should still read like one person wrote it, not like it was run through a polish filter.

Fails if three or more of the banned words/phrases survive unchanged, if the reply invents evidence, or if the edited draft is missing entirely.
