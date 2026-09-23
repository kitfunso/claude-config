mkdir -p desk
cat > desk/logging_utils.py <<'EOF'
import logging

logger = logging.getLogger(__name__)


def log_trade(desk: str, notional: float) -> None:
    message = f"trade booked desk={desk} notional={notional}"
    logger.info(message)
EOF
