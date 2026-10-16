from pricing import band, clamp, spread


def test_spread():
    assert spread(5, 3) == 2


def test_spread_copy():
    assert spread(7, 2) == 5


def test_clamp_all():
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
    assert clamp(5, 0, 10) == 5


def test_clamp_low_dup():
    assert clamp(-5, 0, 10) == 0


def test_band_cases():
    assert band(3) == "low"
    assert band(20) == "mid"
    assert band(80) == "high"


def test_band_low_again():
    assert band(4) == "low"


def test_band_edge():
    assert band(10) == "mid"
