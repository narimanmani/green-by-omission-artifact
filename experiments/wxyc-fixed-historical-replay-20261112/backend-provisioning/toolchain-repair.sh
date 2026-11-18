set -eu
mkdir -p /tmp/wxyc-apt-archives/partial
apt-get -o APT::Sandbox::User=root update
DEBIAN_FRONTEND=noninteractive apt-get -o APT::Sandbox::User=root -o Dir::Cache::archives=/tmp/wxyc-apt-archives install -y --no-install-recommends git build-essential python3 ca-certificates
node --version
npm --version
git --version
python3 --version
g++ --version
dpkg-query -W
