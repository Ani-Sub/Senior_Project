# YouTube Intelligence System

Extracts claims from YouTube video transcripts and comments, synthesizes them into distinct narratives, tracks narrative trends over time, and assesses content risk.

## Features

- **Claim Extraction** — LLM-powered extraction of claims from transcripts and comments
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
YOUTUBE_API_KEY=your_youtube_key_here
GROQ_API_KEY=your_groq_key_here
```

Get your Groq API key at: https://console.groq.com

## Project Structure

```
Backend/
├── main.py                    # Pipeline orchestrator with checkpoints
├── config.py                  # API keys, LLM settings
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
    ├── parser.py              # JSON parsing with truncation repair
    └── chunker.py             # Text chunking for LLM
```

## Running

```bash
cd Backend
python main.py
```

## Output Structure

Each run outputs to a static `latest` folder (overwrites previous run):

```
output/latest/
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
    ├── narratives.json        # → NARRATIVES table
    ├── narrative_videos.json  # → Many-to-many link table
    ├── narrative_trends.json  # → Trend data per narrative
    ├── trends_timeline.json   # → Overall activity timeline
    ├── risk_flags.json        # → Risk flags table
    └── run_metadata.json      # Run info and counts
```

**Static paths for backend integration:**
- `output/latest/db_ready/claims.json`
- `output/latest/db_ready/videos.json`
- etc.

## Cleanup After DB Import

After importing data to your database, call `cleanup_output()` to delete the output folder:

```python
from utility.output import cleanup_output

# After successful DB import:
cleanup_output()  # Deletes entire output/ folder
```

Or run from command line:
```bash
cd Backend
python cleanup.py
```

## Configuration

Edit the `run_pipeline()` call in `main.py`:

```python
run_pipeline(
    search_keywords="AI",           # Search query
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
    search_mode="videos",           # "videos" or "channels"
)
```

### Search Modes

| Mode | How it works | Best for |
|------|--------------|----------|
| `"videos"` (default) | Search videos → extract channels → filter by subs → get more videos | Catching all relevant creators |
| `"channels"` | Search channels by name → filter by subs → get videos | When channel names match keywords |

**Why "videos" mode is better:**
- Catches channels that *make* relevant content but aren't *named* for it
- E.g., "Fireship" makes AI videos but wouldn't show up in channel search for "AI"
- Spam channels rarely rank well in video search, so they get filtered out naturally

## Pipeline Steps

```
STEP 1: Discovery
  └─ Check cache → RSS feeds (FREE) or API search
  └─ Filter by subscribers, views, keywords

STEP 2: Extraction (checkpoint after each video)
  └─ Fetch transcript (with auto-translation fallback)
  └─ Fetch comments
  └─ LLM extracts topics + claims
  └─ Save checkpoint immediately

STEP 3: Synthesis (checkpoint)
  └─ LLM identifies 2-5 distinct narratives
  └─ Maps each narrative to supporting videos

STEP 4: Trend Analysis (checkpoint)
  └─ Bucket videos by time period
  └─ Calculate metrics per narrative per period
  └─ Detect patterns (rising/peaking/declining/stable)

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

### Direction Types

| Direction | Condition |
|-----------|-----------|
| **rising** | Activity increasing (≥2× growth or recent uptick) |
| **peaking** | Rise then fall (spike in middle) |
| **declining** | Activity dropping (≤50% of start) |
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
    "channel_name": "Google Developers",
    "total_claims": 42,
    "flagged_claims": 0,
    "accuracy_rate": 0.0,
    "risk_level": "low",
    "risk_score": 0.0,
    "processed_at": null
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
    "channel_id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
    "video_title": "What's New in AI",
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
    "published_date": "2026-03-16T08:20:00Z",
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
    "video_title": "What's New in AI",
    "claim_text": "AI will automate 50% of jobs by 2030",
    "claim_type": "factual",
    "confidence_score": 0.85,
    "risk_level": "low",
    "processed_at": "2026-04-08T10:30:00Z",
    "is_verified": false,
    "accuracy_rating": null
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
    "color": "#3B82F6",
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
