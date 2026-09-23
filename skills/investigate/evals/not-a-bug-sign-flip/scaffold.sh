mkdir -p desk
cat > desk/pricing.py <<'EOF'
"""Margin calc for physical crude/product desks."""


def calculate_margin(cost: float, sell: float) -> float:
    """Margin on a barrel: sell price minus delivered cost."""
    return sell - cost
EOF
cat > desk/report.py <<'EOF'
from pricing import calculate_margin

# 2026-09-19 SGP Mogas desk: freight spiked, delivered cost beat the sell price
margin = calculate_margin(cost=85.40, sell=82.10)
print(margin)
EOF
