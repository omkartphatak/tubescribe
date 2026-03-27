import os
import re
import tempfile
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Configurable via .env or environment variables
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3.5-9b")


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS format."""
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def fetch_transcript(video_id: str, with_timestamps: bool = False) -> str:
    """Fetch transcript. Falls back to Whisper if YouTube captions unavailable."""
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        if with_timestamps:
            lines = [f"[{_format_timestamp(entry.start)}] {entry.text}" for entry in transcript.snippets]
            return "\n".join(lines)
        else:
            lines = [entry.text for entry in transcript.snippets]
            return " ".join(lines)
    except Exception:
        # Whisper fallback
        return whisper_transcribe(video_id, with_timestamps=with_timestamps)


def whisper_transcribe(video_id: str, with_timestamps: bool = False) -> str:
    """Download audio with yt-dlp and transcribe with Whisper locally."""
    try:
        import whisper
    except ImportError:
        raise RuntimeError(
            "No YouTube captions found and Whisper is not installed.\n"
            "Install it with: pip3 install openai-whisper\n"
            "Then try again."
        )

    url = f"https://www.youtube.com/watch?v={video_id}"
    tmp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(tmp_dir, "audio.mp3")

    # Download audio only
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": audio_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "64",
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Find the actual file (yt-dlp may add extension)
    actual_path = audio_path
    if not os.path.exists(actual_path):
        for f in os.listdir(tmp_dir):
            if f.startswith("audio"):
                actual_path = os.path.join(tmp_dir, f)
                break

    # Transcribe with Whisper (use "base" model for speed)
    # Workaround for SSL issues (VPN/proxy)
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    model = whisper.load_model("base")
    result = model.transcribe(actual_path)

    # Clean up
    try:
        os.remove(actual_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass

    if with_timestamps and result.get("segments"):
        lines = [f"[{_format_timestamp(seg['start'])}] {seg['text'].strip()}" for seg in result["segments"]]
        return "\n".join(lines)

    return result["text"]


def fetch_video_metadata(url: str) -> dict:
    """Fetch video title, channel name, and description from YouTube."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "title": info.get("title", "Unknown"),
            "channel": info.get("channel") or info.get("uploader") or "Unknown",
            "channel_url": info.get("channel_url") or info.get("uploader_url") or "",
            "url": info.get("webpage_url") or url,
            "description": info.get("description", ""),
            "duration": info.get("duration_string", ""),
            "view_count": info.get("view_count", 0),
            "upload_date": info.get("upload_date", ""),
            "thumbnail": info.get("thumbnail", ""),
        }


def fetch_playlist_urls(playlist_url: str) -> list[dict]:
    """Extract all video URLs and titles from a YouTube playlist."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        entries = info.get("entries", [])
        videos = []
        for entry in entries:
            if entry:
                videos.append({
                    "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                    "title": entry.get("title", "Unknown"),
                    "id": entry.get("id", ""),
                    "duration": entry.get("duration_string", ""),
                })
        return videos


def is_playlist_url(url: str) -> bool:
    """Check if a URL is a YouTube playlist."""
    return "list=" in url and ("playlist" in url or "list=" in url)


def identify_speakers(transcript: str, metadata: dict, client: OpenAI) -> str:
    """Use local LLM to identify speakers from transcript and metadata."""
    description = metadata.get("description", "")
    title = metadata.get("title", "")
    channel = metadata.get("channel", "")

    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": f"""Based on the video title, channel name, description, and transcript excerpt below, identify who is speaking in this video. List each speaker with a brief description (e.g. host, guest, interviewer). If it's a single person, just state who they are.

Title: {title}
Channel: {channel}
Description: {description[:1500]}

Transcript excerpt:
{transcript[:2000]}

Respond with ONLY a short list of speakers, no extra commentary. Example format:
- **Speaker Name** — Role/description""",
            }
        ],
    )
    return response.choices[0].message.content


def generate_tags(transcript: str, metadata: dict, client: OpenAI) -> list[str]:
    """Use local LLM to auto-generate topic tags for a video."""
    title = metadata.get("title", "")
    channel = metadata.get("channel", "")

    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": f"""Based on the video title, channel, and transcript excerpt, generate 3-6 short topic tags (1-2 words each) that categorize this video. Tags should be lowercase.

Title: {title}
Channel: {channel}

Transcript excerpt:
{transcript[:2000]}

Respond with ONLY a comma-separated list of tags, nothing else. Example: marketing, social media, growth strategy, branding""",
            }
        ],
    )
    msg = response.choices[0].message
    raw = (msg.content or "").strip()
    # Qwen3.5 puts answer in reasoning_content instead of content
    if not raw:
        reasoning = getattr(msg, "reasoning_content", "") or ""
        import re as _re
        # Strategy 1: find lines starting with "Selected:" or "Final:" that contain comma lists
        for line in reasoning.split("\n"):
            cleaned = line.strip()
            if _re.match(r'^(Selected|Final|Output|Result|Answer)[:\s]', cleaned, _re.IGNORECASE):
                after = _re.sub(r'^[^:]+:\s*', '', cleaned)
                if "," in after:
                    raw = after
                    break
        # Strategy 2: find the last standalone comma-separated tag list
        if not raw:
            candidates = []
            for line in reasoning.split("\n"):
                cleaned = line.strip().strip("*-•").strip()
                # Remove backticks
                cleaned = cleaned.replace("`", "")
                if "," in cleaned and len(cleaned) < 300:
                    parts = [p.strip().strip("\"'") for p in cleaned.split(",")]
                    if len(parts) >= 3 and all(0 < len(p) < 30 for p in parts):
                        # Check parts look like tags (short phrases, no colons/questions)
                        if not any("?" in p or ":" in p for p in parts):
                            candidates.append(cleaned)
            if candidates:
                raw = candidates[-1]
        # Strategy 3: extract numbered items like "1. reinforcement learning"
        if not raw:
            items = _re.findall(r'\d+\.\s*[`"\']*([a-z][a-z\s]+?)[`"\']*\s*(?:\(|$|\n)', reasoning.lower())
            if len(items) >= 3:
                raw = ", ".join(i.strip() for i in items[:6])
    # Parse comma-separated tags, clean up
    _junk = {"yes", "no", "ok", "okay", "sure", "none", "n/a", "tags", "tag", "answer", "output", "result"}
    tags = [t.strip().lower().strip(".-#*\"'`0123456789. ") for t in raw.split(",")]
    return [t for t in tags if t and len(t) < 30 and ":" not in t and t not in _junk and len(t) > 1]


def extract_key_quotes(transcript: str, metadata: dict, client: OpenAI) -> str:
    """Extract the most quotable/shareable lines from the transcript with timestamps."""
    title = metadata.get("title", "")
    channel = metadata.get("channel", "")
    has_timestamps = bool(re.search(r'\[\d{1,2}:\d{2}(:\d{2})?\]', transcript))

    timestamp_instruction = (
        "Include the timestamp in [MM:SS] or [HH:MM:SS] format before each quote."
        if has_timestamps
        else "Do NOT include timestamps since the transcript has none."
    )

    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        max_tokens=8192,
        messages=[
            {
                "role": "user",
                "content": f"""From the following YouTube video transcript, extract 5-10 of the most quotable, insightful, or shareable lines. Pick lines that are:
- Memorable or thought-provoking
- Contain a key insight, surprising fact, or strong opinion
- Could stand alone as a social media quote or highlight

{timestamp_instruction}

Format each quote as:
> "[exact quote from transcript]"
— {channel}, *{title}* [TIMESTAMP]

Title: {title}
Channel: {channel}

Transcript:
{truncate(transcript, 10000)}""",
            }
        ],
    )
    return (response.choices[0].message.content or "").strip()


def get_client(base_url: str = None) -> OpenAI:
    """Create an OpenAI client pointing at LM Studio."""
    return OpenAI(base_url=base_url or LM_STUDIO_URL, api_key="lm-studio")


def truncate(text: str, max_chars: int = 12000) -> str:
    """Truncate text to fit within model context limits."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Transcript truncated due to length...]"


ANALYSIS_PROMPTS = {
    "Quick Summary": """Give a brief summary of this YouTube video, then list the key takeaways. Keep it short — this is for someone in a hurry. Use the video title, description, and transcript together to produce an accurate analysis.

**Video Title:** {title}
**Channel:** {channel}
**Description:** {description}

1. **Summary** — 2-3 sentences covering what the video is about.
2. **Key Takeaways** — A bullet list (3-6 points) of the most important things to know.

Transcript:
{transcript}""",

    "Standard": """Analyze the following YouTube video and provide a comprehensive analysis. Use the video title, description, and transcript together to produce an accurate and well-contextualized analysis.

**Video Title:** {title}
**Channel:** {channel}
**Description:** {description}

1. **Summary** — A concise 2-3 paragraph summary of the video content.
2. **Key Points** — A bullet list of the most important points or takeaways.
3. **Main Themes** — The overarching themes or topics discussed.

Transcript:
{transcript}""",

    "Deep Dive": """Provide an in-depth analysis of the following YouTube video. Use the video title, description, and transcript together to produce a thorough, well-contextualized analysis.

**Video Title:** {title}
**Channel:** {channel}
**Description:** {description}

1. **Summary** — A detailed summary of the video content covering all major sections.
2. **Key Points** — A comprehensive bullet list of all important points, arguments, and takeaways.
3. **Main Themes** — The overarching themes or topics discussed, with explanation of how they connect.
4. **Notable Insights** — Interesting quotes, statistics, examples, or ideas mentioned.
5. **Structure & Flow** — How the video is organized and how ideas progress.
6. **Strengths & Gaps** — What the video covers well and what it might be missing.

Transcript:
{transcript}""",
}

DETAIL_LEVELS = list(ANALYSIS_PROMPTS.keys())


def analyze_transcript(transcript: str, client: OpenAI, detail_level: str = "Standard", metadata: dict = None) -> str:
    """Send transcript to local LLM for analysis at the chosen detail level."""
    metadata = metadata or {}
    prompt_template = ANALYSIS_PROMPTS.get(detail_level, ANALYSIS_PROMPTS["Standard"])
    prompt = prompt_template.format(
        transcript=truncate(transcript),
        title=metadata.get("title", "Unknown"),
        channel=metadata.get("channel", "Unknown"),
        description=truncate(metadata.get("description", ""), 2000),
    )

    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        max_tokens=16384,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def ask_question(
    transcript: str,
    question: str,
    chat_history: list[dict],
    client: OpenAI,
) -> str:
    """Answer a question about the transcript using conversation history."""
    system = f"""You are a helpful assistant that answers questions about a YouTube video.
Use the transcript below to answer questions accurately. If the answer isn't in the transcript, say so.

Transcript:
{truncate(transcript)}"""

    messages = [{"role": "system", "content": system}] + chat_history + [{"role": "user", "content": question}]

    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        max_tokens=8192,
        messages=messages,
    )
    return response.choices[0].message.content


def export_markdown(metadata: dict, transcript: str, analysis: str, speakers: str = None, key_quotes: str = None) -> str:
    """Generate a Markdown document with all video data."""
    title = metadata.get("title", "Unknown")
    channel = metadata.get("channel", "Unknown")
    url = metadata.get("url", "")
    duration = metadata.get("duration", "")
    view_count = metadata.get("view_count", 0)
    upload_date = metadata.get("upload_date", "")

    if upload_date:
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"

    view_str = f"{view_count:,}" if view_count else ""

    md = f"""# {title}

**Channel:** {channel}
**URL:** {url}
**Duration:** {duration} | **Views:** {view_str} | **Uploaded:** {upload_date}

---
"""

    if speakers:
        md += f"""
## Speakers

{speakers}

---
"""

    if key_quotes:
        md += f"""
## Key Quotes

{key_quotes}

---
"""

    md += f"""
## Analysis

{analysis}

---

## Transcript

{transcript}

---

*Generated by TubeScribe*
"""
    return md
