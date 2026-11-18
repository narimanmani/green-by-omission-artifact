set -eu
apt-get -o APT::Sandbox::User=root update
DEBIAN_FRONTEND=noninteractive apt-get -o APT::Sandbox::User=root install -y --no-install-recommends git build-essential python3 ca-certificates
node --version
npm --version
git --version
python3 --version
g++ --version
dpkg-query -W
