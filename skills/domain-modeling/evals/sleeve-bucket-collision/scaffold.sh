cat > CONTEXT.md <<'EOF'
# Context

## Order
A confirmed trade ticket for a physical or paper cargo. See src/orders/.
EOF
mkdir -p src/sleeves src/reporting
cat > src/sleeves/allocator.py <<'EOF'
"""Capital allocation for strategies."""


class Sleeve:
    """A capital allocation bucket for one strategy."""

    def __init__(self, sleeve_id: str, capital: float):
        self.sleeve_id = sleeve_id
        self.capital = capital
EOF
cat > src/reporting/bucket_report.py <<'EOF'
def bucket_pnl(bucket_id: str) -> float:
    # bucket_id is a Sleeve.sleeve_id; reporting kept its own name from before the sleeves rename
    return _load_pnl(bucket_id)
EOF
cat > README.md <<'EOF'
Each strategy runs inside its own sleeve. The nightly report groups PnL by bucket.
EOF
