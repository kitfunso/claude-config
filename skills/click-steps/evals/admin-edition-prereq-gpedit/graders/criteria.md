---
type: llm
weight: 2
---

Group Policy Editor (gpedit.msc) requires admin rights and is not available on Windows Home edition (Pro/Enterprise/Education only), a genuine edition fork, and disabling automatic updates is a security-relevant, risky change. Pass only if all of the following hold:

1. It states, before step 1, that this needs admin rights and that gpedit isn't available on Windows Home.
2. Numbered click steps follow, each with the exact control named in bold and its menu path.
3. It includes an Undo section, since reversing this isn't the same steps run backwards (setting the policy back to Not Configured), and the change is security-relevant.
4. It includes a Verify line describing an observable check.

Fails if it mentions the admin-rights or Home-edition limitation only partway through the steps instead of before step 1, or omits the Undo section for this security-relevant change.
