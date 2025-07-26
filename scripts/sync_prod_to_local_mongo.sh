#!/bin/bash

set -e

# 🧩 CONFIGURATION
PRD_MONGODB_URI="mongodb://localhost:27017"
DB_NAME="ecological_journey"
DUMP_DIR="./dump"
CONTAINER_NAME="ecological_mongo"

# 📤 Step 1: Dump from production
echo "📦 Dumping database '$DB_NAME' from production..."
mongodump --uri="$PRD_MONGODB_URI" --db="$DB_NAME" --out="$DUMP_DIR"

# 📥 Step 2: Copy dump to Docker container
echo "🐳 Copying dump into container '$CONTAINER_NAME'..."
docker cp "$DUMP_DIR" "$CONTAINER_NAME":/dump

# ♻️ Step 3: Restore inside the container
echo "🛠️ Restoring dump inside container..."
docker exec -i "$CONTAINER_NAME" mongorestore --nsInclude="${DB_NAME}.*" --drop /dump/"$DB_NAME"

# 🧹 Step 4: Cleanup
echo "🧹 Cleaning up..."
rm -rf "$DUMP_DIR"
docker exec -i "$CONTAINER_NAME" rm -rf /dump

echo "✅ Sync complete! Local MongoDB is now seeded with production data."
