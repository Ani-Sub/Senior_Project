# YouTube Intelligence System

Extracts claims from YouTube video transcripts and comments, then synthesizes them into a cross-video narrative with **temporal trend analysis** and **content risk assessment**.

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
├── ytAPI/
│   ├── channelExtract.py   # search and filter YouTube channels
│   ├── videoExtract.py     # discover and filter videos (with metadata)
│   ├── transcriptExtract.py# fetch video transcripts
│   └── commentExtract.py   # fetch top comments (with timestamps)
├── extraction/
│   ├── llmPrompts.py       # all LLM prompt builders
│   └── analyzer.py         # LLM calls, claim extraction, synthesis
├── trends/                 # Temporal trend analysis
│   ├── temporal.py         # time bucketing (daily/weekly)
│   ├── metrics.py          # activity metric calculations
│   ├── detector.py         # pattern detection (surge/peak/decline)
│   └── aggregator.py       # aggregate by topic/claim/narrative
├── risk/                   # Content risk assessment
│   ├── keywords.py         # risk category keywords and patterns
│   ├── detector.py         # hybrid detection (keyword + LLM)
│   └── aggregator.py       # aggregate risk across videos
└── utility/
    ├── parser.py           # JSON parser
    ├── chunker.py          # text chunker
    └── debugLog.py         # debug logging
```

## Running

```bash
cd Backend
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
    max_comments=30,                # comments to pull per video
    trend_granularity="weekly",     # "daily" or "weekly" time buckets
    assess_risk=True,               # enable content risk assessment
    llm_verify_risk=True            # use LLM for borderline risk cases
)
```

## Trend Analysis

The system now tracks **temporal patterns** of narrative activity:

### Metrics Tracked (per time bucket)
- **Video count** — number of videos published
- **View counts** — total views across videos
- **Comment volume** — total comments
- **Engagement ratio** — (likes + comments) / views

### Pattern Detection
- **Surge** — rapid increase in activity (2x+ growth)
- **Peak** — activity rose then declined (spike pattern)
- **Decline** — significant drop in activity (50%+ decrease)
- **Stable** — relatively consistent activity
- **Emerging** — just starting to grow

### Aggregation Levels
- **Overall** — all videos combined
- **By narrative** — grouped by synthesized narratives
- **By topic** — grouped by extracted topics
- **By claim type** — factual vs. prediction vs. opinion vs. statistic

### Example Output

```json
{
  "trends": {
    "granularity": "weekly",
    "time_range": { "start": "2026-01-15T...", "end": "2026-03-15T..." },
    "overall": {
      "trend": {
        "pattern": "surge",
        "confidence": 0.85,
        "peak_period": "2026-03-01",
        "description": "Activity surged 3.2x from 2026-01-15 to 2026-03-15."
      },
      "timeline": [
        { "period": "2026-W03", "video_count": 2, "total_views": 45000, ... },
        { "period": "2026-W10", "video_count": 8, "total_views": 320000, ... }
      ]
    },
    "by_narrative": [
      {
        "narrative": "AI Coding Assistants & Job Impact",
        "pattern": "peak",
        "peak_period": "2026-W07",
        "confidence": 0.72
      }
    ]
  }
}
```

## Risk Assessment

The system performs **hybrid content risk detection** on transcripts and comments:

### Risk Categories
| Category | Description |
|----------|-------------|
| `self_harm` | Content related to self-harm or suicide |
| `violence` | Threats of violence or violent content |
| `illegal_activity` | References to fraud, drugs, hacking |
| `misinformation` | False or misleading health/political claims |
| `hate_speech` | Discriminatory content targeting groups |
| `harassment` | Targeted harassment, doxxing, stalking |
| `toxicity` | Generally toxic or abusive language |
| `scam` | Financial scams or fraudulent schemes |

### Detection Method (Hybrid)
1. **Keyword scan** — Fast pattern matching for known risk terms
2. **LLM verification** — Borderline cases sent to Ollama for context analysis
3. **Confidence scoring** — Each flag rated 0.0-1.0 based on detection method

### Risk Levels
- **None** — No risks detected
- **Low** — Minor flags, low confidence
- **Medium** — Some concerning content
- **High** — Multiple high-confidence flags
- **Critical** — Severe content requiring immediate attention

### Example Output

```json
{
  "risk": {
    "per_video": [
      {
        "video_id": "abc123",
        "risk_score": 0.65,
        "risk_level": "high",
        "flags": [
          {
            "category": "misinformation",
            "confidence": 0.9,
            "source": "transcript",
            "excerpt": "miracle cure that doctors...",
            "context": "...trying to hide this miracle cure that doctors don't want you to know about...",
            "detection_method": "keyword_high"
          }
        ]
      }
    ],
    "aggregate": {
      "total_videos": 10,
      "videos_with_risks": 3,
      "total_flags": 12,
      "overall_risk_level": "medium",
      "risk_distribution": {
        "misinformation": 5,
        "scam": 4,
        "toxicity": 3
      },
      "high_risk_videos": ["abc123", "xyz789"]
    }
  }
}
```

## Testing Without APIs

Run the test scripts to verify functionality with mock data:

```bash
# Test trend analysis
python test_trends.py

# Test risk assessment  
python test_risk.py
```

No YouTube API key or Ollama required for testing.
