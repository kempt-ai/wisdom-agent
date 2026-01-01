# Wisdom Agent Handoff Summary
**Date:** December 25, 2025  
**Session Focus:** Session Continuity Fix + Knowledge Base Architecture  
**Next Session:** Implement Knowledge Base (Steps 1-4)

---

## Project Overview

The **Wisdom Agent (WA)** is an open-source AI system designed to help individuals grow in wisdom. It's grounded in **Something Deeperism** philosophy, which emphasizes a poetic relation to Truth, Pure Love as foundational reality, and 7 Universal Values: Awareness, Honesty, Accuracy, Competence, Compassion, Loving-kindness, and Joyful-sharing.

**Repository:** github.com/kempt-ai/wisdom-agent

**Tech Stack:**
- Backend: FastAPI + PostgreSQL (with pgvector) + SQLite fallback
- Frontend: Next.js (in development)
- LLM Providers: Anthropic Claude, OpenAI, Google Gemini, Nebius, Ollama
- Vector Memory: ChromaDB (current), migrating to pgvector

---

## What Was Accomplished This Session

### 1. Session Continuity Fix (COMPLETED)

**Problem:** The WA was generating session summaries and 7UV reflections but NOT loading them into new sessions. Each conversation started fresh with no memory of the user's wisdom journey.

**Solution:** Modified two files to add "orientation context" bridging:

#### Modified Files (User has downloaded these):

**`backend/services/conversation_service.py`**
- Added `get_session_orientation_context()` method (lines 118-210)
  - Loads most recent session's summary
  - Loads 7UV reflection scores with visual bars
  - Loads meta-summary (patterns, questions, developments)
  - Returns formatted context string
- Modified `start_session()` to call orientation context automatically
- Modified `end_session()` to update meta-summary when session ends

**`backend/routers/chat.py`**
- Added `build_system_prompt()` helper function
- Added `POST /chat/session-chat` endpoint (full session-aware chat)
- Added `GET /chat/session/{id}/orientation` (view orientation context)
- Added `POST /chat/session/{id}/refresh-orientation` (regenerate context)
- Modified `/complete` to accept optional `session_id` for orientation

**Status:** Files delivered to user, awaiting testing.

### 2. Knowledge Base Architecture (DESIGNED)

Comprehensive architecture designed for:
- Research organization
- Fiction/character interactions (book indexing, character voices, author voices)
- Learning modules (languages, math, concepts)
- Future community sharing

---

## Knowledge Base Architecture Summary

### Core Design Decisions

1. **Indexing Strategy:** User choice with cost disclosure
   - Light index: Summary + key quotes (~5% of original tokens)
   - Standard index: Chapters + characters + 100 passages (~15-25%)
   - Full index: Complete semantic embedding (~120-150%)

2. **Storage Backend:** PostgreSQL + pgvector (existing stack)
   - Simpler than adding dedicated vector DB
   - Sufficient for current scale
   - Abstract behind `VectorStore` interface for future flexibility

3. **Spending Controls:** Global monthly limit (default $20)
   - Disclosure before every costly operation
   - Warning at threshold (default 80%)
   - Hard stop at limit with options to increase

4. **Visibility Model:** Private now, structured for future sharing
   - `private` | `unlisted` | `public` visibility levels
   - Community metadata fields ready but unused

### Data Models

```
KnowledgeCollection
├── id, user_id, project_id (optional)
├── name, description, collection_type
├── visibility, tags[]
└── settings{}

KnowledgeResource
├── id, collection_id, user_id
├── name, description, resource_type
├── source_type, original_content, token_count
├── index_level, index_status
├── index_cost_tokens, index_cost_dollars
├── visibility, metadata{}
└── timestamps

ResourceIndex
├── id, resource_id
├── index_type: "summary" | "structured" | "vector"
├── content (JSON or text)
└── embeddings[]

CharacterProfile (special resource)
├── name, aliases[], description, role
├── voice_profile{vocabulary, speech_patterns, concerns, tone}
├── relationships[], sample_quotes[]
└── source_work, source_author

AuthorVoice (special resource)
├── author_name, era, genres[]
├── style_profile{vocabulary, sentence_structure, themes, tone}
├── sample_passages[], source_works[]

LearningModule (special resource)
├── subject, level, content_type
├── structured_content{} (varies by type)
└── progress_tracking{}

UserSettings (additions)
├── monthly_spending_limit (default $20)
├── spending_warning_threshold (default 0.80)
├── current_month_spending
└── spending_reset_day
```

### Resource Types & Index Options

| Type | Light | Standard | Full |
|------|-------|----------|------|
| Document | Summary, 10 passages | Sections, 100 passages, entities | Complete embedding |
| Fiction Book | Summary, characters, 20 quotes | Chapter summaries, character profiles, themes, 100 passages | Full analysis, dialogue attribution (best-effort) |
| Non-Fiction Book | Summary, arguments, 20 quotes | Chapter summaries, concept glossary, 100 passages | Argument mapping, complete embedding |
| Language Learning | — | Vocabulary embeddings, grammar searchable | — |
| Concept Learning | — | Concept embeddings, prerequisites mapped | — |

### Project ↔ Knowledge Base Integration

Projects can:
- Link to collections (`linked_collections: List[int]`)
- Auto-search KB on every message (`auto_search_knowledge: bool`)
- Limit KB results injected (`knowledge_context_limit: int`)

---

## Next Steps (For New Session)

### Step 1: Create SpendingService

**Why first:** Every costly operation (indexing, LLM calls) needs spending checks.

**File:** `backend/services/spending_service.py`

**Key components:**
```python
class SpendingService:
    TOKEN_COST_PER_1K = {...}  # Cost rates by operation type
    
    def estimate_cost(tokens: int, operation: str) -> float
    def check_can_spend(user_id: int, estimated_cost: float) -> SpendingCheck
    def record_spending(user_id: int, amount: float, operation: str, details: dict)
    def get_spending_summary(user_id: int) -> SpendingSummary
    def reset_monthly_spending(user_id: int)  # Called on reset day
```

**SpendingCheck response:**
```python
@dataclass
class SpendingCheck:
    allowed: bool
    current_spending: float
    estimated_cost: float
    projected_total: float
    limit: float
    remaining: float
    at_warning: bool
    over_limit: bool
```

**Also need:** User settings model updates for spending fields.

---

### Step 2: Create Database Models/Migrations

**Files to create:**
- `backend/models/knowledge_models.py` — Pydantic models
- `backend/database/knowledge_tables.py` — SQLAlchemy models (if using ORM) or raw SQL

**Tables:**
1. `knowledge_collections`
2. `knowledge_resources`
3. `resource_indexes`
4. `character_profiles`
5. `author_voices`
6. `learning_modules`
7. `user_settings` (add spending columns)
8. `spending_history` (audit log)

**Future-ready tables (can create empty):**
9. `shared_resources`
10. `resource_ratings`

---

### Step 3: Create KnowledgeBaseService

**File:** `backend/services/knowledge_base_service.py`

**Key components:**
```python
class KnowledgeBaseService:
    # Collection CRUD
    def create_collection(...) -> Collection
    def get_collection(id) -> Collection
    def list_collections(user_id, project_id=None) -> List[Collection]
    def update_collection(id, ...) -> Collection
    def delete_collection(id) -> bool
    
    # Resource CRUD
    def add_resource(collection_id, content, resource_type, ...) -> Resource
    def get_resource(id) -> Resource
    def list_resources(collection_id) -> List[Resource]
    def delete_resource(id) -> bool
    
    # Indexing (with spending integration)
    def estimate_index_cost(resource_id, index_level) -> CostEstimate
    def index_resource(resource_id, index_level, user_confirmed=False) -> IndexResult
    def get_index(resource_id) -> ResourceIndex
    
    # Search
    def search(query, collections=None, limit=5) -> List[SearchResult]
    def search_by_type(query, resource_type, ...) -> List[SearchResult]
    
    # Special operations
    def extract_characters(book_resource_id) -> List[CharacterProfile]
    def generate_author_voice(author_name, source_works) -> AuthorVoice
```

---

### Step 4: Create API Endpoints

**File:** `backend/routers/knowledge.py`

**Endpoints:**

```
# Collections
POST   /knowledge/collections              — Create collection
GET    /knowledge/collections              — List user's collections
GET    /knowledge/collections/{id}         — Get collection details
PUT    /knowledge/collections/{id}         — Update collection
DELETE /knowledge/collections/{id}         — Delete collection

# Resources
POST   /knowledge/collections/{id}/resources     — Add resource
GET    /knowledge/resources/{id}                 — Get resource
DELETE /knowledge/resources/{id}                 — Delete resource

# Indexing
GET    /knowledge/resources/{id}/index-estimate  — Get cost estimate
POST   /knowledge/resources/{id}/index           — Index resource (with confirmation)
GET    /knowledge/resources/{id}/index           — Get index data

# Search
POST   /knowledge/search                   — Search across collections
GET    /knowledge/search?q=...&collections=...   — Simple search

# Special
POST   /knowledge/resources/{id}/extract-characters  — Extract from book
POST   /knowledge/author-voices                      — Create author voice

# Spending (could be separate router)
GET    /user/spending                      — Get spending summary
GET    /user/spending/history              — Get spending history
PUT    /user/settings/spending-limit       — Update limit
```

---

## Key Files Reference

### Existing Files (User's Codebase)

| File | Purpose | Notes |
|------|---------|-------|
| `backend/services/conversation_service.py` | Session management | **MODIFIED THIS SESSION** |
| `backend/services/reflection_service.py` | 7UV reflections, summaries | Has `get_recent_summaries()`, `load_meta_summary()` |
| `backend/services/memory_service.py` | Vector memory (ChromaDB) | May want to align with KB vector storage |
| `backend/services/fact_check_service.py` | Fact checking | Should integrate with KB search |
| `backend/routers/chat.py` | Chat endpoints | **MODIFIED THIS SESSION** |
| `backend/config.py` | Configuration | Will need spending defaults |

### Files to Create (Next Session)

| File | Purpose |
|------|---------|
| `backend/services/spending_service.py` | Token spending tracking |
| `backend/services/knowledge_base_service.py` | KB operations |
| `backend/models/knowledge_models.py` | Pydantic models |
| `backend/database/knowledge_tables.py` | DB schema |
| `backend/routers/knowledge.py` | KB API endpoints |
| `backend/routers/spending.py` | Spending API endpoints (optional, could be in user router) |

---

## Important Context

### The Dialogue Attribution Problem

User tried to have LLMs attribute dialogue in Pride and Prejudice — it failed. LLMs can't reliably tell who said what in novels.

**Current approach:** 
- "Best effort" attribution for full indexing
- Flag that manual review is recommended
- User built a manual annotation tool (code location unknown)
- Defer sophisticated annotation features to later

### Preparing for WA Website

The user plans to create a public website where:
- Fact checks are published
- Users can share knowledge, sessions, philosophies
- People can pay for their own WA instance

Structure visibility/sharing fields now even though everything is private.

### Spending Philosophy

- No separate "indexing budget" — just one global monthly limit
- Default $20/month, user-configurable
- Disclosure before every operation
- Warning at 80%, hard stop at 100%
- Reset monthly (configurable day)

---

## Testing Checklist (Before Next Session)

User is testing:
1. [ ] Fact checker functionality
2. [ ] Session continuity (does new session load previous context?)
   - Start session, have conversation, end session
   - Start new session
   - Check `GET /chat/session/{id}/orientation`
   - Verify LLM references previous conversation naturally

---

## Questions Resolved This Session

1. **Indexing strategy:** User choice with disclosure (Option B)
2. **Storage backend:** PostgreSQL + pgvector (existing stack)
3. **Spending limits:** Global monthly limit, not per-feature
4. **Community features:** Private for now, structured for future sharing
5. **Dialogue attribution:** Defer sophisticated solution, use best-effort + manual review

---

## Open Questions for Future

1. How to integrate the manual annotation tool user built?
2. Community moderation strategy when sharing goes live?
3. Pricing model for paid WA instances?
4. Self-evolving AI governance constraints?

---

## How to Continue

Start new session with:

> "I'm continuing work on the Wisdom Agent Knowledge Base implementation. Please read the handoff document I'm uploading to understand context, then let's proceed with Step 1: Creating the SpendingService."

Upload this document and any relevant code files (conversation_service.py, config.py, etc.) to give context.
