# Wisdom Agent - Database Layer

PostgreSQL + pgvector database for the Wisdom Agent platform.

## Quick Start

### 1. Start PostgreSQL

```bash
# Start PostgreSQL with pgvector in Docker
docker-compose up -d

# Check it's running
docker-compose ps
```

### 2. Initialize Database

```bash
# Install Python dependencies first
pip install -r requirements.txt

# Run database setup
python -m backend.database.setup_db

# Or with test data
python -m backend.database.setup_db --seed-test-data
```

### 3. Verify Setup

```bash
# Connect to database
docker-compose exec postgres psql -U wisdom_agent -d wisdom_agent_db

# Check tables
\dt

# Check pgvector extension
\dx

# Exit
\q
```

## Database Schema

### Core Tables

- **users** - User accounts (multi-user ready)
- **organizations** - Organizations for collaboration (future)
- **projects** - Learning projects (e.g., "improve_my_spanish")
- **sessions** - Conversation sessions within projects
- **messages** - Individual chat messages
- **session_summaries** - AI-generated session summaries
- **session_reflections** - 7 Universal Values scoring

### Memory Tables

- **memories** - Vector embeddings for semantic search (384-dimensional)

### Future Tables (Democracy & Fact-Checking)

- **claims** - Claims for fact-checking
- **verifications** - Fact-check results from APIs
- **evidence** - Supporting/refuting evidence
- **logical_analyses** - Logical argument analysis

### Future Tables (AI Evolution)

- **reasoning_traces** - Audit trail of AI reasoning
- **evolution_proposals** - Proposed system improvements
- **evolution_log** - Log of actual changes

## Configuration

Database settings in `.env`:

```bash
DB_USER=wisdom_agent
DB_PASSWORD=wisdom_dev_pass
DB_HOST=localhost
DB_PORT=5432
DB_NAME=wisdom_agent_db

# Or use full connection string
DATABASE_URL=postgresql://wisdom_agent:wisdom_dev_pass@localhost:5432/wisdom_agent_db

# Vector dimension (all-MiniLM-L6-v2)
VECTOR_DIMENSION=384
```

## Common Operations

### Reset Database

```bash
# Stop and remove containers
docker-compose down

# Remove volume (deletes all data!)
docker volume rm wisdom-agent_postgres_data

# Start fresh
docker-compose up -d
python -m backend.database.setup_db
```

### Backup Database

```bash
# Backup
docker-compose exec postgres pg_dump -U wisdom_agent wisdom_agent_db > backup.sql

# Restore
docker-compose exec -T postgres psql -U wisdom_agent wisdom_agent_db < backup.sql
```

### View Logs

```bash
docker-compose logs -f postgres
```

## Development

### Adding New Models

1. Edit `backend/database/models.py`
2. Add your SQLAlchemy model
3. Run migrations (future: Alembic)

### Direct Database Access

```python
from backend.database import SessionLocal
from backend.database.models import User, Project

db = SessionLocal()
try:
    users = db.query(User).all()
    for user in users:
        print(user.username)
finally:
    db.close()
```

### Using in FastAPI

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.database import get_db

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

## Architecture Notes

### Vector Similarity Search

The `memories` table uses pgvector for semantic search:

```python
from sqlalchemy import func
from backend.database.models import Memory

# Find similar memories (cosine distance)
similar = db.query(Memory).order_by(
    Memory.embedding.cosine_distance(query_embedding)
).limit(5).all()
```

### Visibility Levels

All user-generated content has visibility controls:

- `PRIVATE` - Only owner can see
- `ORGANIZATION` - Organization members can see
- `PUBLIC` - Everyone can see

### 7 Universal Values

Session reflections track 7 values (0-10 scale):

1. Awareness
2. Honesty
3. Accuracy
4. Competence
5. Compassion
6. Loving-kindness
7. Joyful-sharing

## Troubleshooting

### Connection Refused

```bash
# Check if PostgreSQL is running
docker-compose ps

# If not, start it
docker-compose up -d

# Check logs
docker-compose logs postgres
```

### Extension Error

If you get "extension 'vector' does not exist":

```bash
# Connect as superuser
docker-compose exec postgres psql -U postgres

# Enable extension
CREATE EXTENSION vector;
```

### Port Already in Use

If port 5432 is taken:

```bash
# Change port in .env
DB_PORT=5433

# Restart
docker-compose down
docker-compose up -d
```

## Next Steps (Week 2+)

- [ ] Migrate ChromaDB data to PostgreSQL
- [ ] Update memory_service.py to use PostgreSQL
- [ ] Add Alembic for database migrations
- [ ] Implement user authentication
- [ ] Add multi-user support
- [ ] Build fact-checking features
