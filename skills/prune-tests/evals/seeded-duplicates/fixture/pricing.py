"""Toy desk helpers for the prune-tests seeded eval."""


def spread(a: float, b: float) -> float:
    return a - b


def clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def band(x: float) -> str:
    if x < 10:
        return "low"
    if x < 50:
        return "mid"
    return "high"


def rolling_total(xs: list[float], window: int) -> list[float]:
    out = []
    for i in range(len(xs)):
        start = max(0, i - window + 1)
        out.append(sum(xs[start:i + 1]))
    return out
