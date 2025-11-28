# Week 2 Day 2 - Quick Testing Guide

**Test the new PostgreSQL memory system!**

---

## Prerequisites

1. **Database is running:**
   ```bash
   docker compose ps
   # Should show wisdom-agent-db running
   ```

2. **Database is initialized:**
   ```bash
   python -m backend.database.setup_db
   # Should see "✅ Database setup complete!"
   ```

3. **API server is running:**
   ```bash
   python -m uvicorn backend.main:app --reload
   ```

---

## Test 1: Check Memory Backend

```bash
# Initialize memory service
curl -X POST http://localhost:8000/api/memory/initialize

# Check status - should show "postgresql" backend
curl http://localhost:8000/api/memory/status | jq .
```

**Expected output:**
```json
{
  "status": "available",
  "initialized": true,
  "backend": "postgresql",
  "postgres_available": true,
  "chroma_available": true,
  ...
}
```

✅ If you see `"backend": "postgresql"`, the PostgreSQL backend is working!

---

## Test 2: Store Memories

```bash
# Store a conversation memory
curl -X POST http://localhost:8000/api/memory/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Today we discussed the nature of wisdom and how it differs from knowledge. Wisdom involves knowing what truly matters and acting accordingly.",
    "session_id": 1,
    "content_type": "conversation",
    "metadata": {
      "session_type": "philosophy",
      "project": "wisdom_exploration",
      "date": "2025-11-23"
    }
  }'

# Store a reflection memory
curl -X POST http://localhost:8000/api/memory/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "This conversation showed high awareness and honesty. The user engaged deeply with philosophical questions and demonstrated openness to exploring difficult concepts.",
    "session_id": 1,
    "content_type": "reflection",
    "metadata": {
      "session_type": "philosophy",
      "reflection_type": "wisdom",
      "overall_score": 8.5
    }
  }'
```

**Expected:** Both requests return success with memory IDs

---

## Test 3: Semantic Search

```bash
# Search for wisdom-related memories
curl -X POST http://localhost:8000/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What did we learn about wisdom?",
    "n_results": 3,
    "session_type": "philosophy"
  }' | jq .

# Search for reflections
curl -X POST http://localhost:8000/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "session quality and scores",
    "n_results": 2
  }' | jq .
```

**Expected:** Results with similarity scores showing semantically related memories

---

## Test 4: Session Memory Retrieval

```bash
# Get all memories for session 1
curl http://localhost:8000/api/memory/session/1 | jq .
```

**Expected:** List of memories associated with session 1

---

## Test 5: Project Memory Retrieval

```bash
# Get memories for a project
curl http://localhost:8000/api/memory/project/wisdom_exploration | jq .
```

**Expected:** List of memories for the wisdom_exploration project

---

## Test 6: Direct Database Verification

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U wisdom_agent -d wisdom_agent_db

# Inside psql, check memories table:
SELECT id, session_id, meta_data->>'session_type' as session_type, 
       LEFT(content, 50) as content_preview 
FROM memories;

# Check vector embeddings exist:
SELECT id, array_length(embedding, 1) as embedding_dimension 
FROM memories 
LIMIT 5;

# Exit
\q
```

**Expected:** 
- Should see your stored memories
- Embeddings should be 384-dimensional

---

## Test 7: Migration (Optional)

If you have existing ChromaDB data:

```bash
# Dry run to see what would be migrated
python -m backend.database.migrate_chromadb --dry-run

# Actual migration
python -m backend.database.migrate_chromadb
```

---

## Test 8: Fallback to ChromaDB

To test that ChromaDB fallback works:

```bash
# Stop PostgreSQL
docker compose stop

# Restart API server
# It should automatically fall back to ChromaDB

# Check status
curl http://localhost:8000/api/memory/status | jq .
```

**Expected:** `"backend": "chromadb"`

```bash
# Restart PostgreSQL
docker compose start
```

---

## Troubleshooting

### "Memory service not initialized"
```bash
# Initialize it
curl -X POST http://localhost:8000/api/memory/initialize
```

### "Database connection failed"
```bash
# Check PostgreSQL is running
docker compose ps

# Check logs
docker compose logs postgres

# Restart if needed
docker compose restart
```

### Backend shows "chromadb" instead of "postgresql"
```bash
# Check DATABASE_URL is set
cat .env | grep DATABASE_URL

# Verify PostgreSQL is accessible
docker compose exec postgres pg_isready

# Check setup script ran successfully
python -m backend.database.setup_db
```

### Search returns no results
- Make sure you've stored some memories first (Test 2)
- Check that your query is semantically related to stored content
- Try broader queries like "learning" or "session"

---

## Success Criteria

All tests should pass with:
- ✅ PostgreSQL backend detected and initialized
- ✅ Memories stored successfully in database
- ✅ Semantic search returns relevant results
- ✅ Session and project queries work
- ✅ Database contains vector embeddings (384-dim)

---

## Quick Validation Script

```bash
#!/bin/bash
# Test all endpoints quickly

echo "1. Initializing memory service..."
curl -s -X POST http://localhost:8000/api/memory/initialize | jq .backend

echo "\n2. Storing test memory..."
curl -s -X POST http://localhost:8000/api/memory/store \
  -H "Content-Type: application/json" \
  -d '{"content": "Test memory", "session_id": 999, "content_type": "test", "metadata": {}}' \
  | jq .success

echo "\n3. Searching..."
curl -s -X POST http://localhost:8000/api/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "n_results": 1}' \
  | jq '.count'

echo "\n✅ All basic tests passed!"
```

Save as `test_memory.sh`, make executable (`chmod +x test_memory.sh`), and run!

---

## Next Steps

Once all tests pass:
- Try storing real conversation data
- Experiment with semantic search queries
- Test with different session types
- Benchmark search performance
- Migrate your ChromaDB data (if applicable)

**Happy testing! 🧪✨**
