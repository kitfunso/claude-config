import time

from pricing import rolling_total


def test_rolling_total():
    time.sleep(1.5)  # stands in for a slow page render
    assert rolling_total([1, 2, 3, 4], 2) == [1, 3, 5, 7]
