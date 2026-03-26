# YouTube Intelligence System

Extracts claims from YouTube video transcripts and comments, then synthesizes them into a cross-video narrative.

## Setup

1. **Install dependencies**
```bash
pip install youtube-transcript-api requests google-api-python-client python-dotenv
```

2. **Create a `.env` file** in the `Backend/` folder:
```
YOUTUBE_API_KEY=your_key_here
```

3. **Make sure Ollama is running** with llama3:
```bash
ollama run llama3
```

## Project Structure

```
Backend/
├── main.py                 # entry point — run this
├── config.py               # API keys, LLM settings, constants
├── ingestion/
│   ├── channels.py         # search and filter YouTube channels
│   ├── videos.py           # discover and filter videos
│   ├── transcripts.py      # fetch video transcripts
│   └── comments.py         # fetch top comments
├── extraction/
│   ├── prompts.py          # all LLM prompt builders
│   └── analyzer.py         # LLM calls, claim extraction, synthesis
└── utils/
    └── parsing.py          # JSON parser and text chunker
```

## Running

```bash
cd yt_intelligence
python main.py
```

Results are saved to a timestamped `summary_YYYYMMDD_HHMMSS.json` file.

## Customizing

Edit the `run_pipeline()` call in `main.py`:

```python
run_pipeline(
    search_keywords="AI news",      # what to search for
    channel_sub_min=100_000,        # minimum channel subscribers
    video_view_min=20_000,          # minimum video views
    video_keywords=["ai", "tech"],  # keywords that must appear in video title
    days=90,                        # how far back to look
    max_comments=30                 # comments to pull per video
)
```
