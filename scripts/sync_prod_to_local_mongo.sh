#!/bin/bash

set -e

# 🔍 Ensure PRD_MONGODB_URI is set
if [ -z "$PRD_MONGODB_URI" ]; then
  echo "❌ Error: PRD_MONGODB_URI is not set in environment."
  exit 1
fi

DB_NAME="ecological_journey"
CONTAINER_NAME="ecological_mongo"
TEMP_DUMP_DIR=$(mktemp -d)

# 📤 Step 1: Dump from production to temp dir
echo "📦 Dumping database '$DB_NAME' from production..."
mongodump --uri="$PRD_MONGODB_URI" --db="$DB_NAME" --out="$TEMP_DUMP_DIR"

# 📥 Step 2: Copy dump to Docker container
echo "🐳 Copying dump into container '$CONTAINER_NAME'..."
docker cp "$TEMP_DUMP_DIR" "$CONTAINER_NAME":/dump

# ♻️ Step 3: Restore inside the container
echo "🛠️ Restoring dump inside container..."
docker exec -i "$CONTAINER_NAME" mongorestore --db "$DB_NAME" --drop /dump/"$DB_NAME"

# 🧹 Step 4: Cleanup
echo "🧹 Cleaning up..."
rm -rf "$TEMP_DUMP_DIR"
docker exec -i "$CONTAINER_NAME" rm -rf /dump

echo "✅ Sync complete! Local MongoDB is now seeded with production data."
