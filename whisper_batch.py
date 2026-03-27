"""Fetch transcripts via Whisper for videos without YouTube captions.
Optimized: uses whisper 'tiny' model for speed, processes sequentially.
"""
import os
import time
import tempfile
import ssl
import yt_dlp
from database import save_video, get_video, count_videos

# Fix SSL for VPN/proxy
ssl._create_default_https_context = ssl._create_unverified_context

CHANNEL_VIDEOS = "https://www.youtube.com/@starterstory/videos"

# Load whisper model once
import whisper
print("Loading Whisper model (tiny)...")
WHISPER_MODEL = whisper.load_model("tiny")
print("Model loaded.\n")


def get_all_video_ids():
    ydl_opts = {"quiet": True, "skip_download": True, "no_warnings": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_VIDEOS, download=False)
        return [
            {"id": e.get("id", ""), "title": e.get("title", "")}
            for e in info.get("entries", []) if e
        ]


def whisper_transcribe(video_id):
    """Download audio and transcribe with Whisper tiny model."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    tmp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(tmp_dir, "audio.mp3")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "worstaudio/worst",  # smallest file for speed
        "outtmpl": audio_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "32",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Find the actual file
    actual_path = audio_path
    if not os.path.exists(actual_path):
        for f in os.listdir(tmp_dir):
            if f.startswith("audio"):
                actual_path = os.path.join(tmp_dir, f)
                break

    result = WHISPER_MODEL.transcribe(actual_path)

    # Cleanup
    try:
        os.remove(actual_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass

    return result["text"]


def fetch_metadata_fast(video_id, fallback_title=""):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", fallback_title),
                "channel": info.get("channel") or "Starter Story",
                "channel_url": info.get("channel_url") or "",
                "url": info.get("webpage_url") or url,
                "description": info.get("description", ""),
                "duration": info.get("duration_string", ""),
                "view_count": info.get("view_count", 0),
                "upload_date": info.get("upload_date", ""),
                "thumbnail": info.get("thumbnail", ""),
            }
    except Exception:
        return {"title": fallback_title, "channel": "Starter Story", "url": url}


def main():
    print("Fetching video list...")
    videos = get_all_video_ids()

    # Filter to only those not yet in DB
    to_process = []
    for v in videos:
        existing = get_video(v["id"])
        if not existing or not existing.get("transcript"):
            to_process.append(v)

    print(f"Total videos: {len(videos)}, Need Whisper: {len(to_process)}\n")

    ok = 0
    err = 0
    for i, video in enumerate(to_process):
        try:
            print(f"[{i+1}/{len(to_process)}] Transcribing: {video['title'][:60]}...", flush=True)
            transcript = whisper_transcribe(video["id"])
            metadata = fetch_metadata_fast(video["id"], video["title"])
            url = f"https://www.youtube.com/watch?v={video['id']}"
            save_video(video["id"], url, metadata, transcript, None, None, None)
            ok += 1
            print(f"  -> OK ({len(transcript)} chars)")
        except Exception as e:
            err += 1
            print(f"  -> ERROR: {e}")

    print(f"\nDone! OK={ok}, Errors={err}, Total in library: {count_videos()}")


if __name__ == "__main__":
    main()
