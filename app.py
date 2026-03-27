import re
import streamlit as st
from transcript_agent import (
    extract_video_id, fetch_transcript, analyze_transcript,
    ask_question, get_client, fetch_video_metadata, identify_speakers,
    fetch_playlist_urls, is_playlist_url, export_markdown,
    generate_tags, extract_key_quotes, DETAIL_LEVELS,
)
from database import (
    save_video, search_videos, list_all_videos, get_video, delete_video, count_videos,
    save_tags, get_tags, get_all_tags, get_videos_by_tag,
    create_collection, delete_collection, add_to_collection, remove_from_collection,
    list_collections, get_collection_videos, get_video_collections,
    save_key_quotes, get_key_quotes,
)

st.set_page_config(page_title="TubeScribe", page_icon="https://em-content.zobj.net/source/apple/391/pen_1f58a-fe0f.png", layout="wide")

# --- Custom CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Global */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Hero header */
.hero {
    text-align: center;
    padding: 1.5rem 0 1rem 0;
}
.hero h1 {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #FF0050, #FF4D8D, #7C3AED);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
    letter-spacing: -0.5px;
}
.hero p {
    color: #888;
    font-size: 1.05rem;
    margin-top: 0;
}

/* Section headers */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: 1.5rem 0 0.75rem 0;
    font-size: 1.3rem;
    font-weight: 700;
    color: #E0E0E0;
}
.section-header .icon {
    font-size: 1.4rem;
}

/* Transcript box */
div[data-testid="stTextArea"] textarea {
    background: #1A1A2E !important;
    border: 1px solid #2A2A4A !important;
    border-radius: 12px !important;
    color: #D0D0D0 !important;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.85rem !important;
    line-height: 1.6 !important;
    padding: 1rem !important;
}

/* Analysis card */
.analysis-card {
    background: #1A1A2E;
    border: 1px solid #2A2A4A;
    border-radius: 12px;
    padding: 1.5rem;
    margin: 0.75rem 0;
}

/* Video info card */
.video-info {
    background: #1A1A2E;
    border: 1px solid #2A2A4A;
    border-radius: 12px;
    padding: 1.25rem;
    margin: 0.75rem 0;
}
.video-info .video-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: #E0E0E0;
    margin-bottom: 0.4rem;
}
.video-info .video-channel {
    font-size: 0.95rem;
    color: #FF4D8D;
    font-weight: 600;
    margin-bottom: 0.5rem;
}
.video-info .video-meta {
    font-size: 0.8rem;
    color: #888;
}
.video-info .video-meta span {
    margin-right: 1rem;
}

/* Sidebar text input */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input {
    border: 1.5px solid #3A3A5A !important;
    border-radius: 8px !important;
    background: #12121F !important;
    color: #E0E0E0 !important;
    padding: 0.6rem 0.75rem !important;
}
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input:focus {
    border-color: #FF4D8D !important;
    box-shadow: 0 0 0 1px #FF4D8D !important;
}
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input::placeholder {
    color: #666 !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: #0E0E1A;
    border-right: 1px solid #1E1E3A;
}
section[data-testid="stSidebar"] .stMarkdown h2 {
    color: #FF4D8D;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}

/* Buttons */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #FF0050, #7C3AED) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px;
    transition: opacity 0.2s;
}
div.stButton > button[kind="primary"]:hover {
    opacity: 0.85;
}

/* Chat messages */
div[data-testid="stChatMessage"] {
    border-radius: 12px !important;
    border: 1px solid #2A2A4A !important;
    margin-bottom: 0.5rem;
}

/* Divider */
hr {
    border-color: #2A2A4A !important;
}

/* Badge */
.badge {
    display: inline-block;
    background: #1A1A2E;
    border: 1px solid #2A2A4A;
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.75rem;
    color: #888;
    margin-top: 0.5rem;
}

/* Speakers card */
.speakers-card {
    background: #1A1A2E;
    border: 1px solid #2A2A4A;
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin: 0.5rem 0;
}

/* Playlist item */
.playlist-item {
    background: #1A1A2E;
    border: 1px solid #2A2A4A;
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin: 0.5rem 0;
}
.playlist-item .pl-title {
    font-weight: 600;
    color: #E0E0E0;
    font-size: 1rem;
    margin-bottom: 0.3rem;
}
.playlist-item .pl-summary {
    color: #B0B0B0;
    font-size: 0.85rem;
    line-height: 1.5;
}

/* Library items */
.lib-item {
    background: #12121F;
    border: 1px solid #2A2A4A;
    border-radius: 8px;
    padding: 0.6rem 0.75rem;
    margin: 0.3rem 0;
    cursor: pointer;
    transition: border-color 0.2s;
}
.lib-item:hover {
    border-color: #FF4D8D;
}
.lib-item .lib-title {
    font-size: 0.8rem;
    font-weight: 600;
    color: #D0D0D0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.lib-item .lib-channel {
    font-size: 0.7rem;
    color: #888;
}

/* Key quotes */
.quotes-card {
    background: #1A1A2E;
    border: 1px solid #2A2A4A;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin: 0.75rem 0;
}
.quotes-card blockquote {
    border-left: 3px solid #FF4D8D;
    padding-left: 1rem;
    margin: 1rem 0;
    color: #D0D0D0;
    font-style: italic;
}

/* Tag badges */
.tag-badge {
    display: inline-block;
    background: #1A1A2E;
    border: 1px solid #7C3AED;
    border-radius: 20px;
    padding: 0.2rem 0.65rem;
    font-size: 0.75rem;
    color: #BB86FC;
    margin: 0.15rem 0.2rem;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# --- Hero ---
st.markdown("""
<div class="hero">
    <h1>TubeScribe</h1>
    <p>Extract, read, and analyze YouTube transcripts — powered by local AI</p>
</div>
""", unsafe_allow_html=True)

# Initialize LM Studio client
client = get_client()

# Session state
for key, default in {
    "transcript": None,
    "analysis": None,
    "metadata": None,
    "speakers": None,
    "chat_history": [],
    "messages": [],
    "playlist_results": None,
    "key_quotes": None,
    "auto_analyze": False,
    "auto_analyze_detail": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Sidebar ---
with st.sidebar:
    st.markdown("## TubeScribe")
    st.caption("100% local. 100% free.")
    st.markdown("---")
    if "last_url" not in st.session_state:
        st.session_state.last_url = ""
    url = st.text_input("YouTube URL", placeholder="Paste link here", label_visibility="visible")
    with_timestamps = st.toggle("Include timestamps", value=False)
    st.markdown("#### Analysis Detail")
    detail_level = st.radio(
        "Detail level",
        DETAIL_LEVELS,
        index=1,
        label_visibility="collapsed",
        horizontal=True,
    )
    fetch_btn = st.button("Get Insights", type="primary", use_container_width=True)

    # Auto-fetch when URL changes (no need to press a separate button)
    # Skip if we just loaded a video from the library
    url_changed = url and url != st.session_state.last_url
    if url_changed and not st.session_state.get("loaded_from_library"):
        fetch_btn = True
        st.session_state.last_url = url
    st.session_state.loaded_from_library = False

    if st.button("Clear", use_container_width=True):
        for key in ["transcript", "analysis", "metadata", "speakers", "playlist_results", "key_quotes"]:
            st.session_state[key] = None
        st.session_state.chat_history = []
        st.session_state.messages = []
        st.session_state.last_url = ""
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="badge">Qwen3.5 via LM Studio</div>', unsafe_allow_html=True)

    # --- Library ---
    st.markdown("---")
    lib_count = count_videos()
    st.markdown(f"## Library ({lib_count})")
    lib_search = st.text_input("Search library", placeholder="Search saved videos...", label_visibility="collapsed", key="lib_search")

    # Filter by tag
    all_tags = get_all_tags()
    tag_options = ["All"] + [f"{t['tag']} ({t['count']})" for t in all_tags]
    if "lib_tag_filter" not in st.session_state:
        st.session_state.lib_tag_filter = "All"
    selected_tag_option = st.selectbox("Filter by tag", tag_options, index=0, label_visibility="collapsed", key="tag_filter_select")

    # Filter by collection
    all_colls = list_collections()
    coll_options = ["All"] + [f"{c['name']} ({c['video_count']})" for c in all_colls]
    selected_coll_option = st.selectbox("Filter by collection", coll_options, index=0, label_visibility="collapsed", key="coll_filter_select")

    # Determine which videos to show
    if lib_search:
        try:
            lib_videos = search_videos(lib_search)
        except Exception:
            lib_videos = []
    elif selected_tag_option != "All":
        tag_name = selected_tag_option.rsplit(" (", 1)[0]
        lib_videos = get_videos_by_tag(tag_name)
    elif selected_coll_option != "All":
        coll_name = selected_coll_option.rsplit(" (", 1)[0]
        coll_match = next((c for c in all_colls if c["name"] == coll_name), None)
        lib_videos = get_collection_videos(coll_match["id"]) if coll_match else []
    else:
        lib_videos = list_all_videos()

    for lv in lib_videos[:15]:
        if st.button(f"📄 {lv['title'][:40]}", key=f"lib_{lv['video_id']}", use_container_width=True):
            saved = get_video(lv["video_id"])
            if saved:
                st.session_state.metadata = {
                    "title": saved["title"],
                    "channel": saved["channel"],
                    "channel_url": saved.get("channel_url", ""),
                    "url": saved["url"],
                    "description": saved.get("description", ""),
                    "duration": saved.get("duration", ""),
                    "view_count": saved.get("view_count"),
                    "upload_date": saved.get("upload_date", ""),
                    "thumbnail": saved.get("thumbnail", ""),
                }
                st.session_state.transcript = saved["transcript"]
                st.session_state.analysis = saved["analysis"]
                st.session_state.speakers = saved.get("speakers")
                st.session_state.key_quotes = saved.get("key_quotes")
                st.session_state.playlist_results = None
                st.session_state.chat_history = []
                st.session_state.messages = []
                st.session_state.last_url = saved["url"]
                st.session_state.loaded_from_library = True
                st.rerun()

    # --- Collections management ---
    with st.expander("Manage Collections"):
        new_coll_name = st.text_input("New collection", placeholder="e.g. Tech Talks", key="new_coll_input", label_visibility="collapsed")
        if st.button("Create", key="create_coll_btn") and new_coll_name.strip():
            create_collection(new_coll_name.strip())
            st.rerun()
        for c in all_colls:
            col_a, col_b = st.columns([4, 1])
            col_a.caption(f"{c['name']} ({c['video_count']})")
            if col_b.button("x", key=f"del_coll_{c['id']}"):
                delete_collection(c["id"])
                st.rerun()

# --- Fetch Transcript + Metadata ---
if fetch_btn and url:
    # Check if playlist
    if is_playlist_url(url):
        try:
            with st.spinner("Fetching playlist videos..."):
                videos = fetch_playlist_urls(url)
            st.session_state.playlist_results = []
            st.session_state.transcript = None
            st.session_state.analysis = None
            st.session_state.metadata = None
            st.session_state.speakers = None

            progress = st.progress(0, text="Processing playlist...")
            for i, video in enumerate(videos):
                progress.progress((i + 1) / len(videos), text=f"Processing {i + 1}/{len(videos)}: {video['title'][:50]}...")
                try:
                    vid_id = video["id"] or extract_video_id(video["url"])
                    transcript = fetch_transcript(vid_id, with_timestamps=False)
                    pl_meta = {"title": video["title"], "channel": "", "duration": video.get("duration", "")}
                    analysis = analyze_transcript(transcript, client, detail_level, metadata=pl_meta)
                    st.session_state.playlist_results.append({
                        "title": video["title"],
                        "url": video["url"],
                        "duration": video.get("duration", ""),
                        "transcript": transcript,
                        "analysis": analysis,
                    })
                    # Auto-save each playlist video to library + auto-tag
                    save_video(vid_id, video["url"], pl_meta, transcript, None, analysis, detail_level)
                    try:
                        tags = generate_tags(transcript, pl_meta, client)
                        save_tags(vid_id, tags)
                    except Exception:
                        pass
                except Exception as e:
                    st.session_state.playlist_results.append({
                        "title": video["title"],
                        "url": video["url"],
                        "duration": video.get("duration", ""),
                        "transcript": None,
                        "analysis": f"Error: {e}",
                    })
            progress.empty()

        except Exception as e:
            st.error(f"Error: {e}")
    else:
        # Single video
        try:
            video_id = extract_video_id(url)
            with st.spinner("Fetching video info & transcript..."):
                metadata = fetch_video_metadata(url)
                st.session_state.metadata = metadata
                transcript = fetch_transcript(video_id, with_timestamps=with_timestamps)
                st.session_state.transcript = transcript
            st.session_state.analysis = None
            st.session_state.speakers = None
            st.session_state.key_quotes = None
            st.session_state.playlist_results = None
            st.session_state.chat_history = []
            st.session_state.messages = []

            # Identify speakers
            with st.spinner("Identifying speakers..."):
                try:
                    speakers = identify_speakers(transcript, metadata, client)
                    st.session_state.speakers = speakers
                except Exception:
                    st.session_state.speakers = None

            # Schedule auto-analyze on next rerun so transcript renders first
            st.session_state.auto_analyze = True
            st.session_state.auto_analyze_detail = detail_level
            st.rerun()

        except Exception as e:
            st.error(f"Error: {e}")

# =============================================
# PLAYLIST MODE
# =============================================
if st.session_state.playlist_results:
    st.markdown('<div class="section-header"><span class="icon">📋</span> Playlist Results</div>', unsafe_allow_html=True)
    st.caption(f"{len(st.session_state.playlist_results)} videos processed")

    # Export entire playlist as one markdown
    all_md = "# Playlist Analysis\n\n---\n\n"
    for r in st.session_state.playlist_results:
        all_md += f"## {r['title']}\n\n**URL:** {r['url']}\n\n{r['analysis']}\n\n---\n\n"

    st.download_button(
        "📥 Download All as Markdown",
        data=all_md,
        file_name="playlist_analysis.md",
        mime="text/markdown",
        key="dl_playlist_md",
    )

    for idx, result in enumerate(st.session_state.playlist_results):
        with st.expander(f"**{idx + 1}.** {result['title']}", expanded=(idx == 0)):
            st.caption(f"{result.get('duration', '')} | [Open Video]({result['url']})")
            st.markdown(result["analysis"])
            if result.get("transcript"):
                with st.expander("Transcript"):
                    st.text(result["transcript"][:5000])

# =============================================
# SINGLE VIDEO MODE
# =============================================
elif st.session_state.transcript:

    # --- Video Info Card ---
    if st.session_state.metadata:
        meta = st.session_state.metadata
        view_str = f"{meta['view_count']:,}" if meta.get("view_count") else ""
        upload_str = ""
        if meta.get("upload_date"):
            d = meta["upload_date"]
            upload_str = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

        channel_name = meta.get('channel', 'Unknown')
        channel_url = meta.get('channel_url', '')
        video_url = meta.get('url', '')
        channel_html = f'<a href="{channel_url}" target="_blank" style="color:#FF4D8D;text-decoration:none;">{channel_name}</a>' if channel_url else channel_name

        st.markdown(f"""
        <div class="video-info">
            <div class="video-title">{meta.get('title', '')}</div>
            <div class="video-channel">{channel_html}</div>
            <div class="video-meta">
                <span>{meta.get('duration', '')}</span>
                <span>{view_str} views</span>
                <span>{upload_str}</span>
            </div>
            <div style="margin-top:0.5rem;font-size:0.8rem;">
                <a href="{video_url}" target="_blank" style="color:#7C3AED;text-decoration:none;">🔗 {video_url}</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- Tags & Collections ---
    if st.session_state.metadata and st.session_state.metadata.get("url"):
        current_vid_id = extract_video_id(st.session_state.metadata["url"])
        video_tags = get_tags(current_vid_id)
        if video_tags:
            tags_html = " ".join(f'<span class="tag-badge">{t}</span>' for t in video_tags)
            st.markdown(f'<div style="margin:0.5rem 0;">{tags_html}</div>', unsafe_allow_html=True)

        # Collection management for this video
        vid_colls = get_video_collections(current_vid_id)
        all_colls_list = list_collections()
        if all_colls_list:
            vid_coll_ids = {c["id"] for c in vid_colls}
            available = [c for c in all_colls_list if c["id"] not in vid_coll_ids]
            if vid_colls:
                coll_names = ", ".join(c["name"] for c in vid_colls)
                st.caption(f"In collections: {coll_names}")
            if available:
                col_add, col_btn = st.columns([3, 1])
                with col_add:
                    add_coll = st.selectbox(
                        "Add to collection",
                        options=[c["name"] for c in available],
                        label_visibility="collapsed",
                        key="add_to_coll_select",
                    )
                with col_btn:
                    if st.button("Add", key="add_to_coll_btn"):
                        match = next((c for c in available if c["name"] == add_coll), None)
                        if match:
                            add_to_collection(match["id"], current_vid_id)
                            st.rerun()

    # --- Speakers ---
    if st.session_state.speakers:
        st.markdown('<div class="section-header"><span class="icon">🎙️</span> Speakers</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="speakers-card">{st.session_state.speakers}</div>', unsafe_allow_html=True)

    # --- Video Description (collapsed) ---
    if st.session_state.metadata and st.session_state.metadata.get("description"):
        with st.expander("Video Description"):
            st.text(st.session_state.metadata["description"][:2000])

    # --- Transcript (collapsed) ---
    char_count = len(st.session_state.transcript)
    word_count = len(st.session_state.transcript.split())
    with st.expander(f"📝 Transcript  —  {word_count:,} words  |  {char_count:,} characters"):
        line_count = st.session_state.transcript.count("\n") + len(st.session_state.transcript) // 80
        height = min(max(line_count * 20, 150), 500)
        st.text_area("transcript_raw", st.session_state.transcript, height=height, label_visibility="collapsed", disabled=True)

    # --- Auto-analyze after fetch (transcript is already visible above) ---
    if st.session_state.auto_analyze:
        auto_detail = st.session_state.auto_analyze_detail or detail_level
        st.session_state.auto_analyze = False
        st.session_state.auto_analyze_detail = None
        with st.spinner(f"Analyzing ({auto_detail}) — this may take a minute..."):
            try:
                analysis = analyze_transcript(st.session_state.transcript, client, auto_detail, metadata=st.session_state.metadata)
                st.session_state.analysis = analysis
                # Auto-save to library + auto-tag
                if st.session_state.metadata:
                    vid_id = extract_video_id(st.session_state.metadata.get("url", ""))
                    save_video(vid_id, st.session_state.metadata.get("url", ""),
                               st.session_state.metadata, st.session_state.transcript,
                               st.session_state.speakers, analysis, auto_detail)
                    try:
                        tags = generate_tags(st.session_state.transcript, st.session_state.metadata, client)
                        save_tags(vid_id, tags)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"Analysis failed: {e}")
        # Extract key quotes after analysis
        if st.session_state.analysis and st.session_state.metadata:
            with st.spinner("Extracting key quotes..."):
                try:
                    quotes = extract_key_quotes(st.session_state.transcript, st.session_state.metadata, client)
                    st.session_state.key_quotes = quotes
                    vid_id = extract_video_id(st.session_state.metadata.get("url", ""))
                    save_key_quotes(vid_id, quotes)
                except Exception:
                    pass
        st.rerun()

    # --- Re-analyze Button (always available to switch detail levels) ---
    reanalyze_label = "Analyze Transcript" if st.session_state.analysis is None else f"Re-analyze ({detail_level})"
    if st.button(reanalyze_label, type="primary", key="analyze_btn"):
        with st.spinner(f"Analyzing ({detail_level}) — this may take a minute..."):
            try:
                analysis = analyze_transcript(st.session_state.transcript, client, detail_level, metadata=st.session_state.metadata)
                st.session_state.analysis = analysis
                # Update library with new analysis + re-tag
                if st.session_state.metadata:
                    vid_id = extract_video_id(st.session_state.metadata.get("url", ""))
                    save_video(vid_id, st.session_state.metadata.get("url", ""),
                               st.session_state.metadata, st.session_state.transcript,
                               st.session_state.speakers, analysis, detail_level)
                    try:
                        tags = generate_tags(st.session_state.transcript, st.session_state.metadata, client)
                        save_tags(vid_id, tags)
                    except Exception:
                        pass
            except Exception as e:
                st.error(f"Error: {e}")
        # Extract key quotes on re-analyze too
        if st.session_state.analysis and st.session_state.metadata:
            with st.spinner("Extracting key quotes..."):
                try:
                    quotes = extract_key_quotes(st.session_state.transcript, st.session_state.metadata, client)
                    st.session_state.key_quotes = quotes
                    vid_id = extract_video_id(st.session_state.metadata.get("url", ""))
                    save_key_quotes(vid_id, quotes)
                except Exception:
                    pass
        st.rerun()

    # --- Display Analysis ---
    if st.session_state.analysis:
        st.markdown("---")
        st.markdown('<div class="section-header"><span class="icon">🔍</span> Analysis</div>', unsafe_allow_html=True)

        st.markdown(st.session_state.analysis)

        # --- Key Quotes ---
        if st.session_state.key_quotes:
            st.markdown("---")
            st.markdown('<div class="section-header"><span class="icon">💎</span> Key Quotes</div>', unsafe_allow_html=True)
            st.markdown(st.session_state.key_quotes)
        elif st.session_state.metadata:
            if st.button("💎 Extract Key Quotes", key="extract_quotes_btn"):
                with st.spinner("Extracting key quotes..."):
                    try:
                        quotes = extract_key_quotes(st.session_state.transcript, st.session_state.metadata, client)
                        st.session_state.key_quotes = quotes
                        vid_id = extract_video_id(st.session_state.metadata.get("url", ""))
                        save_key_quotes(vid_id, quotes)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not extract quotes: {e}")

        # --- Action buttons row ---
        col1, col2 = st.columns(2)

        # Copy button
        with col1:
            import streamlit.components.v1 as components
            import html as html_mod
            escaped = html_mod.escape(st.session_state.analysis).replace("`", "\\`")
            copy_html = f"""
            <textarea id="analysis-copy-text" style="position:absolute;left:-9999px;">{escaped}</textarea>
            <button id="copy-btn" style="
                background: linear-gradient(135deg, #FF0050, #7C3AED);
                border: none; border-radius: 8px; color: white;
                padding: 0.5rem 1.25rem; font-weight: 600; font-size: 0.85rem;
                cursor: pointer; font-family: Inter, sans-serif; width: 100%;
            ">📋 Copy Analysis</button>
            <script>
            document.getElementById('copy-btn').addEventListener('click', function() {{
                var t = document.getElementById('analysis-copy-text');
                t.select();
                document.execCommand('copy');
                this.textContent = '✅ Copied!';
                setTimeout(() => this.textContent = '📋 Copy Analysis', 2000);
            }});
            </script>
            """
            components.html(copy_html, height=45)

        # Export to Markdown button
        with col2:
            md_content = export_markdown(
                metadata=st.session_state.metadata or {},
                transcript=st.session_state.transcript,
                analysis=st.session_state.analysis,
                speakers=st.session_state.speakers,
                key_quotes=st.session_state.key_quotes,
            )
            title_slug = (st.session_state.metadata or {}).get("title", "video")
            title_slug = re.sub(r'[^\w\s-]', '', title_slug)[:50].strip().replace(' ', '_')
            st.download_button(
                "📥 Download as Markdown",
                data=md_content,
                file_name=f"tubescribe_{title_slug}.md",
                mime="text/markdown",
                use_container_width=True,
            )

        st.markdown("---")

        # --- Q&A Chat ---
        st.markdown('<div class="section-header"><span class="icon">💬</span> Ask Questions</div>', unsafe_allow_html=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if question := st.chat_input("Ask anything about the video..."):
            st.session_state.messages.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer = ask_question(
                        st.session_state.transcript,
                        question,
                        st.session_state.chat_history,
                        client,
                    )
                st.markdown(answer)

            st.session_state.chat_history.append({"role": "user", "content": question})
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.session_state.messages.append({"role": "assistant", "content": answer})
else:
    st.markdown("""
    <div style="text-align: center; padding: 3rem 1rem; color: #666;">
        <p style="font-size: 3rem; margin-bottom: 0.5rem;">🎬</p>
        <p style="font-size: 1.1rem;">Paste a YouTube URL or playlist link in the sidebar to get started</p>
    </div>
    """, unsafe_allow_html=True)
