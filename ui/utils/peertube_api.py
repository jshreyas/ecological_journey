import math
import os
from pathlib import Path
from typing import Optional

import httpx

PEERTUBE_URL: str = "https://makertube.net"
PEERTUBE_TOKEN: str = "be1d26c1147580eab185d328d879b808cef4b1f8"
CHUNK_SIZE_MB: int = 1  # 8MB per chunk


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
            # import pdb; pdb.set_trace()
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

    async def upload_resumable(self, file_path: Path, name: str, channel_id: int = 12177):
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
            # import pdb; pdb.set_trace()
            init_resp.raise_for_status()
            # upload_id = init_resp.json()["upload_id"]
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
                        # import pdb; pdb.set_trace()
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

    # async def upload_chunked(self, file_path: Path, name: str, channel_id: Optional[str] = 12177):
    #     """Chunked upload for large files (>2GB)."""

    #     file_size = os.path.getsize(file_path)
    #     chunk_size = CHUNK_SIZE_MB * 1024 * 1024
    #     num_chunks = math.ceil(file_size / chunk_size)

    #     async with httpx.AsyncClient() as client:
    #         with open(file_path, "rb") as f:
    #             for i in range(num_chunks):
    #                 chunk = f.read(chunk_size)
    #                 headers = {**self.headers,
    #                            "Content-Range": f"bytes {i*chunk_size}-{(i+1)*chunk_size-1}/{file_size}",
    #                            }
    #                 data = {"name": name}
    #                 if channel_id:
    #                     data["channelId"] = channel_id
    #                 files = {"videofile": (file_path.name, chunk, "video/mp4")}
    #                 r = await client.post(f"{self.base_url}/api/v1/videos/upload-resumable",
    #                                       headers=headers, data=data, files=files)
    #                 r.raise_for_status()
    #         return {"status": "uploaded", "name": name, "chunks": num_chunks}
