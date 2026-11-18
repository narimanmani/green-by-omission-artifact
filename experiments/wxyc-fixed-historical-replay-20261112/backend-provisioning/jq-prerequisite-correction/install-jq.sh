set -eu
mkdir -p /tmp/wxyc-apt-archives/partial
DEBIAN_FRONTEND=noninteractive apt-get -o APT::Sandbox::User=root -o Dir::Cache::archives=/tmp/wxyc-apt-archives install -y --no-install-recommends jq=1.6-2.1+deb12u3
