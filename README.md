# Wisdom Agent

An open-source AI platform that helps individuals grow in wisdom through philosophical grounding in "Something Deeperism" and the 7 Universal Values framework.

## 🌟 Vision

Wisdom Agent is designed as a three-layer system:

1. **Open Source WA** (Current Focus) - Downloadable, self-hostable, customizable
2. **Public Platform** (Future) - Hosted WA with F/L/W archive, democracy wiki, micropayments
3. **Wisdom AI** (Long-term) - Self-evolving AI constrained by wisdom principles with human oversight

## ✨ Current Features

### Chat & Wisdom Sessions
- AI conversations grounded in wisdom philosophy
- Session memory and context across conversations
- Automatic summary generation after sessions
- 7 Universal Values self-assessment scoring
- Project-based organization for different contexts
- Philosophy grounding at session start

### Knowledge Base
- Create collections to organize research
- Index web content and documents
- Searchable knowledge repository
- Resource tagging and categorization
- Cost estimation for indexing operations
- Project-level organization
- **Resource parsing** - Extract structured arguments from articles (thesis, claims, evidence)
- Multiple parse levels: Light (quick overview), Standard (balanced), Full (comprehensive)

*Status: Fully functional with parsing capabilities.*

### Investigation Builder ✨ NEW

Build structured, navigable arguments from your research. The Investigation Builder transforms Knowledge Base resources into comprehensive investigations:

#### Core Features
- **Readable prose with embedded links** - Investigations read naturally, with colored links to definitions (blue) and claims (orange)
- **Slide-out panel navigation** - Click any link to see details without losing context
- **Hierarchical arguments** - Claims can link to sub-investigations for complex argument trees
- **Rich evidence with supporting quotes** - Capture not just one quote, but the full context including examples and data

#### Knowledge Base Integration
- **Search KB from evidence editor** - Find and link resources without leaving your investigation
- **Browse parsed content** - Select specific claims, quotes, or examples from parsed articles
- **Auto-fill evidence fields** - Selecting parsed content populates the evidence form automatically
- **Supporting quotes bundled** - When you select a claim, its supporting evidence comes with it
- **"View in parse" links** - Click through from evidence back to the exact location in the source
- **Auto-add to KB** - Add new sources to your Knowledge Base while creating evidence

#### Content Management
- Create and edit investigations, definitions, claims, and evidence through the UI
- Clickable definition and claim cards
- Status tracking (ongoing, resolved, historical, superseded)
- Evidence credibility metadata (source type, key quotes, key points)

*Status: Core features complete including counterarguments and reordering. Credibility assessment planned.*

See [ARGUMENT\_BUILDER\_DESIGN.md][1] for full specification.

### Fact/Logic/Wisdom Checker

> ⚠️ **Status: Hidden from UI** - The F/L/W Checker backend is functional but currently hidden from the interface. Early testing revealed the analysis tends toward overly pedantic, uncharitable readings—ironically failing its own wisdom standards. We're pausing UI exposure while we improve the prompts and calibration. The backend code remains intact and the API endpoints work for testing.

Analyze any content across three dimensions:

| Dimension   | Question                | What It Checks                                            |
| ----------- | ----------------------- | --------------------------------------------------------- |
| **Factual** | Is it True?             | Verifies claims against web sources, fact-check databases |
| **Logical** | Is it Reasonable?       | Analyzes argument structure, identifies reasoning issues  |
| **Wisdom**  | Does it Support Wisdom? | Evaluates whether content supports conditions for wisdom  |

### Philosophy Framework

Built on **Something Deeperism** - a philosophical approach that:
- Seeks deeper truth beneath surface appearances
- Acknowledges we can't capture Truth literally, only point toward it
- Emphasizes epistemic humility while still reasoning toward better understanding
- Distinguishes between private wisdom (experiential) and public wisdom (assessable form)
- Grounds all activity in the 7 Universal Values

**The 7 Universal Values:**

| Value               | Description                                              |
| ------------------- | -------------------------------------------------------- |
| **Awareness**       | Being present and attentive to what's actually happening |
| **Honesty**         | Truthfulness with self and others                        |
| **Accuracy**        | Precision in thought and expression                      |
| **Competence**      | Skillful action and understanding                        |
| **Compassion**      | Care for the suffering of others                         |
| **Loving-kindness** | Active goodwill toward all beings                        |
| **Joyful-sharing**  | Generous spirit in community                             |

### Multi-LLM Support
Supports multiple AI providers with transparent pricing:

| Provider      | Models                                             | Best For                      |
| ------------- | -------------------------------------------------- | ----------------------------- |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus | Nuanced reasoning, safety     |
| **OpenAI**    | GPT-4o, GPT-4o Mini, GPT-4 Turbo                   | Versatility, speed            |
| **Google**    | Gemini 2.0 Flash, Gemini 1.5 Pro                   | Cost-effective, large context |
| **Nebius**    | Llama 3.3 70B, DeepSeek V3, Mixtral                | Budget-friendly               |
| **Local**     | Ollama (Mistral, Llama, Phi-3)                     | Free, private, offline        |

### Budget Management
- Set monthly spending limits
- Cost estimation before all LLM operations
- Detailed usage tracking and history
- Per-operation cost breakdown
- Spending dashboard with visualizations

### Session Management
- Automatic session summaries
- 7 Values self-reflection scoring after chat sessions
- Session history and search
- Project-based session organization

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL (recommended) or SQLite (fallback)
- Docker (optional, for PostgreSQL)

### Option 1: With Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/kempt-ai/wisdom-agent.git
cd wisdom-agent

# Start PostgreSQL with Docker
docker-compose up -d

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Start the backend
uvicorn backend.main:app --reload
```

### Option 2: Without Docker (SQLite)

```bash
# Clone and set up as above, but skip docker-compose
# The app will automatically use SQLite if no DATABASE_URL is set
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` to access the application.

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:

```bash
# Required: At least one LLM provider
ANTHROPIC_API_KEY=your_key_here      # Recommended primary
OPENAI_API_KEY=your_key_here         # Optional
GOOGLE_API_KEY=your_key_here         # Optional (also enables Google Fact Check)
NEBIUS_API_KEY=your_key_here         # Optional (budget-friendly)

# Database (optional - defaults to SQLite if not set)
DATABASE_URL=postgresql://postgres:password@localhost:5432/wisdom_agent

# Fact-checking providers (optional - enhances F/L/W when re-enabled)
CLAIMBUSTER_API_KEY=your_key_here    # Academic fact-check database
# Google Fact Check API uses GOOGLE_API_KEY above
```

### Database Options
- **PostgreSQL** (recommended): Better performance, vector search support, required for production
- **SQLite** (default): No setup required, great for development and personal use

## 📂 Project Structure

```
wisdom-agent/
├── backend/
│   ├── main.py              # FastAPI application entry
│   ├── routers/             # API endpoints
│   │   ├── review_router.py      # Fact/Logic/Wisdom checker (hidden from UI)
│   │   ├── knowledge.py          # Knowledge base
│   │   ├── arguments.py          # Resource parsing
│   │   ├── ab_router.py          # Investigation Builder API
│   │   ├── chat.py               # Chat sessions
│   │   ├── sessions.py           # Session management
│   │   └── spending.py           # Budget tracking
│   ├── services/            # Business logic
│   │   ├── review_service.py          # F/L/W pipeline orchestrator
│   │   ├── fact_check_service.py      # Fact verification
│   │   ├── logic_analysis_service.py  # Logic analysis
│   │   ├── wisdom_evaluation_service.py # Wisdom assessment
│   │   ├── claim_extraction_service.py  # Claim extraction
│   │   ├── knowledge_service.py       # Knowledge base
│   │   ├── parsing_service.py         # Resource parsing for arguments
│   │   ├── ab_service.py              # Investigation Builder logic
│   │   ├── reflection_service.py      # Session reflections
│   │   ├── llm_router.py              # Multi-LLM routing
│   │   └── web_search_service.py      # Web search
│   ├── providers/           # External API integrations
│   │   ├── llm_verification.py   # LLM + web search verification
│   │   ├── google_factcheck.py   # Google Fact Check API
│   │   └── claimbuster.py        # ClaimBuster API
│   ├── database/            # DB models and connections
│   │   ├── argument_tables.py    # Parsing data models
│   │   └── ab_tables.py          # Investigation Builder tables
│   └── models/              # Pydantic request/response models
│       ├── argument_models.py    # Parsing schemas
│       └── ab_schemas.py         # Investigation Builder schemas
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages
│       │   ├── (dashboard)/ # Main app pages
│       │   │   ├── fact-checker/   # F/L/W Checker UI (hidden)
│       │   │   ├── knowledge/      # Knowledge Base UI
│       │   │   ├── investigations/ # Investigation Builder UI
│       │   │   └── chat/           # Chat interface
│       │   └── page.tsx     # Landing page
│       ├── components/      # React components
│       │   └── arguments/   # Investigation Builder components
│       │       ├── InvestigationOverview.tsx
│       │       ├── SlideOutPanel.tsx
│       │       ├── DefinitionView.tsx
│       │       ├── DefinitionEditor.tsx
│       │       ├── ClaimView.tsx
│       │       ├── ClaimEditor.tsx
│       │       ├── EvidenceCard.tsx
│       │       ├── EvidenceEditor.tsx
│       │       ├── CounterargumentCard.tsx
│       │       ├── CounterargumentEditor.tsx
│       │       ├── KBResourcePicker.tsx
│       │       └── InvestigationEditor.tsx
│       └── lib/             # Utilities and API client
│           ├── api.ts
│           ├── knowledge-api.ts
│           └── arguments-api.ts
├── data/
│   └── philosophy/          # Philosophy text files
│       └── base/            # Core philosophy documents
└── config/
    └── llm_providers.json   # LLM provider configuration
```

## 🔍 Troubleshooting

### Backend won't start
- Check that at least one LLM API key is set in `.env`
- Ensure PostgreSQL is running if using `DATABASE_URL`
- Check Python dependencies: `pip install -r requirements.txt`
- Look for error messages in terminal output

### "Knowledge Base tables" warnings
- Usually harmless if tables already exist
- If KB isn't working, verify PostgreSQL connection

### Frontend not updating
- Stop and restart: `npm run dev`
- Clear Next.js cache: `rm -rf frontend/.next && npm run dev`
- Check for TypeScript errors in terminal

### Pydantic namespace warnings
These warnings appear on startup but don't break functionality:
```
Field "model_id" has conflict with protected namespace "model_".
```
This is cosmetic and can be ignored.

### F/L/W Checker (for developers testing the hidden feature)
- API endpoints remain functional at `/review/*`
- Check backend logs for debug output
- External APIs (ClaimBuster) may be unavailable; system falls back to LLM verification

## 🎯 Development Status

### Active ✅
- Multi-LLM support with 5 providers (Anthropic, OpenAI, Google, Nebius, Ollama)
- Chat with wisdom grounding
- Budget tracking and spending limits
- Session summaries and 7 Values reflections
- Knowledge Base with resource parsing
- Project-based organization
- **Investigation Builder** - Core features complete:
  - Investigations with definitions and claims
  - Slide-out panel navigation
  - Rich evidence with supporting quotes
  - KB integration (search, browse parses, auto-add)
  - Sub-investigation linking for hierarchical arguments
  - "View in parse" links for source traceability
  - Counterarguments and rebuttals
  - Claim and evidence reordering

### In Progress 🔄
- **Source credibility assessment** - User checklist + AI-assisted evaluation
- Knowledge Base frontend polish
- Session reflection integration across all activities

### Paused ⏸️
- **Fact/Logic/Wisdom Checker** - Backend works but produces overly pedantic analysis. Hidden from UI while we improve prompt calibration.

### Planned 📋
- Link extraction and source verification
- Genre-aware F/L/W analysis standards
- Memory integration for KB activities
- Collaborative editing and version control
- Temporal versioning for investigations
- Democracy tools and election monitoring (long-term)

## 🤝 Contributing

This is an open-source project welcoming contributions. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. **Read existing code before modifying** - understand what's there
4. Make small, tested changes
5. Ensure no existing features are broken
6. Submit a pull request

### Development Principles
- **Surgical changes only** - Don't rewrite files, make targeted edits
- **View before modify** - Always check existing code first
- **Trace bugs to source** - Don't guess, investigate
- **Check callers before callees** - Bug often in how something is called
- **Minimal changes** - Fix the bug, don't rewrite the file
- **One change, then test** - Don't batch modifications
- **Preserve functionality** - Working code \> clean code

## 📄 License

[License type to be determined]

## 🙏 Acknowledgments

Built with:
- [FastAPI][2] - Backend framework
- [Next.js][3] - Frontend framework
- [Anthropic Claude][4] - Primary AI provider
- [DuckDuckGo][5] - Web search
- The wisdom traditions that inspire this work

---

*"Something Deeperism" is a philosophical approach that seeks the deeper truth beneath surface appearances, guided by universal values that transcend cultural boundaries.*

## 📞 Support

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Documentation**: Check `/docs` endpoint when backend is running
- **API Docs**: Visit `http://localhost:8000/docs` for Swagger UI

[1]:	./ARGUMENT_BUILDER_DESIGN.md
[2]:	https://fastapi.tiangolo.com/
[3]:	https://nextjs.org/
[4]:	https://www.anthropic.com/
[5]:	https://duckduckgo.com/