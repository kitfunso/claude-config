---
name: etl-bare-except
tags: [critique, ro]
plugins: ["../.."]
runs: 3
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Critique this before I ship it, brutally honest:

```python
import pandas as pd

def load_prices(path="C:/dl/prices.csv"):
    try:
        df = pd.read_csv(path)
        df["date"] = pd.to_datetime(df["date"])
        df = df.drop_duplicates(subset="date", keep="first")
        return df
    except:
        print("failed to load")
        return None

def daily_mean(df):
    return df.groupby("date")["price"].mean()
```
