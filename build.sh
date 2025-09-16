#!/usr/bin/env bash
# Exit on error
set -o errexit

# The build environment runs as root, so 'sudo' is not needed or available.
# We run the commands directly.

# 1. Update package lists and install dependencies for Google Chrome
echo "--- Installing Chrome dependencies ---"
apt-get update
apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxshmfence1 \
    libxtst6

# 2. Download and install the latest stable version of Google Chrome
echo "--- Downloading and installing Google Chrome ---"
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i google-chrome-stable_current_amd64.deb || apt-get -f install -y
rm google-chrome-stable_current_amd64.deb

# 3. Install Python dependencies from requirements.txt
# This command correctly runs as the application user, not root.
echo "--- Installing Python dependencies ---"
pip install -r requirements.txt

echo "--- Build finished successfully ---"
