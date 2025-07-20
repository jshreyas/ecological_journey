import uuid

from pymongo import MongoClient

# --- CONFIGURE THIS ---
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "ecological_journey"  # Change to your DB name
PLAYLISTS_COLLECTION = "playlists"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
playlists = db[PLAYLISTS_COLLECTION]


def migrate():
    updated_count = 0
    for playlist in playlists.find():
        playlist_changed = False
        for video in playlist.get("videos", []):
            for clip in video.get("clips", []):
                if "clip_id" not in clip or not clip["clip_id"]:
                    clip["clip_id"] = str(uuid.uuid4())
                    playlist_changed = True
        if playlist_changed:
            playlists.update_one(
                {"_id": playlist["_id"]}, {"$set": {"videos": playlist["videos"]}}
            )
            updated_count += 1
    print(f"Migration complete. Updated {updated_count} playlists.")


if __name__ == "__main__":
    migrate()
