import sys
from transcript_agent import extract_video_id, fetch_transcript, analyze_transcript, ask_question, get_client


def main():
    client = get_client()

    # Get URL from argument or prompt
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter YouTube URL: ").strip()

    if not url:
        print("Error: No URL provided.")
        sys.exit(1)

    # Extract video ID and fetch transcript
    try:
        video_id = extract_video_id(url)
        print(f"Fetching transcript for video: {video_id}...")
        transcript = fetch_transcript(video_id)
        print(f"Transcript fetched ({len(transcript)} characters).\n")
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        sys.exit(1)

    # Analyze
    print("Analyzing transcript...\n")
    try:
        analysis = analyze_transcript(transcript, client)
        print("=" * 60)
        print("ANALYSIS")
        print("=" * 60)
        print(analysis)
        print("=" * 60)
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)

    # Q&A loop
    print("\nYou can now ask questions about the video. Type 'exit' or 'quit' to stop.\n")
    chat_history = []

    while True:
        question = input("You: ").strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        try:
            answer = ask_question(transcript, question, chat_history, client)
            print(f"\nAssistant: {answer}\n")
            chat_history.append({"role": "user", "content": question})
            chat_history.append({"role": "assistant", "content": answer})
        except Exception as e:
            print(f"Error: {e}\n")


if __name__ == "__main__":
    main()
