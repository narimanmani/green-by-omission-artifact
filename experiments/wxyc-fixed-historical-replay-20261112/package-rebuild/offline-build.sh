set -eu
cd /home/node/work/wxyc-shared
node --version
npm --version
npm run generate:typescript
npm run build
npm pack --json
