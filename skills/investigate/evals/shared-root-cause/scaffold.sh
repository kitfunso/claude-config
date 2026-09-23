mkdir -p utils desk
cat > utils/numbers.py <<'EOF'
"""Shared numeric parsing helpers."""


def to_float(raw: str) -> float:
    return float(raw)
EOF
cat > desk/pnl_shaping.py <<'EOF'
from utils.numbers import to_float


def brent_leg_value(raw_price: str, barrels: float) -> float:
    return to_float(raw_price) * barrels
EOF
cat > desk/arb_economics.py <<'EOF'
from utils.numbers import to_float


def freight_adjusted_cost(raw_cost: str, freight: float) -> float:
    return to_float(raw_cost) + freight
EOF
