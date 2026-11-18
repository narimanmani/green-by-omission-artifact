set -eu
cd /opt/replay/seed
node --version
npm --version
git rev-parse HEAD
git rev-parse origin/main
npm cache add /opt/replay/provenance/wxyc-shared-4.1.0.tgz --ignore-scripts --no-audit --no-fund
npm ci --ignore-scripts --prefer-offline --no-audit --no-fund
