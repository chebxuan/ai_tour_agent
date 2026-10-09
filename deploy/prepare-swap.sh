#!/bin/sh
# Optional for the existing small Ubuntu server; preserve every existing swap.
set -eu
if [ "$(id -u)" -ne 0 ]; then
    echo 'Run as root on the server.' >&2
    exit 1
fi
if [ -n "$(swapon --show --noheadings)" ]; then
    echo 'Existing swap is active; left unchanged.'
    exit 0
fi
SWAP_FILE=/swap.travel-copilot
if [ -e "$SWAP_FILE" ]; then
    echo 'Swap file already exists; review before changing it.' >&2
    exit 1
fi
fallocate -l 2G "$SWAP_FILE"
chmod 600 "$SWAP_FILE"
mkswap "$SWAP_FILE"
swapon "$SWAP_FILE"
if [ ! -e /etc/fstab.before-travel-copilot ]; then
    cp -p /etc/fstab /etc/fstab.before-travel-copilot
fi
echo "$SWAP_FILE none swap sw 0 0" >> /etc/fstab
free -m
