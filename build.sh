#!/usr/bin/env bash
# Exit on error
set -o errexit

# Only install Python dependencies
echo "--- Installing Python dependencies ---"
pip install -r requirements.txt

echo "--- Build finished successfully ---"
