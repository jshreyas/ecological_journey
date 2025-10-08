import math
import os
from pathlib import Path
from typing import Optional

import httpx

PEERTUBE_URL: str = "https://makertube.net"
PEERTUBE_TOKEN: str = "08d80740687e374e4b9184605115785211ed9a29"
CHUNK_SIZE_MB: int = 80  # 80MB per chunk


class PeerTubeClient:
    """Lightweight client for PeerTube REST API."""

    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or PEERTUBE_URL.rstrip("/")
        self.token = token or PEERTUBE_TOKEN
        self.headers = {"Authorization": f"Bearer {self.token}"}

    async def create_channel(self, name: str, display_name: Optional[str] = None):
        data = {"name": name, "displayName": display_name or name}
        async with httpx.AsyncClient() as client:
            r = await client.post(f"{self.base_url}/api/v1/users/me/channels", headers=self.headers, data=data)
            r.raise_for_status()
            return r.json()

    async def list_channels(self):
        async with httpx.AsyncClient() as client:
            request = await client.get(f"{self.base_url}/api/v1/video-channels", headers=self.headers)
            request.raise_for_status()
            return request.json()

    async def get_video(self, video_id: str):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/api/v1/videos/{video_id}", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def delete_video(self, video_id: str):
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{self.base_url}/api/v1/videos/{video_id}", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def upload_and_attach_to_playlist(
        self,
        file_input: Path,
        name: str,
        channel_id: int = 12187,
        file_input_name: str = "uploaded_file.mp4",
        playlist_id: int = 37814,
    ):
        """
        Upload a video to the specified channel, then attach it to a playlist.
        """
        video_info = await self.upload_resumable(
            file_input, channel_id=channel_id, name=name, file_input_name=file_input_name
        )
        video_id = video_info["video"]["uuid"]
        await self.add_video_to_playlist(playlist_id, video_id)
        return video_info

    async def get_playlist(self, playlist_id: str):
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/api/v1/video-playlists/{playlist_id}", headers=self.headers)
            r.raise_for_status()
            return r.json()

    async def _get_playlist_videos(self, playlist_id: str):
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.base_url}/api/v1/video-playlists/{playlist_id}/videos", headers=self.headers)
            res.raise_for_status()
            return res.json()

    async def get_playlist_videos(self, playlist_id: str):
        videos = []
        playlist_videos = await self._get_playlist_videos(playlist_id)
        for each in playlist_videos["data"]:
            video_data = {
                "title": each["video"]["name"],
                "video_id": f'{each["video"]["id"]}',
                "youtube_url": each["video"]["url"],
                "date": each["video"]["publishedAt"].replace("Z", "+00:00"),
                "type": "",
                "partners": [],
                "positions": [],
                "notes": "",
                "labels": [],
                "clips": [],
                "duration_seconds": each["video"]["duration"],
            }
            # Fetch and replace youtube url with hls url
            videos.append(video_data)
        return videos

    async def add_video_to_playlist(self, playlist_id: str, video_id: str, position: Optional[int] = None):
        """
        Add a video to a given playlist.

        Args:
            playlist_id: The PeerTube playlist ID.
            video_id: The PeerTube video UUID or numeric ID.
            position: Optional numeric position within the playlist.
        """
        data = {"videoId": video_id}
        if position is not None:
            data["position"] = position

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/api/v1/video-playlists/{playlist_id}/videos", headers=self.headers, data=data
            )
            r.raise_for_status()
            return r.json()

    async def upload_video(self, file_path: Path, name: str, channel_id: Optional[str] = 12177):
        """Simple full upload (non-chunked)"""
        data = {"name": name}
        if channel_id:
            data["channelId"] = channel_id
        timeout = httpx.Timeout(600.0, read=600.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            with open(file_path, "rb") as f:
                files = {"videofile": (file_path.name, f, "video/mp4")}
                r = await client.post(
                    f"{self.base_url}/api/v1/videos/upload",
                    headers=self.headers,
                    data=data,
                    files=files,
                )
                r.raise_for_status()
                return r.json()

    async def upload_resumable(
        self,
        file_input,
        name: str,
        channel_id: int = 12187,  # 12177,
        file_input_name: str = "uploaded_file.mp4",
        on_progress=None,  # NEW
    ):
        import math
        import os

        import httpx

        # Determine if we got a path or file-like object
        if hasattr(file_input, "read"):  # file-like (streaming)
            file_obj = file_input
            file_obj.seek(0, os.SEEK_END)
            file_size = file_obj.tell()
            file_obj.seek(0)
            file_name = file_input_name
        else:  # Path
            file_obj = open(file_input, "rb")
            file_size = os.path.getsize(file_input)
            file_name = os.path.basename(file_input)

        chunk_size = CHUNK_SIZE_MB * 1024 * 1024
        num_chunks = math.ceil(file_size / chunk_size)
        headers = {"Authorization": f"Bearer {self.token}"}
        timeout = httpx.Timeout(600.0, read=600.0)

        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            # 1️⃣ Initialize resumable upload
            init_headers = {
                **headers,
                "X-Upload-Content-Length": str(file_size),
                "X-Upload-Content-Type": "video/mp4",
            }
            init_body = {"channelId": channel_id, "filename": file_name, "name": name, "privacy": "1"}

            print("DEBUG: Initializing upload with init_body:", init_body)
            init_resp = await client.post(
                f"{self.base_url}/api/v1/videos/upload-resumable",
                headers=init_headers,
                data=init_body,
            )
            init_resp.raise_for_status()
            chunk_url = init_resp.headers["location"]
            print(f"✅ Initialized upload: {chunk_url}")

            # 2️⃣ Upload chunks
            uploaded_bytes = 0
            for i in range(num_chunks):
                chunk = file_obj.read(chunk_size)
                start = uploaded_bytes
                end = min(start + len(chunk), file_size) - 1

                put_headers = {
                    **headers,
                    "Content-Length": str(len(chunk)),
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Content-Type": "application/octet-stream",
                }

                res = await client.put(chunk_url, headers=put_headers, content=chunk)
                uploaded_bytes += len(chunk)

                # 🔁 Report progress if callback provided
                if on_progress:
                    await on_progress(uploaded_bytes, file_size)

                if res.status_code == 308:
                    print(f"📦 Chunk {i+1}/{num_chunks} accepted ({uploaded_bytes/file_size*100:.1f}%)")
                    continue
                elif res.status_code in (200, 201):
                    print("🎉 Upload complete!")
                    return res.json()
                else:
                    res.raise_for_status()

    async def _upload_resumable(self, file_path: Path, name: str, channel_id: int = 12177):
        file_size = os.path.getsize(file_path)
        chunk_size = CHUNK_SIZE_MB * 1024 * 1024
        num_chunks = math.ceil(file_size / chunk_size)
        headers = {"Authorization": f"Bearer {self.token}"}
        timeout = httpx.Timeout(600.0, read=600.0)

        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            # 1️⃣ Initialize resumable upload
            init_headers = {
                **headers,
                "X-Upload-Content-Length": str(file_size),
                "X-Upload-Content-Type": "video/mp4",
            }
            init_body = {
                "channelId": channel_id,
                "filename": file_path.name,
                "name": name,
            }

            init_resp = await client.post(
                f"{self.base_url}/api/v1/videos/upload-resumable",
                headers=init_headers,
                data=init_body,
            )
            init_resp.raise_for_status()
            chunk_url = init_resp.headers["location"]
            print(f"✅ Initialized upload: {chunk_url}")

            # 2️⃣ Upload chunks
            with open(file_path, "rb") as f:
                for i in range(num_chunks):
                    chunk = f.read(chunk_size)
                    start = i * chunk_size
                    end = min(start + len(chunk), file_size) - 1

                    put_headers = {
                        **headers,
                        "Content-Length": str(len(chunk)),
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Content-Type": "application/octet-stream",
                    }

                    res = await client.put(
                        chunk_url,
                        headers=put_headers,
                        content=chunk,
                    )

                    # ✅ DO NOT raise on 308
                    if res.status_code == 308:
                        print(f"📦 Chunk {i+1}/{num_chunks} accepted ({res.headers.get('Range')})")
                        continue
                    elif res.status_code in (200, 201):
                        print("🎉 Upload complete!")
                        return res.json()
                    else:
                        res.raise_for_status()

    async def upload_chunked(self, file_path: Path, name: str, channel_id: int = 12177):
        """Proper resumable upload for large files (>2GB)."""
        timeout = httpx.Timeout(600.0, read=600.0)

        async with httpx.AsyncClient(timeout=timeout) as client:
            # 1️⃣ Init the resumable upload
            init_data = {"name": name, "channelId": str(channel_id)}
            init_resp = await client.post(
                f"{self.base_url}/api/v1/videos/upload-resumable/init",
                headers=self.headers,
                data=init_data,
            )
            init_resp.raise_for_status()
            upload_id = init_resp.json()["uploadId"]

            # 2️⃣ Upload chunks
            file_size = os.path.getsize(file_path)
            chunk_size = CHUNK_SIZE_MB * 1024 * 1024
            num_chunks = math.ceil(file_size / chunk_size)

            with open(file_path, "rb") as f:
                for i in range(num_chunks):
                    chunk = f.read(chunk_size)
                    start = i * chunk_size
                    end = min(start + len(chunk), file_size) - 1
                    headers = {
                        **self.headers,
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Upload-Id": upload_id,
                    }
                    files = {"videofile": (file_path.name, chunk, "video/mp4")}
                    r = await client.post(
                        f"{self.base_url}/api/v1/videos/upload-resumable",
                        headers=headers,
                        files=files,
                    )
                    r.raise_for_status()
                    print(f"Uploaded chunk {i+1}/{num_chunks}")

            # 3️⃣ Finalize upload
            finish_resp = await client.post(
                f"{self.base_url}/api/v1/videos/upload-resumable/finish",
                headers=self.headers,
                data={"uploadId": upload_id},
            )
            finish_resp.raise_for_status()
            return finish_resp.json()
