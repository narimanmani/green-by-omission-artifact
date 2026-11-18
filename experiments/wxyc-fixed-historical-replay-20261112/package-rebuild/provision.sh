set -eu
mkdir -p /home/node/work/wxyc-shared
tar -xzf /tmp/source.tar.gz --strip-components=1 --no-same-owner -C /home/node/work/wxyc-shared
cd /home/node/work/wxyc-shared
node --version
npm --version
npm ci --ignore-scripts --no-audit --no-fund
