#!/usr/bin/env bash
# Render & Linux automated build script
set -o errexit

echo "=== Packaging WordPress Stealth Plugin ==="
mkdir -p frontend/public
cd wp-plugin && zip -FSr ai-news-publisher.zip ai-news-publisher && cp ai-news-publisher.zip pulse-content-sync.zip && cp pulse-content-sync.zip ../frontend/public/pulse-content-sync.zip && cd ..

echo "=== Building React Frontend ==="
cd frontend
npm install
npm run build
cp public/pulse-content-sync.zip dist/pulse-content-sync.zip 2>/dev/null || true
cd ..

echo "=== Installing Python Backend Dependencies ==="
pip install -r backend/requirements.txt

echo "=== Build Complete ==="
