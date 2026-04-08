# YouTube Intelligence System

Extracts claims from YouTube video transcripts and comments, synthesizes them into distinct narratives, tracks narrative trends over time, and assesses content risk.

## Features

- **Claim Extraction** — LLM-powered extraction of claims from transcripts and comments
- **Vector Embeddings** — Semantic embeddings for claims and narrative centroids
- **Narrative Synthesis** — Identifies 2-5 distinct narratives across videos
- **Temporal Trends** — Tracks each narrative's growth/decline over time
- **Risk Assessment** — Hybrid keyword + LLM detection of harmful content
- **Quota Optimization** — RSS feeds + caching to minimize YouTube API usage
- **Checkpoint System** — Saves progress after each step (crash recovery)
- **DB-Ready Export** — Flat JSON files ready for database import

## Setup

1. **Install dependencies**
```bash
pip install youtube-transcript-api requests google-api-python-client python-dotenv
```

2. **Create a `.env` file** in the `Backend/` folder:
```
YOUTUBE_API_KEY=your_key_here
```

3. **Make sure Ollama is running** with llama3 and embedding model:
```bash
ollama run llama3
ollama pull nomic-embed-text
```

## Project Structure

```
Backend/
├── main.py                    # Pipeline orchestrator with checkpoints
├── config.py                  # API keys, LLM settings, embedding config
│
├── ytAPI/                     # YouTube data fetching
│   ├── channelExtract.py      # Search and filter channels
│   ├── videoExtract.py        # Discover videos (RSS + API hybrid)
│   ├── transcriptExtract.py   # Fetch transcripts (with translation)
│   ├── commentExtract.py      # Fetch top comments
│   ├── rss_feed.py            # FREE video discovery via RSS
│   └── channel_cache.py       # Cache channels to reduce API calls
│
├── extraction/                # LLM-based extraction
│   ├── llmPrompts.py          # Prompt templates
│   └── analyzer.py            # Claim extraction + synthesis
│
├── trends/                    # Temporal trend analysis
│   ├── __init__.py            # Module exports
│   ├── temporal.py            # Time bucketing (daily/weekly)
│   ├── metrics.py             # Per-period metric calculations
│   ├── detector.py            # Pattern detection (surge/peak/decline)
│   └── aggregator.py          # Aggregate trends by narrative
│
├── risk/                      # Content risk assessment
│   ├── __init__.py            # Module exports
│   ├── keywords.py            # Risk category keywords
│   ├── detector.py            # Hybrid detection (keyword + LLM)
│   └── aggregator.py          # Aggregate risk across videos
│
└── utility/
    ├── output.py              # Checkpoint saves + DB-ready export
    ├── embeddings.py          # Vector embeddings via Ollama
    ├── parser.py              # JSON parsing with truncation repair
    └── chunker.py             # Text chunking for LLM
```

## Running

```bash
cd Backend
python main.py
```

## Output Structure

Each run creates a timestamped directory:

```
output/run_20260407_143022/
├── checkpoints/               # Incremental saves (crash recovery)
│   ├── video_abc123.json      # Saved after each video processed
│   ├── video_def456.json
│   ├── synthesis.json         # Saved after synthesis step
│   ├── trends.json            # Saved after trends step
│   └── risk.json              # Saved after risk step
│
└── db_ready/                  # Flat files for database import
    ├── channels.json          # → CHANNELS table
    ├── videos.json            # → VIDEOS table
    ├── transcripts.json       # → TRANSCRIPTS table
    ├── transcript_chunks.json # → TRANSCRIPT_CHUNKS table
    ├── comments.json          # → COMMENTS table
    ├── claims.json            # → CLAIMS table
    ├── claim_embeddings.json  # → Claim vectors (768 dims)
    ├── narratives.json        # → NARRATIVES table (with centroid)
    ├── narrative_videos.json  # → Many-to-many link table
    ├── narrative_trends.json  # → Trend data per narrative
    ├── trends_timeline.json   # → Overall activity timeline
    ├── risk_flags.json        # → Risk flags table
    └── run_metadata.json      # Run info and counts
```

## Configuration

Edit the `run_pipeline()` call in `main.py`:

```python
run_pipeline(
    search_keywords="AI",           # Channel search query
    channel_sub_min=100_000,        # Minimum subscribers
    video_view_min=50_000,          # Minimum video views
    video_keywords=["ai", "tech"],  # Required title keywords
    days=60,                        # How far back to look
    max_comments=30,                # Comments per video
    trend_granularity="weekly",     # "daily" or "weekly"
    assess_risk=True,               # Enable risk assessment
    llm_verify_risk=True,           # LLM for borderline cases
    use_cache=True,                 # Use RSS + cache (saves quota)
    cache_max_age_days=30,          # Re-search channels after N days
    generate_embeddings=True,       # Vector embeddings for claims
)
```

## Pipeline Steps

```
STEP 1: Discovery
  └─ Check cache → RSS feeds (FREE) or API search
  └─ Filter by subscribers, views, keywords

STEP 2: Extraction (checkpoint after each video)
  └─ Fetch transcript (with auto-translation fallback)
  └─ Fetch comments
  └─ LLM extracts topics + claims
  └─ Generate embeddings for each claim (if enabled)
  └─ Save checkpoint immediately

STEP 3: Synthesis (checkpoint)
  └─ LLM identifies 2-5 distinct narratives
  └─ Maps each narrative to supporting videos

STEP 4: Trend Analysis (checkpoint)
  └─ Bucket videos by time period
  └─ Calculate metrics per narrative per period
  └─ Detect patterns (surge/peak/decline/stable)

STEP 5: Risk Assessment (checkpoint)
  └─ Keyword scan for risk categories
  └─ LLM verification for borderline cases
  └─ Aggregate risk scores

STEP 6: Export
  └─ Generate DB-ready flat files
```

## Quota Optimization

YouTube API quota is limited (10,000 units/day). This system minimizes usage:

| Action | First Run | Repeat Runs |
|--------|-----------|-------------|
| Channel search | 100 units | **FREE** (cached) |
| Video discovery | API calls | **FREE** (RSS feeds) |
| Video metadata | 1 unit/50 videos | 1 unit/50 videos |
| Transcripts | **FREE** | **FREE** |

**How it works:**
1. First search for "AI" → API finds channels → saves to cache
2. Next search for "AI" → cache hit → RSS feeds for videos → only API for view counts

## Narrative Synthesis

The LLM identifies distinct narratives across videos:

```json
{
  "narratives": [
    {
      "id": "narrative_1",
      "name": "AI Job Displacement Concerns",
      "summary": "Growing worry that AI will automate white-collar jobs...",
      "video_ids": ["abc123", "def456", "ghi789"]
    },
    {
      "id": "narrative_2",
      "name": "Open Source AI Movement",
      "summary": "Community pushing for transparent AI development...",
      "video_ids": ["xyz123", "abc123"]
    }
  ],
  "overall_summary": "The dataset reveals increasing tension between...",
  "high_confidence_claims": [...]
}
```

## Trend Analysis

Each narrative is tracked over time:

```json
{
  "narratives": [
    {
      "narrative_id": "narrative_1",
      "name": "AI Job Displacement Concerns",
      "video_count": 5,
      "trend": {
        "pattern": "surge",
        "confidence": 0.85,
        "peak_period": "2026-W12",
        "description": "Activity surged 2.5x from 2026-W10 to 2026-W12."
      },
      "timeline": [
        {
          "period": "2026-W10",
          "video_count": 1,
          "total_views": 50000,
          "total_likes": 2500,
          "total_comments": 340,
          "engagement_ratio": 0.057,
          "claim_count": 12
        },
        {
          "period": "2026-W11",
          "video_count": 3,
          "total_views": 180000,
          ...
        }
      ]
    }
  ]
}
```

### Pattern Types

| Pattern | Condition |
|---------|-----------|
| **surge** | Last period ≥ 2× first period |
| **decline** | Last period ≤ 50% of first |
| **peak** | Rise then fall (spike in middle) |
| **emerging** | Recent growth, limited data |
| **stable** | Consistent activity |

## Risk Assessment

Hybrid detection with 8 risk categories:

| Category | Description |
|----------|-------------|
| `self_harm` | Self-harm or suicide content |
| `violence` | Threats or violent content |
| `illegal_activity` | Fraud, drugs, hacking |
| `misinformation` | False health/political claims |
| `hate_speech` | Discriminatory content |
| `harassment` | Targeted harassment, doxxing |
| `toxicity` | Abusive language |
| `scam` | Financial scams |

### Detection Flow

1. **Keyword scan** — Fast pattern matching (high/medium confidence)
2. **LLM verification** — Borderline cases checked for context
3. **Confidence scoring** — 0.0-1.0 based on detection method

### Risk Levels

- **none** — No risks detected
- **low** — Minor flags, low confidence
- **medium** — Some concerning content
- **high** — Multiple high-confidence flags
- **critical** — Severe content

## DB-Ready Format

Each file maps directly to a database table:

**channels.json:**
```json
[
  {
    "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
    "channel_title": "Google Developers"
  }
]
```

**videos.json:**
```json
[
  {
    "video_id": "abc123",
    "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
    "title": "What's New in AI",
    "description": "In this video we explore...",
    "view_count": 150000,
    "duration_seconds": 930,
    "published_at": "2026-03-15T14:30:00Z",
    "processed": true,
    "processed_at": "2026-04-08T10:30:00Z"
  }
]
```

**transcripts.json:**
```json
[
  {
    "transcript_id": 1,
    "video_id": "abc123",
    "transcript": "Welcome to our video about AI trends...",
    "processed_at": "2026-04-08T10:30:00Z"
  }
]
```

**comments.json:**
```json
[
  {
    "comment_id": "UgwXyz123",
    "video_id": "abc123",
    "commenter_name": "TechFan42",
    "comment_text": "Great explanation of LLMs!",
    "published_at": "2026-03-16T08:20:00Z",
    "is_reply": false,
    "top_level_comment_id": null,
    "processed_at": "2026-04-08T10:30:00Z"
  }
]
```

**claims.json:**
```json
[
  {
    "claim_id": 1,
    "video_id": "abc123",
    "narrative_id": null,
    "claim_text": "AI will automate 50% of jobs by 2030",
    "processed_at": "2026-04-08T10:30:00Z"
  }
]
```

**narratives.json:**
```json
[
  {
    "narrative_id": "narrative_1",
    "title": "AI Job Displacement Concerns",
    "summary": "Growing worry about automation...",
    "topic_label": "AI Job Displacement Concerns",
    "claim_count": 15,
    "first_seen_at": "2026-02-10T12:00:00Z",
    "last_seen_at": "2026-04-01T09:30:00Z"
  }
]
```

**narrative_videos.json** (many-to-many):
```json
[
  {"narrative_id": "narrative_1", "video_id": "abc123"},
  {"narrative_id": "narrative_1", "video_id": "def456"},
  {"narrative_id": "narrative_2", "video_id": "abc123"}
]
```

## Vector Embeddings

The pipeline generates semantic embeddings for claims using Ollama's `nomic-embed-text` model (768 dimensions).

### Setup

```bash
ollama pull nomic-embed-text
```

### How It Works

1. **Claim Embeddings** — Each extracted claim gets a 768-dimensional vector
2. **Narrative Centroids** — Average of all claim vectors in that narrative
3. **Similarity Matching** — New claims can be matched to existing narratives by comparing vectors

### Output Files

**claim_embeddings.json:**
```json
[
  {
    "claim_id": 1,
    "embedding": [0.123, -0.456, 0.789, ...]  // 768 floats
  }
]
```

**narratives.json** (includes centroid):
```json
[
  {
    "narrative_id": "narrative_1",
    "title": "AI Job Displacement",
    "centroid_embedding": [0.234, -0.567, 0.890, ...],  // 768 floats
    ...
  }
]
```

### Use Cases

- **Incremental Processing** — Match new claims to existing narratives without re-running synthesis
- **Similarity Search** — Find claims similar to a query
- **Clustering** — Automatically discover narratives using K-means on embeddings

### Disabling Embeddings

If you don't need embeddings (faster processing):

```python
run_pipeline(
    ...
    generate_embeddings=False
)
```

## Testing

Test without APIs using mock data:

```bash
python test_trends.py   # Test trend analysis
python test_risk.py     # Test risk assessment
```

## Troubleshooting

### No videos discovered
- Broaden `video_keywords` or lower `video_view_min`
- Check if channels have recent uploads

### LLM truncation errors
- Increase `LLM_NUM_PREDICT` in `config.py` (default: 2500)
- Reduce `CHUNK_SIZE` for smaller transcript chunks

### Quota exceeded
- Enable caching: `use_cache=True`
- Wait for daily reset or use multiple API keys

### Transcript not found
- Video may not have captions
- System auto-tries translation if original language isn't English

### Embeddings not generated
- Make sure embedding model is installed: `ollama pull nomic-embed-text`
- Check Ollama is running: `ollama list`
- Pipeline continues without embeddings if service unavailable
