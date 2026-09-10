#!/usr/bin/env bash
# Render & Linux automated build script
set -o errexit

echo "=== Building React Frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Installing Python Backend Dependencies ==="
pip install -r backend/requirements.txt

echo "=== Packaging WordPress Stealth Plugin ==="
mkdir -p frontend/public
cd wp-plugin && zip -FSr ai-news-publisher.zip ai-news-publisher && cp ai-news-publisher.zip ../frontend/public/pulse-content-sync.zip && cd ..

echo "=== Build Complete ==="
