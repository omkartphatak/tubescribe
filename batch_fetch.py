"""Batch fetch all Starter Story video transcripts and save to tubescribe library.
Uses only YouTube captions API (no Whisper fallback) for speed. Skips shorts.
"""
import time
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from database import save_video, get_video, count_videos

CHANNEL_VIDEOS = "https://www.youtube.com/@starterstory/videos"


def get_all_video_ids():
    """Get all video IDs and titles from channel videos tab."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "extract_flat": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_VIDEOS, download=False)
        entries = info.get("entries", [])
        return [
            {"id": e.get("id", ""), "title": e.get("title", ""), "duration": e.get("duration", "")}
            for e in entries if e
        ]


def fetch_transcript_fast(video_id):
    """Fetch transcript using only YouTube captions API (fast, no Whisper)."""
    ytt_api = YouTubeTranscriptApi()
    transcript = ytt_api.fetch(video_id)
    lines = [entry.text for entry in transcript.snippets]
    return " ".join(lines)


def fetch_metadata_fast(video_id, fallback_title=""):
    """Fetch metadata using yt-dlp."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", fallback_title),
                "channel": info.get("channel") or info.get("uploader") or "Starter Story",
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


def fetch_and_save(video):
    """Fetch transcript + metadata for one video and save to DB."""
    vid_id = video["id"]

    # Skip if already in DB with transcript
    existing = get_video(vid_id)
    if existing and existing.get("transcript"):
        return "skip"

    url = f"https://www.youtube.com/watch?v={vid_id}"

    # Fetch transcript (captions only, no Whisper)
    try:
        transcript = fetch_transcript_fast(vid_id)
    except Exception:
        return "no_captions"

    # Fetch metadata
    metadata = fetch_metadata_fast(vid_id, video["title"])

    # Save to DB
    save_video(vid_id, url, metadata, transcript, None, None, None)
    return "ok"


def main():
    print("=" * 60)
    print("STARTER STORY — BATCH TRANSCRIPT FETCH (videos only)")
    print("=" * 60)

    print("\nFetching video list...")
    videos = get_all_video_ids()
    print(f"Found {len(videos)} videos to process\n")

    results = {"ok": 0, "skip": 0, "no_captions": 0}

    for i, video in enumerate(videos):
        status = fetch_and_save(video)
        results[status if status in results else "no_captions"] += 1
        label = {"ok": "OK  ", "skip": "SKIP", "no_captions": "NOCAP"}
        print(f"[{i+1}/{len(videos)}] {label.get(status, 'ERR ')} {video['title'][:65]}")

        if status == "ok":
            time.sleep(0.3)

    print(f"\n{'=' * 60}")
    print(f"OK={results['ok']}, Skipped={results['skip']}, NoCaptions={results['no_captions']}")
    print(f"Total in library: {count_videos()}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
