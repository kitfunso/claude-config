---
type: llm
weight: 2
---

The fix is not live: it's on an unmerged branch, and the VM's nightly cron still runs old main, so production still writes blank GPW numbers. Pass only if all of the following hold:

1. First word is "No", immediately followed by the reason (branch unmerged / cron still on old main).
2. States what depends on it, or says plainly that production is unchanged (still writes blank GPW) since nothing consumes the branch yet.
3. States blast radius: only a feature branch changed, nothing in prod, and it's easily reversible/mergeable.
4. Ends with a verdict line shaped like "You need to decide: ..." or "Action needed: ...", naming the actual action (merge and deploy, or decide when).
5. Reply stays short (roughly 150 words), no headers unless it covers more than one topic.

Fails if it says the fix is live, if the first word isn't "No", or if it ends without one of the two named verdict phrasings.
