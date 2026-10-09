#!/bin/sh
# Official Docker apt repository; never remove existing container runtimes.
set -eu
if [ "$(id -u)" -ne 0 ]; then
    echo 'Run on the server as root.' >&2
    exit 1
fi
. /etc/os-release
if [ "$ID" != ubuntu ] || [ "$VERSION_CODENAME" != jammy ]; then
    echo 'This reviewed installer is for Ubuntu 22.04 only.' >&2
    exit 1
fi
if command -v docker >/dev/null 2>&1; then
    docker version
    docker compose version
    exit 0
fi
for package in docker.io docker-compose containerd runc podman-docker; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
        echo "Existing runtime package: $package. Review it before installing." >&2
        exit 1
    fi
done
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=l
apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl --connect-timeout 15 --max-time 60 -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/travel-docker.asc
chmod 0644 /etc/apt/keyrings/travel-docker.asc
ARCHITECTURE=$(dpkg --print-architecture)
SOURCE=/etc/apt/sources.list.d/travel-docker.sources
if [ -e "$SOURCE" ]; then
    echo 'Docker source file already exists. Review before replacing.' >&2
    exit 1
fi
cat > "$SOURCE" <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: jammy
Components: stable
Architectures: $ARCHITECTURE
Signed-By: /etc/apt/keyrings/travel-docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
