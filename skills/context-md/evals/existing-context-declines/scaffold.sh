cat > CONTEXT.md <<'EOF'
# Context

## Order
A confirmed trade ticket for a physical or paper cargo.

## Desk
A trading team responsible for one product and region, e.g. SGP Mogas.
EOF
mkdir -p src/orders
cat > src/orders/models.py <<'EOF'
class Order:
    def __init__(self, order_id: str, desk: str):
        self.order_id = order_id
        self.desk = desk
EOF
