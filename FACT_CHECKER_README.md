# Fact & Logic Checker Feature

## Overview

The Fact & Logic Checker is a core feature of Wisdom Agent that analyzes content for factual accuracy, logical soundness, and alignment with wisdom principles. Unlike traditional fact-checkers that only ask "Is it true?", Wisdom Agent also asks "Does it serve wisdom?"

### What Makes This Unique

- **7 Universal Values Scoring**: Every analysis is evaluated against Awareness, Honesty, Accuracy, Competence, Compassion, Loving-kindness, and Joyful-sharing
- **Something Deeperism Philosophy**: Content is assessed for whether it fosters or squelches wisdom-seeking
- **The Three Questions**: Is it True? Is it Reasonable? Does it help humans organize around spiritual Love?

## Features

### Content Sources
- **URLs**: Fetch and analyze articles, blog posts, news stories
- **Text**: Paste content directly for analysis
- **Files**: Upload PDF or DOCX documents

### Analysis Pipeline
1. **Content Extraction**: Fetches and cleans content from various sources
2. **Claim Extraction**: Uses LLM to identify factual claims worth checking
3. **Fact Checking**: Verifies claims using multiple providers
4. **Logic Analysis**: Detects fallacies and analyzes argument structure
5. **Wisdom Evaluation**: Scores against 7 Universal Values

### Fact-Check Providers
- **Google Fact Check API**: Searches existing fact-checks from PolitiFact, Snopes, etc.
- **ClaimBuster**: Check-worthiness scoring and fact-check database
- **LLM Verification**: Web search + LLM analysis for novel claims
- **DuckDuckGo**: Free web search (no API key needed)

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies for Phase 2:
```
beautifulsoup4>=4.12.0       # HTML parsing
readability-lxml>=0.8.1      # Article extraction
pdfplumber>=0.10.0           # PDF text extraction
lxml>=5.0.0                  # Required by readability-lxml
```

### 2. Configure API Keys (Optional but Recommended)

Create or update your `.env` file:

```bash
# Required for full functionality (but system works without these)
GOOGLE_FACT_CHECK_API_KEY=your_key_here    # Get from Google Cloud Console
CLAIMBUSTER_API_KEY=your_key_here          # Get from https://idir.uta.edu/claimbuster/api/

# Optional premium search
BRAVE_SEARCH_API_KEY=your_key_here         # Get from https://brave.com/search/api/
TAVILY_API_KEY=your_key_here               # Get from https://tavily.com/
```

**Note**: The system works without any API keys! It will use DuckDuckGo for web search and LLM verification as fallbacks.

### 3. Run Database Migrations

```bash
# The fact-checker tables should be created automatically on first run
# Or run the migration script manually:
python -m backend.database.migrations.create_fact_check_tables
```

## Usage

### API Endpoints

All endpoints are under `/api/reviews`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reviews` | Create a new fact-check review |
| GET | `/api/reviews` | List all reviews (with filtering) |
| GET | `/api/reviews/{id}` | Get review with full details |
| DELETE | `/api/reviews/{id}` | Delete a review |
| GET | `/api/reviews/{id}/status` | Poll for analysis progress |
| POST | `/api/reviews/{id}/analyze` | Re-run analysis |
| GET | `/api/reviews/session/{session_id}` | Get reviews for a session |
| GET | `/api/reviews/repository/all` | Browse all completed reviews |

### Example: Create a Review

```bash
# Analyze a URL
curl -X POST http://localhost:8000/api/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "url",
    "source_url": "https://example.com/article",
    "title": "Example Article Analysis"
  }'

# Analyze pasted text
curl -X POST http://localhost:8000/api/reviews \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "text",
    "source_content": "The earth is flat and vaccines cause autism.",
    "title": "Test Claims"
  }'
```

### Example: Check Analysis Status

```bash
curl http://localhost:8000/api/reviews/1/status
```

Response:
```json
{
  "id": 1,
  "status": "fact_checking",
  "progress_message": "Verifying claims against sources...",
  "error_message": null,
  "completed_at": null
}
```

### Example: Get Full Results

```bash
curl http://localhost:8000/api/reviews/1
```

## Testing

### Run the Test Suite

```bash
# Run all tests
pytest backend/tests/ -v

# Run fact-checker specific tests
pytest backend/tests/test_fact_checker.py -v
```

### Manual Testing

1. **Start the server**:
   ```bash
   uvicorn backend.main:app --reload
   ```

2. **Open Swagger UI**: http://localhost:8000/docs

3. **Test the flow**:
   - Create a review with a URL or text
   - Poll the status endpoint until `status` is `completed`
   - Fetch the full review to see results

### Testing Individual Services

```python
# Test content extraction
from backend.services.content_extraction_service import get_content_extraction_service

service = get_content_extraction_service()
# Service will extract content when run_analysis is called

# Test web search
from backend.services.web_search_service import get_web_search_service
import asyncio

async def test_search():
    service = get_web_search_service()
    results = await service.search("climate change facts")
    for r in results:
        print(f"{r.title}: {r.url}")

asyncio.run(test_search())

# Check provider availability
from backend.providers import get_provider_registry
import asyncio

async def check_providers():
    registry = get_provider_registry()
    providers = await registry.get_available_providers()
    print(f"Available providers: {[p.name for p in providers]}")

asyncio.run(check_providers())
```

## Architecture

```
backend/
├── services/
│   ├── review_service.py           # Main orchestrator
│   ├── content_extraction_service.py
│   ├── claim_extraction_service.py
│   ├── fact_check_service.py
│   ├── web_search_service.py
│   ├── logic_analysis_service.py
│   └── wisdom_evaluation_service.py
├── providers/
│   ├── __init__.py
│   ├── base.py                     # Provider interface
│   ├── registry.py                 # Provider management
│   ├── claimbuster.py
│   ├── google_factcheck.py
│   └── llm_verification.py
├── routers/
│   └── review_router.py            # API endpoints
├── database/
│   └── fact_check_models.py        # SQLAlchemy models
└── models/
    └── review_models.py            # Pydantic schemas
```

## Response Structure

A completed review includes:

```json
{
  "id": 1,
  "title": "Article Analysis",
  "status": "completed",
  "quick_summary": "Analyzed 5 claims: 2 verified, 2 false, 1 mixed.",
  "overall_factual_verdict": "mixed",
  "overall_wisdom_verdict": "mostly_wise",
  "confidence_score": 0.75,
  "claims": [
    {
      "claim_text": "The specific claim",
      "claim_type": "factual",
      "check_worthiness_score": 0.8,
      "fact_check_result": {
        "verdict": "false",
        "confidence": 0.9,
        "explanation": "...",
        "sources": [...]
      }
    }
  ],
  "logic_analysis": {
    "main_conclusion": "...",
    "premises": [...],
    "fallacies_found": [...],
    "logic_quality_score": 0.7
  },
  "wisdom_evaluation": {
    "awareness": {"score": 4, "notes": "..."},
    "honesty": {"score": 3, "notes": "..."},
    // ... other values
    "overall_wisdom_score": 0.65,
    "serves_wisdom_or_folly": "mostly_wise",
    "final_reflection": "..."
  }
}
```

## Verdicts

### Factual Verdicts
- `accurate` - All claims verified true
- `mostly_accurate` - Most claims true, minor issues
- `mixed` - Roughly equal true and false claims
- `mostly_inaccurate` - Most claims false
- `inaccurate` - All/most claims false
- `unverifiable` - Cannot be verified

### Wisdom Verdicts
- `serves_wisdom` - Exemplary alignment with values
- `mostly_wise` - Good alignment with minor issues
- `mixed` - Some wise, some unwise elements
- `mostly_unwise` - Significant alignment issues
- `serves_folly` - Actively undermines wisdom
- `uncertain` - Cannot determine

## Troubleshooting

### "No providers available"
- This means no API keys are configured AND web search failed
- Solution: The LLM verification provider with DuckDuckGo should always be available
- Check that your LLM router is configured correctly

### "Paywall detected"
- The URL has a paywall blocking content access
- Solution: Copy/paste the article text and use `source_type: "text"`

### "Content too short"
- Content must be at least 50-100 characters for meaningful analysis
- Solution: Provide more substantial content

### Slow analysis
- Full analysis can take 30-60 seconds depending on content length
- Use the status endpoint to poll for progress
- Consider implementing webhooks for production use
