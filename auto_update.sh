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
    echo "$(date): Update detected, pulling latest changes and rebooting Pi..."
    git pull origin main || { echo "$(date): Git pull failed, skipping reboot."; sleep 60; continue; }
    sudo reboot
  fi

  sleep 1667
done
