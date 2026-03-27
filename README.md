# TubeScribe

100% local YouTube transcript scraper and analyzer. Extract, read, and analyze YouTube transcripts — powered by local AI.

## Features

- **Transcript Extraction** — Fetch transcripts from any YouTube video or playlist. Falls back to Whisper for videos without captions.
- **AI-Powered Analysis** — Three detail levels (Quick Summary, Standard, Deep Dive) using a local LLM via LM Studio.
- **Key Quotes Extraction** — Automatically pulls out the most quotable/shareable lines with timestamps.
- **Speaker Identification** — Detects speakers in interviews and multi-person videos.
- **Searchable Library** — SQLite + FTS5 full-text search across all saved transcripts and insights.
- **Auto-Tagging** — LLM-generated topic tags for every video.
- **Collections** — Organize videos into custom groups (e.g. "Tech Talks", "Marketing").
- **Playlist Support** — Batch-process entire playlists with progress tracking.
- **Q&A Chat** — Ask follow-up questions about any video's content.
- **Export** — Copy analysis or download as Markdown.

## Tech Stack

- **Frontend:** Streamlit
- **LLM:** Qwen3.5-9B via LM Studio (localhost:1234)
- **Database:** SQLite with FTS5
- **Transcription:** youtube-transcript-api + Whisper fallback
- **Metadata:** yt-dlp

## Setup

1. Install [LM Studio](https://lmstudio.ai/) and load `qwen/qwen3.5-9b`
2. Start the LM Studio local server on port 1234
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the app:

```bash
streamlit run app.py
```

## Project Structure

```
app.py              — Streamlit web UI
transcript_agent.py — Core logic: transcript fetching, LLM analysis, quotes, tags
database.py         — SQLite persistence layer with FTS5 search
cli.py              — CLI interface
batch_fetch.py      — Batch transcript fetching
analyze_batch.py    — Batch analysis
generate_report.py  — Report generation
whisper_batch.py    — Batch Whisper transcription
```

## License

MIT
