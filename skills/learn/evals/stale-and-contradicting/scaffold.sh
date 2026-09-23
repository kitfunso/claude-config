cat > learnings.jsonl <<'EOF'
{"type":"pitfall","key":"csv-bom-drop","insight":"ETL silently drops rows when the source CSV has a BOM character","confidence":8,"source":"observed","files":["etl/load_csv.py"]}
{"type":"pattern","key":"retry-backoff","insight":"Use exponential backoff on the price API, it rate-limits after 5 calls/sec","confidence":9,"source":"observed","files":["etl/fetch_prices.py"]}
{"type":"preference","key":"cache-ttl","insight":"Cache prices for 60 seconds","confidence":6,"source":"observed","files":["etl/fetch_prices.py"]}
{"type":"preference","key":"cache-ttl","insight":"Never cache prices, always fetch fresh","confidence":7,"source":"observed","files":["etl/fetch_prices.py"]}
{"type":"pattern","key":"legacy-loader","insight":"legacy_loader.py handles the old XML format","confidence":7,"source":"observed","files":["etl/legacy_loader.py"]}
EOF
mkdir -p etl
cat > etl/load_csv.py <<'EOF'
def load(path: str):
    with open(path, encoding="utf-8") as f:
        return f.read()
EOF
cat > etl/fetch_prices.py <<'EOF'
def fetch_prices(pairs: list[str]) -> dict:
    return {}
EOF
