---
name: retry-unbound-local
tags: [grill-me, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Grill this, is the retry logic actually solid before I wire it into the price fetcher?

```python
def fetch_with_retry(url: str, tries: int = 3) -> dict:
    for i in range(tries):
        try:
            resp = requests.get(url, timeout=5)
            return resp.json()
        except requests.RequestException:
            time.sleep(2 ** i)
    return resp.json()
```
