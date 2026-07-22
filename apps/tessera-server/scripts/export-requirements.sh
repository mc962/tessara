#!/bin/bash
set -e

echo "Exporting requirements files..."

uv export --no-dev --output-file requirements.txt

git add requirements.txt
echo "All requirements files updated and staged"
