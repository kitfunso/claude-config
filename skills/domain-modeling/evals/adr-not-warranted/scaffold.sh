cat > CONTEXT.md <<'EOF'
# Context

## Purchase
A confirmed trade ticket for a physical or paper cargo. See src/purchases/.
EOF
mkdir -p src/purchases
cat > src/purchases/models.py <<'EOF'
class Purchase:
    def __init__(self, purchase_id: str, desk: str):
        self.purchase_id = purchase_id
        self.desk = desk
EOF
