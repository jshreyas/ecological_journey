import math
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import httpx
import requests
from nicegui import ui

PEERTUBE_URL: str = "https://makertube.net"
PEERTUBE_TOKEN: str = "67ee8bd680cab0b36c09be3b52bfa9c75172b422"
CHUNK_SIZE_MB: int = 50  # 50MB per chunk


class PeerTubeClient:
    """Lightweight client for PeerTube REST API."""

    def __init__(self, base_url: str = None, token: str = None):
        self.base_url = base_url or PEERTUBE_URL.rstrip("/")
        self.token = token or PEERTUBE_TOKEN
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.log = None

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
        # TODO: handle pagination
        # TODO: handle 429 rate limits
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.base_url}/api/v1/video-playlists/{playlist_id}/videos", headers=self.headers)
            res.raise_for_status()
            return res.json()

    async def get_playlist_videos(self, playlist_id: str):
        """
        Fetch videos from a playlist.

        If a video is still transcoding, it will return None for the HLS URL.
        Final URL can be fetched later in a sync step.
        """
        videos = []
        playlist_videos = await self._get_playlist_videos(playlist_id)

        for each in playlist_videos["data"]:
            # TODO: dont fetch for videos which are already published
            hls_info = await self.get_video(each["video"]["uuid"])
            video_state = hls_info.get("state", {}).get("label", "").lower()
            streaming_playlists = hls_info.get("streamingPlaylists", [])

            if video_state == "published" and streaming_playlists:
                hls_url = streaming_playlists[0].get("playlistUrl")  # latest playlist
            else:
                hls_url = None  # transcoding not finished
                print(f"⚠️ Video {each['video']['uuid']} is still {video_state}, HLS URL not ready yet.")
                break

            print(f"Video {each['video']['uuid']} state: {video_state}, HLS URL: {hls_url}")

            try:
                video_data = {
                    "title": each["video"]["name"],
                    "video_id": f'{each["video"]["id"]}',
                    "youtube_url": hls_url,  # will be None if not ready
                    "date": each["video"]["publishedAt"].replace("Z", "+00:00"),
                    "type": "",
                    "partners": [],
                    "positions": [],
                    "notes": "",
                    "labels": [],
                    "clips": [],
                    "duration_seconds": each["video"]["duration"],
                }
                videos.append(video_data)
            except Exception as exc:
                print(f"❌ Error processing video {each['video']['uuid']}: {exc}")

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
        channel_id: int = 12187,
        file_input_name: str = "uploaded_file.mp4",
        on_progress=None,
    ):
        import asyncio
        import math
        import os
        import time

        import httpx

        # 🌱 Create a live upload log UI
        if not self.log:
            self.log = ui.log().classes("w-full h-64 bg-black text-primary p-2 font-mono text-xs overflow-y-auto")
        self.log.push(f"🚀 Starting upload: {name}")

        try:
            # Determine file details
            if hasattr(file_input, "read"):
                file_obj = file_input
                file_obj.seek(0, os.SEEK_END)
                file_size = file_obj.tell()
                file_obj.seek(0)
                file_name = file_input_name
            else:
                file_obj = open(file_input, "rb")
                file_size = os.path.getsize(file_input)
                file_name = os.path.basename(file_input)

            chunk_size = CHUNK_SIZE_MB * 1024 * 1024
            num_chunks = math.ceil(file_size / chunk_size)
            headers = {"Authorization": f"Bearer {self.token}"}
            timeout = httpx.Timeout(800.0, read=800.0, write=800.0)

            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
                self.log.push(f"Initializing upload for {file_name} ({file_size/1024/1024:.2f} MB)...")
                init_body = {"channelId": channel_id, "filename": file_name, "name": name, "privacy": "1"}
                init_headers = {
                    **headers,
                    "X-Upload-Content-Length": str(file_size),
                    "X-Upload-Content-Type": "video/mp4",
                }

                init_resp = await client.post(
                    f"{self.base_url}/api/v1/videos/upload-resumable",
                    headers=init_headers,
                    data=init_body,
                )
                init_resp.raise_for_status()
                chunk_url = init_resp.headers["location"]
                self.log.push(f"✅ Initialized upload: {chunk_url}")

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

                    for attempt in range(10):
                        try:
                            t0 = time.monotonic()
                            res = await client.put(chunk_url, headers=put_headers, content=chunk)
                            elapsed = time.monotonic() - t0
                            if res.status_code in (200, 201, 308):
                                self.log.push(
                                    f"📦 Chunk {i+1}/{num_chunks} accepted ({uploaded_bytes/file_size*100:.1f}%) [{elapsed:.2f}s]"
                                )
                                break
                            else:
                                self.log.push(f"⚠️ Chunk {i+1} failed ({res.status_code}), retrying... [{elapsed:.2f}s]")
                        except httpx.ReadError:
                            self.log.push(f"❌ ReadError on chunk {i+1}, retrying... [{elapsed:.2f}s]")
                        await asyncio.sleep(2**attempt)
                    else:
                        self.log.push(f"💀 Chunk {i+1} failed after 10 retries.")
                        raise RuntimeError("Chunk upload failed after 10 retries")

                    uploaded_bytes += len(chunk)
                    if on_progress:
                        await on_progress(uploaded_bytes, file_size)

                    if res.status_code in (200, 201):
                        self.log.push(f"🎉 Upload complete for {name}")
                        return res.json()

            self.log.push("⚠️ Upload did not complete cleanly — check PeerTube logs.")
        except Exception as exc:
            self.log.push(f"❌ Upload failed: {exc}")
            raise

    async def get_hls_clip(
        self,
        start_sec: float = 20.0,
        end_sec: float = 30.0,
        prefer_resolution: str | None = None,
        timeout: int = 10,
        debug: bool = True,
    ):
        """
        Build a valid mini HLS variant playlist containing only the segments
        that cover [start_sec, end_sec).
        Returns a single HLS playlist string (for direct playback).
        """

        master_or_variant_url = (
            "https://makertube01.fsn1.your-objectstorage.com/"
            "streaming-playlists/hls/301d79c9-6a39-4d9e-8676-3e994a22d44d/"
            "9152a582-6d86-4a6d-95d3-0b91a2feded0-master.m3u8"
        )

        if end_sec <= start_sec:
            raise ValueError("end_sec must be > start_sec")

        def log(*a):
            if debug:
                print("[get_hls_clip]", *a)

        # --- Fetch master or variant ---
        log(f"Fetching: {master_or_variant_url}")
        r = requests.get(master_or_variant_url, timeout=timeout)
        r.raise_for_status()
        lines = [ln.strip() for ln in r.text.splitlines() if ln.strip()]

        # --- If master, choose one variant ---
        if any("#EXT-X-STREAM-INF" in ln for ln in lines):
            variants = []
            for i, ln in enumerate(lines):
                if ln.startswith("#EXT-X-STREAM-INF"):
                    m_res = re.search(r"RESOLUTION=(\d+x\d+)", ln)
                    m_bw = re.search(r"BANDWIDTH=(\d+)", ln)
                    if i + 1 < len(lines):
                        variants.append(
                            {
                                "uri": lines[i + 1],
                                "res": m_res.group(1) if m_res else None,
                                "bw": int(m_bw.group(1)) if m_bw else None,
                            }
                        )
            if not variants:
                raise RuntimeError("No variants found")

            chosen = None
            if prefer_resolution:
                for v in variants:
                    if prefer_resolution in (v["res"] or ""):
                        chosen = v
                        break
            if not chosen:
                chosen = max(variants, key=lambda v: v["bw"] or 0)

            variant_url = (
                chosen["uri"] if chosen["uri"].startswith("http") else urljoin(master_or_variant_url, chosen["uri"])
            )

            log(f"Chosen variant: {variant_url}")
            vr = requests.get(variant_url, timeout=timeout)
            vr.raise_for_status()
            lines = [ln.strip() for ln in vr.text.splitlines() if ln.strip()]
            base_url = variant_url.rsplit("/", 1)[0] + "/"
        else:
            base_url = master_or_variant_url.rsplit("/", 1)[0] + "/"

        # --- Parse variant ---
        ext_x_map = None
        segments = []
        seq = 0
        total = 0.0
        # _current_range = None

        for i, ln in enumerate(lines):
            if ln.startswith("#EXT-X-MAP"):
                m = re.search(r'URI="([^"]+)"', ln)
                if m:
                    ext_x_map = urljoin(base_url, m.group(1))
            elif ln.startswith("#EXT-X-BYTERANGE"):
                _ = ln.split(":", 1)[1].strip()
            elif ln.startswith("#EXTINF"):
                try:
                    dur = float(ln.split(":")[1].split(",")[0])
                except Exception:
                    dur = 0
                byterange = None
                if i + 1 < len(lines) and lines[i + 1].startswith("#EXT-X-BYTERANGE"):
                    byterange = lines[i + 1].split(":")[1].strip()
                    uri = lines[i + 2]
                    # skip = 2
                else:
                    uri = lines[i + 1]
                    # skip = 1
                segments.append(
                    {
                        "uri": urljoin(base_url, uri),
                        "duration": dur,
                        "index": seq,
                        "start": total,
                        "end": total + dur,
                        "byterange": byterange,
                    }
                )
                seq += 1
                total += dur

        if not segments:
            raise RuntimeError("No media segments found")

        # --- Select relevant segments ---
        chosen = [s for s in segments if s["end"] > start_sec and s["start"] < end_sec]
        if not chosen:
            raise RuntimeError("No overlapping segments")

        # --- Build final HLS playlist ---
        new_pl = [
            "#EXTM3U",
            "#EXT-X-VERSION:3",
            f"#EXT-X-TARGETDURATION:{math.ceil(max(s['duration'] for s in chosen))}",
            f"#EXT-X-MEDIA-SEQUENCE:{chosen[0]['index']}",
        ]

        if ext_x_map:
            new_pl.append(f'#EXT-X-MAP:URI="{ext_x_map}"')

        for seg in chosen:
            new_pl.append(f"#EXTINF:{seg['duration']:.3f},")
            if "byterange" in seg and seg["byterange"]:
                new_pl.append(f"#EXT-X-BYTERANGE:{seg['byterange']}")
            new_pl.append(seg["uri"])

        new_pl.append("#EXT-X-ENDLIST")

        log(f"Built playlist with {len(chosen)} segments ({chosen[0]['start']:.1f}s → {chosen[-1]['end']:.1f}s)")
        log(new_pl)
        return "\n".join(new_pl)
