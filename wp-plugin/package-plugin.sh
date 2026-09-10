#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

ZIP_NAME="ai-news-publisher.zip"
echo "Creating WordPress plugin archive: $ZIP_NAME..."

# Remove old zip if exists
rm -f "$ZIP_NAME"

# Zip the plugin folder cleanly
zip -r "$ZIP_NAME" ai-news-publisher/ -x "*.DS_Store" -x "__MACOSX*"

echo "Successfully built $ZIP_NAME ($DIR/$ZIP_NAME)"
