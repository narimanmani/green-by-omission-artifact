set -eu
cd /opt/replay/seed
node --version
npm --version
npm rebuild --offline --no-audit --no-fund
python3 /opt/replay/provenance/verify_seed.py
