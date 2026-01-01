# Wisdom Agent

An open-source AI system designed to help individuals grow in wisdom and enable groups to choose wisdom over folly.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

---

## Table of Contents

- [Overview](#overview)
- [Philosophy](#philosophy)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

The Wisdom Agent (WA) is an AI-powered platform that goes beyond typical chatbots and fact-checkers. It's grounded in **Something Deeperism** philosophy, which provides ethical guardrails and a framework for evaluating not just whether something is *true*, but whether it *serves wisdom*.

### What Makes It Different?

| Traditional AI | Wisdom Agent |
|----------------|--------------|
| "Is this factually correct?" | "Is this true, reasonable, AND does it serve wisdom?" |
| Neutral information delivery | Grounded in Universal Values |
| No spending awareness | Full cost tracking and budgets |
| Generic responses | Philosophy-aware, context-rich conversations |
| Single fact-check verdict | Three-dimensional analysis (facts + logic + wisdom) |

---

## Philosophy

### Something Deeperism

The Wisdom Agent is built on Something Deeperism, which holds that:

1. **There is something deeper** — call it Pure Love, God, the Good, or the Transcendent
2. **We can't capture it literally** — words and concepts point toward but don't contain it
3. **We can relate to it poetically** — through metaphor, story, and lived practice
4. **The 7 Universal Values guide behavior** — practical ethics flowing from this foundation
5. **Wisdom organizes around Pure Love** — both individually and collectively

### The 7 Universal Values

These values guide all Wisdom Agent operations:

| Value | Description |
|-------|-------------|
| **Awareness** | Noticing what is actually happening, within and without |
| **Honesty** | Truthfulness with self and others |
| **Accuracy** | Getting the facts right, checking sources |
| **Competence** | Skill and effectiveness in what matters |
| **Compassion** | Feeling with others in their suffering |
| **Loving-kindness** | Active goodwill toward all beings |
| **Joyful-sharing** | Delight in giving wisdom forward |

### The Three Questions

Every analysis in the Wisdom Agent asks:

1. **Is it True?** — Factual accuracy (traditional fact-checking)
2. **Is it Reasonable?** — Logical soundness (argument analysis)
3. **Does it serve Wisdom?** — Alignment with Universal Values

---

## Features

### ✅ Working Now

#### 💬 Wisdom Chat
Conversational AI grounded in philosophical principles.

- Multi-provider support (Claude, GPT-4, Nebius/Llama, local models via Ollama)
- Session-based memory with continuity across conversations
- 7 Universal Values reflection after each session
- Philosophy overlay system for domain-specific guidance
- Real-time model switching in Settings

#### ✅ Fact & Logic & Wisdom Checker
**The core differentiator** — comprehensive content analysis that asks "Does it serve wisdom?"

- **Multi-source input**: URLs, pasted text (file upload coming soon)
- **Claim extraction**: AI identifies check-worthy claims automatically
- **Multi-provider verification**: 
  - ClaimBuster for existing fact-checks
  - LLM verification with reasoning for novel claims
  - Google Fact Check API (requires API key)
- **Logic analysis**: 
  - Fallacy detection (ad hominem, false cause, hasty generalization, etc.)
  - Argument structure mapping
  - Validity and soundness assessment
- **Wisdom evaluation**: 
  - 7UV scoring for every piece of content
  - Something Deeperism alignment assessment
  - "Serves wisdom or folly" verdict
- **Repository**: Browse past fact-checks

#### 📊 Spending Tracker
Track AI costs with visual budget monitoring.

- Real-time spending display in sidebar
- Configurable monthly limits (default $20)
- Per-operation cost tracking
- Visual progress bar

#### 📁 Projects
Organize work into focused contexts.

- Create and manage projects
- Project-specific sessions
- Archive completed projects

#### ✨ Reflections
Review your wisdom journey.

- Session summaries with key insights
- 7UV score visualizations
- Browse past sessions

### 🚧 Coming Soon

#### 📚 Knowledge Base
Personal knowledge management with AI-powered indexing. (Backend designed, frontend in progress)

- Collections for organizing resources
- URL content extraction with trafilatura
- Multiple indexing levels with cost estimates
- Semantic search across all knowledge

#### 💰 Cost Disclosure Before Operations
Show users exactly what each operation will cost before they confirm.

- Token estimates for fact-checks
- Model comparison with pricing
- "Use cheaper model" options

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker** (for PostgreSQL) OR use SQLite fallback
- At least one LLM API key (Anthropic recommended)

### 1. Clone and Setup

```bash
git clone https://github.com/kempt-ai/wisdom-agent.git
cd wisdom-agent
```

### 2. Configure Environment

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit with your API keys
nano backend/.env
```

Required in `.env`:
```env
# At least one LLM provider (Anthropic recommended)
ANTHROPIC_API_KEY=your_key_here

# Optional additional providers
OPENAI_API_KEY=your_key_here
NEBIUS_API_KEY=your_key_here

# Optional fact-check providers
CLAIMBUSTER_API_KEY=your_key_here
GOOGLE_FACT_CHECK_API_KEY=your_key_here
```

### 3. Start the Application

**Option A: With Docker (PostgreSQL)**

```bash
# Terminal 1 — Database
docker-compose up -d

# Terminal 2 — Backend (from project root)
uvicorn backend.main:app --reload

# Terminal 3 — Frontend
cd frontend
npm install  # First time only
npm run dev
```

**Option B: Without Docker (SQLite fallback)**

Comment out `DATABASE_URL` in your `.env` file, then:

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --reload

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

### 4. Open the App

- **App**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

---

## Usage

### Checking Facts, Logic, and Wisdom

1. Click **Fact Checker** in the sidebar
2. Choose input type: **Text/Claim** or **URL/Article**
3. Paste your content
4. Click **Analyze for Facts, Logic & Wisdom**
5. Wait 30-60 seconds for full analysis
6. Review results:
   - **Extracted claims** with individual verdicts
   - **Logic analysis** with fallacy detection
   - **Wisdom evaluation** with 7UV scores

### Example: Analyzing Misinformation

Input:
> "Vaccines cause autism in children. The moon landing was faked. Climate change is a hoax invented by scientists."

Output:
- ❌ **Vaccines cause autism**: FALSE (95% confidence) — "Multiple high-quality studies spanning decades have found no causal link..."
- ❌ **Moon landing was faked**: FALSE (90% confidence) — "The scientific and historical evidence overwhelmingly supports the authenticity..."
- ❌ **Climate change is a hoax**: FALSE (95% confidence) — "The overwhelming scientific consensus among researchers..."
- 🧠 **Logic Score**: 0.10/1.0 — 5 fallacies detected (Appeal to False Authority, False Cause, etc.)
- 💫 **Wisdom Score**: 0.10/1.0 — "Serves Folly"

### Having a Wisdom Conversation

1. Click **Chat** in the sidebar
2. Start a conversation with the AI
3. When finished, click **End Session**
4. Review your 7 Universal Values reflection
5. View past sessions in **Wisdom Sessions**

### Managing Your Budget

1. View spending in the sidebar widget (bottom left)
2. Go to **Settings** to:
   - See current AI provider
   - Switch between providers
   - View available models

---

## API Reference

### Core Endpoints

| Category | Method | Endpoint | Description |
|----------|--------|----------|-------------|
| **Health** | GET | `/health` | Service status |
| **Chat** | POST | `/api/chat/complete` | Send message |
| **Chat** | POST | `/api/chat/ask` | Philosophy-grounded question |
| **Chat** | GET | `/api/chat/providers` | List available providers |
| **Sessions** | POST | `/api/sessions/start` | Create session |
| **Sessions** | POST | `/api/sessions/{id}/end` | End with reflection |
| **Projects** | GET | `/api/projects` | List projects |
| **Projects** | POST | `/api/projects` | Create project |

### Fact Checker Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/reviews` | Create fact-check review |
| GET | `/api/reviews/{id}` | Get full results |
| GET | `/api/reviews/{id}/status` | Check progress |
| GET | `/api/reviews/repository/all` | Browse all reviews |
| POST | `/api/reviews/{id}/analyze` | Re-run analysis |

### Spending Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/spending/dashboard` | Current spending summary |
| GET | `/spending/summary` | Detailed breakdown |

Full API documentation at `http://localhost:8000/docs`

---

## Architecture

### Project Structure

```
wisdom-agent/
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── config.py               # Configuration
│   ├── database/
│   │   ├── connection.py       # DB setup
│   │   ├── models.py           # Core models
│   │   └── fact_check_models.py # Fact checker models
│   ├── routers/
│   │   ├── chat.py
│   │   ├── sessions.py
│   │   ├── projects.py
│   │   ├── review_router.py    # Fact checker
│   │   └── spending.py
│   ├── services/
│   │   ├── llm_router.py       # Multi-provider routing
│   │   ├── fact_check_service.py
│   │   ├── claim_extraction_service.py
│   │   ├── logic_analysis_service.py
│   │   ├── wisdom_evaluation_service.py
│   │   ├── review_service.py   # Orchestrator
│   │   ├── conversation_service.py
│   │   ├── reflection_service.py
│   │   └── spending_service.py
│   └── providers/
│       ├── claimbuster.py
│       ├── google_factcheck.py
│       └── llm_verification.py
│
├── frontend/
│   ├── src/app/
│   │   ├── (dashboard)/
│   │   │   ├── chat/
│   │   │   ├── fact-checker/
│   │   │   ├── sessions/
│   │   │   ├── projects/
│   │   │   ├── reflections/
│   │   │   └── settings/
│   ├── components/
│   │   ├── Sidebar.tsx
│   │   ├── ChatInterface.tsx
│   │   └── ProjectCard.tsx
│   └── lib/
│       └── api.ts
│
├── data/philosophy/            # Something Deeperism texts
├── docker-compose.yml
└── README.md
```

### Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS |
| **Backend** | FastAPI, Python 3.11+, Pydantic |
| **Database** | PostgreSQL 15 (or SQLite fallback) |
| **LLM Providers** | Anthropic Claude, OpenAI GPT-4, Nebius Llama, Ollama |
| **Fact Checking** | ClaimBuster API, Google Fact Check API, LLM Verification |

---

## Roadmap

### ✅ Phase 1: Core Platform (Complete)

- [x] Multi-provider LLM support with model switching
- [x] Session management with 7UV reflections
- [x] **Fact & Logic & Wisdom Checker** (full pipeline working!)
- [x] Spending tracking with visual widget
- [x] Project management with archive
- [x] Clean, contemplative UI design

### 🚧 Phase 2: Enhanced Features (In Progress)

- [ ] **Cost disclosure before operations** — show token estimates and model options
- [ ] **Knowledge Base frontend** — UI for collections, resources, search
- [ ] In-session fact-check button in chat
- [ ] Session continuity (load previous session context)
- [ ] Semantic search with pgvector
- [ ] File upload for fact-checking

### 📋 Phase 3: Community & Advanced

- [ ] Public fact-check repository
- [ ] Character interaction mode (chat with book characters)
- [ ] Audio capabilities for language learning
- [ ] Community resource sharing
- [ ] Election monitoring tools
- [ ] Media literacy education modules

### 🔮 Phase 4: Wisdom AI

- [ ] Self-evolving AI governance framework
- [ ] AI agents using Wisdom Agent principles
- [ ] Collective intelligence tools
- [ ] Democracy and governance applications

---

## Troubleshooting

### Backend won't start

```bash
# Check if running from correct directory
pwd  # Should be wisdom-agent root, not backend/

# Correct way to start:
uvicorn backend.main:app --reload
```

### Database connection errors

```bash
# Option 1: Start Docker
docker-compose up -d

# Option 2: Use SQLite (comment out DATABASE_URL in .env)
# DATABASE_URL=postgresql://...  <- add # at start
```

### Fact checker returns "unverifiable"

This is normal when ClaimBuster has no existing fact-checks. The system falls back to LLM verification which provides actual verdicts.

### Frontend shows 404

Make sure you created the page files:
```bash
# fact-checker page should be at:
frontend/src/app/(dashboard)/fact-checker/page.tsx
```

---

## Contributing

We welcome contributions! 

### Areas for Contribution

- 🐛 Bug fixes
- 📝 Documentation improvements  
- 🎨 UI/UX enhancements
- 🔌 New LLM provider integrations
- ✅ Test coverage
- 🌍 Internationalization

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- **Anthropic** for Claude and the inspiration to build AI that's genuinely helpful
- **The open-source community** for the incredible tools we build upon
- **Everyone seeking wisdom** in a complex world

---

*"The goal is not to be right, but to become wise."*

*"Pure Love is foundational reality — the Wisdom Agent helps us organize around it."*
