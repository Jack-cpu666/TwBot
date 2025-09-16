#!/usr/bin/env bash
# Exit on error
set -o errexit

# --- THE FIX IS HERE: Add 'sudo' to all apt-get and dpkg commands ---

# 1. Install dependencies for Google Chrome using sudo for root privileges
echo "--- Installing Chrome dependencies ---"
sudo apt-get update
# Use -y to automatically answer yes to prompts
sudo apt-get install -y libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libxshmfence1 libxtst6

# 2. Download and install the latest stable version of Google Chrome
echo "--- Downloading and installing Google Chrome ---"
# wget does not need sudo as it downloads to the local directory
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
# dpkg and apt-get need sudo to install system packages
sudo dpkg -i google-chrome-stable_current_amd64.deb || sudo apt-get -f install -y
# rm does not need sudo to remove a file in the local directory
rm google-chrome-stable_current_amd64.deb

# 3. Install Python dependencies from requirements.txt
# pip should NOT use sudo, as it installs packages for your application user.
echo "--- Installing Python dependencies ---"
pip install -r requirements.txt

echo "--- Build finished successfully ---"
