# Wisdom Agent

An AI system designed to help individuals and groups grow in wisdom.

## Philosophy

Grounded in **Something Deeperism**:
- Poetic (not literal) relation to Truth
- Pure Love = Reality, chooses everyone
- 7 Universal Values for self-evaluation

### The 7 Universal Values

| Value | Description |
|-------|-------------|
| **Awareness** | Staying present to what's actually happening |
| **Honesty** | Truth-telling even when difficult |
| **Accuracy** | Precision in understanding and communication |
| **Competence** | Doing things well and skillfully |
| **Compassion** | Meeting all beings and their suffering with care |
| **Loving-kindness** | Active goodwill toward everyone |
| **Joyful-sharing** | Generosity and celebration of the good |

## Core Questions

1. **How can AI best help humans select for wisdom?**
2. **How can AI pursue this without overstepping?**

## Quick Start

### Option 1: Without Database (Simpler)

```bash
# 1. Copy environment file and add your API keys
cp .env.example .env
# Edit .env to add your ANTHROPIC_API_KEY

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
python -m uvicorn backend.main:app --reload
```

### Option 2: With Database (Full Setup)

```bash
# 1. Start PostgreSQL with pgvector
docker-compose up -d

# 2. Copy environment file and configure
cp .env.example .env
# Edit .env to add your ANTHROPIC_API_KEY and database settings

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python -m backend.database.setup_db

# 5. Run the server
python -m uvicorn backend.main:app --reload
```

Visit:
- **http://localhost:8000** - Health check
- **http://localhost:8000/docs** - Swagger UI (interactive API docs)
- **http://localhost:8000/redoc** - ReDoc (alternative docs)

**Note:** The database is optional for Week 1 features. The system will use ChromaDB for memory if PostgreSQL is not configured.

## Project Structure

```
wisdom-agent/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Configuration management
│   ├── services/            # Business logic
│   │   ├── philosophy_loader.py  # Layered philosophy system
│   │   ├── llm_router.py         # Multi-LLM provider support
│   │   ├── memory_service.py     # Vector DB (ChromaDB)
│   │   ├── project_service.py    # Learning projects
│   │   ├── file_service.py       # File uploads/downloads
│   │   ├── pedagogy_service.py   # Learning plans & progress
│   │   └── reflection_service.py # 7 Values self-evaluation
│   ├── routers/             # API endpoints
│   │   ├── chat.py          # LLM interactions
│   │   ├── memory.py        # Semantic search
│   │   ├── projects.py      # Project CRUD
│   │   ├── files.py         # File management
│   │   ├── pedagogy.py      # Learning tools
│   │   └── reflection.py    # Self-reflection system
│   ├── models/              # Pydantic models (future)
│   └── database/            # PostgreSQL (Week 2)
├── data/
│   ├── philosophy/
│   │   ├── base/            # Something Deeperism core files
│   │   ├── domains/         # democracy/, corporate/, etc.
│   │   └── organizations/   # Org-specific values
│   ├── conversations/       # Session artifacts
│   ├── projects/            # Learning projects
│   ├── uploads/             # User uploads
│   ├── exports/             # Generated exports
│   └── memory/vector_db/    # ChromaDB storage
├── config/
│   └── llm_providers.json   # LLM configuration
├── requirements.txt
└── .env.example
```

## API Reference

### Health & Info

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Basic health check |
| `/health` | GET | Detailed service status |
| `/philosophy` | GET | Philosophy files info |

### Chat API (`/api/chat/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/providers` | GET | List LLM providers |
| `/providers/{provider}/activate` | POST | Switch active provider |
| `/complete` | POST | Raw LLM completion |
| `/ask` | POST | Philosophy-grounded question |

### Memory API (`/api/memory/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Memory service status |
| `/initialize` | POST | Initialize embedding model |
| `/search` | POST | Semantic similarity search |
| `/store` | POST | Store content with embeddings |
| `/stats` | GET | Database statistics |
| `/projects` | GET | List projects in memory |

### Projects API (`/api/projects/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | List all projects |
| `/` | POST | Create new project |
| `/{name}` | GET | Get project details |
| `/{name}` | DELETE | Delete project |
| `/{name}/sessions` | GET/POST | Session management |
| `/{name}/resources` | GET/POST | Resource management |
| `/{name}/journal` | GET/POST | Journal entries |
| `/{name}/progress` | GET/POST | Progress tracking |
| `/{name}/outline` | GET | Full project outline |
| `/{name}/learning-plan` | GET/PUT | Learning plan management |

### Files API (`/api/files/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Service status & capabilities |
| `/stats` | GET | File statistics |
| `/upload` | POST | Upload file |
| `/uploads` | GET | List uploaded files |
| `/download` | GET | Download file |
| `/extract-text` | POST | Extract text from PDF/DOCX |
| `/project/{name}` | GET | List project files |

### Pedagogy API (`/api/pedagogy/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Service status |
| `/initialize` | POST | Initialize service |
| `/learning-plan` | POST | Generate personalized learning plan |
| `/detect-session-type` | POST | Classify session type |
| `/pedagogical-reflection` | POST | Reflect on learning session |
| `/progress-update` | POST | Generate progress assessment |
| `/suggest-next-topics` | POST | Suggest next study topics |

### Reflection API (`/api/reflection/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Service status |
| `/initialize` | POST | Initialize service |
| `/values` | GET | Get 7 Universal Values info |
| `/values-reflection` | POST | **Generate 7 Values self-evaluation** |
| `/session-summary` | POST | Generate session summary |
| `/save-artifacts` | POST | Save session files |
| `/meta-summary` | GET | Get evolving meta-summary |
| `/meta-summary/update` | POST | Update meta-summary |
| `/recent-summaries` | GET | Get recent summaries |
| `/values-trend` | GET | Analyze values trend |
| `/complete-session` | POST | **Full session workflow (all-in-one)** |

## Usage Examples

### Initialize Services

```bash
# Initialize LLM-dependent services
curl -X POST http://localhost:8000/api/pedagogy/initialize
curl -X POST http://localhost:8000/api/reflection/initialize
```

### Create a Learning Project

```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Learn Spanish",
    "project_type": "learning",
    "description": "Improve my Spanish",
    "learning_goal": "Conversational fluency"
  }'
```

### Generate a Learning Plan

```bash
curl -X POST http://localhost:8000/api/pedagogy/learning-plan \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Spanish Language",
    "current_level": "Complete beginner",
    "learning_goal": "Hold basic conversations",
    "time_commitment": "30 minutes per day"
  }'
```

### Generate 7 Universal Values Reflection

```bash
curl -X POST http://localhost:8000/api/reflection/values-reflection \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "messages": [
      {"role": "user", "content": "What is wisdom?"},
      {"role": "assistant", "content": "Wisdom involves integrating knowledge with good judgment..."}
    ]
  }'
```

### Complete a Full Session

```bash
curl -X POST "http://localhost:8000/api/reflection/complete-session?session_id=1" \
  -H "Content-Type: application/json" \
  -d '[
    {"role": "user", "content": "Hello, I want to explore what it means to live wisely."},
    {"role": "assistant", "content": "That is a beautiful question to contemplate..."}
  ]'
```

## Database (PostgreSQL + pgvector)

**Status:** Week 2 - Foundation Complete

The Wisdom Agent uses PostgreSQL with pgvector for:
- User accounts & projects
- Session data & conversations
- Vector embeddings for semantic memory search
- 7 Universal Values scoring and tracking

### Quick Database Setup

```bash
# Start PostgreSQL
docker-compose up -d

# Initialize schema
python -m backend.database.setup_db

# Check status
docker-compose ps
```

### Database Schema

**Core Tables:**
- `users` - User accounts (multi-user ready)
- `projects` - Learning projects
- `sessions` - Conversation sessions
- `messages` - Chat messages
- `session_summaries` - AI-generated summaries
- `session_reflections` - 7 Values scoring

**Memory Tables:**
- `memories` - Vector embeddings (384-dimensional)

**Future Tables:**
- `claims`, `verifications`, `evidence` - Fact-checking
- `reasoning_traces`, `evolution_log` - AI evolution tracking

For detailed database documentation, see [`backend/database/README.md`](backend/database/README.md).

### Hybrid Memory Service (Week 2 Day 2)

The Wisdom Agent now features an intelligent hybrid memory system:

**Primary Backend: PostgreSQL + pgvector**
- Production-ready vector storage
- Semantic similarity search with cosine distance
- Scalable to millions of memories
- Multi-user ready with isolation
- Full ACID compliance

**Fallback Backend: ChromaDB**
- Development-friendly
- No database setup required
- Perfect for prototyping

The system automatically selects the best available backend:
1. If `DATABASE_URL` is configured → Uses PostgreSQL
2. Otherwise → Falls back to ChromaDB

**Test the memory system:**
```bash
# Initialize memory service
curl -X POST http://localhost:8000/api/memory/initialize

# Check which backend is active
curl http://localhost:8000/api/memory/status
```

**Migrate from ChromaDB to PostgreSQL:**
```bash
python -m backend.database.migrate_chromadb --dry-run  # Test first
python -m backend.database.migrate_chromadb           # Actual migration
```

See [`TESTING_GUIDE_DAY2.md`](TESTING_GUIDE_DAY2.md) for comprehensive testing instructions.

### Database Configuration

In `.env`:

```bash
DB_USER=wisdom_agent
DB_PASSWORD=wisdom_dev_pass
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wisdom_agent_db
```

## LLM Providers

Supported providers (configure in `.env`):

| Provider | Required Env Var | Notes |
|----------|-----------------|-------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude models (recommended) |
| OpenAI | `OPENAI_API_KEY` | GPT-4 models |
| Nebius | `NEBIUS_API_KEY` | Llama models |
| Local | - | Ollama (localhost:11434) |

## Optional Dependencies

The memory service requires additional packages:

```bash
# For semantic memory features
pip install sentence-transformers chromadb
```

The app will run without these, but memory/search features will be disabled.

## Migration Status

**Week 1 Complete:**
- ✅ FastAPI backend structure
- ✅ Configuration management
- ✅ Philosophy loader with layered system
- ✅ LLM Router (multi-provider)
- ✅ Memory Service (ChromaDB)
- ✅ Project Service (CRUD + learning plans)
- ✅ File Service (upload/download/extract)
- ✅ Pedagogy Service (learning plans, progress)
- ✅ Reflection Service (7 Values self-evaluation)
- ✅ All API endpoints functional
- ✅ Integration tested

**Week 2 Days 1-2 Complete:**
- ✅ Day 1: Database foundation (PostgreSQL + pgvector setup, SQLAlchemy models)
- ✅ Day 2: Hybrid memory service (PostgreSQL primary, ChromaDB fallback)
- ✅ Day 2: Vector similarity search with pgvector
- ✅ Day 2: Migration script (ChromaDB → PostgreSQL)
- 🚧 Days 3-5: Session & conversation management, testing, integration

**Coming Next:**
- Days 3-5: Complete session/conversation migration to PostgreSQL
- Week 3+: Next.js frontend
- Future: User authentication, fact-checking features

## Contributing

This is an open-source project designed to help individuals and groups grow in wisdom. Contributions welcome!

## License

MIT License

---

*"How can AI best help humans select for wisdom without overstepping?"*
