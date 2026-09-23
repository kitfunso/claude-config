---
type: llm
weight: 2
---

No CONTEXT.md or ubiquitous-language file exists in this workspace. The sentence uses generic engineering jargon: "backfill" (filling in missing historical data), "golden set" (a saved, trusted comparison dataset), "shadow write" (a write to a copy/test destination, not the live one), "hot path" (the main code that runs on every live request), "flip" (switching over to the new version). Pass only if all of the following hold:

1. It re-pitches the sentence in short, simple sentences: one idea per sentence, not jargon left untranslated.
2. It gives a little orienting context before diving into the explanation.
3. It explains each term in plain words (paraphrase is fine; exact wording above not required) rather than repeating the jargon unexplained.
4. It does not present the explanation as sourced from a specific project document it actually found and read. Noting that it checked for CONTEXT.md and found none is fine and even preferred; what fails is inventing a definition and attributing it to an authoritative doc that does not exist.

Fails if the reply just restates the original sentence with a couple of words swapped, or invents a citation to a specific file or document that was never read.
