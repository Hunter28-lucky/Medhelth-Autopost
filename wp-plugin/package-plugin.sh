#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

ZIP_NAME="pulse-content-sync.zip"
LEGACY_ZIP="ai-news-publisher.zip"
echo "Creating WordPress plugin archive: $ZIP_NAME..."

# Remove old zips if exist
rm -f "$ZIP_NAME" "$LEGACY_ZIP"

# Zip the plugin folder cleanly
zip -r "$ZIP_NAME" ai-news-publisher/ -x "*.DS_Store" -x "__MACOSX*"
cp "$ZIP_NAME" "$LEGACY_ZIP"

echo "Successfully built $ZIP_NAME and $LEGACY_ZIP ($DIR/$ZIP_NAME)"
