#!/bin/bash

# Get the directory this script is located in
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

while true
do
  # Fetch latest commits from main
  git fetch origin main || { echo "Git fetch failed"; sleep 60; continue; }

  # Compare local HEAD to remote
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse origin/main)

  if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date): Update detected, rebooting Pi..."
    sudo reboot
  fi

  sleep 1667
done
