# Wisdom Agent

An open-source AI platform that helps individuals grow in wisdom through philosophical grounding in "Something Deeperism" and the 7 Universal Values.

## 🌟 Features

### Chat & Wisdom Sessions
- AI conversations grounded in wisdom philosophy
- Session memory and context across conversations
- Automatic reflection generation after sessions
- Project-based organization

### Fact/Logic/Wisdom Checker (Three-Dimensional Analysis)
Analyze any content across three dimensions:
1. **Is it True?** (Factual Accuracy) - Verifies claims against trusted sources and fact-checking databases
2. **Is it Reasonable?** (Logical Soundness) - Analyzes argument structure and detects fallacies
3. **Does it Serve Wisdom?** (Wisdom Alignment) - Evaluates alignment with the 7 Universal Values

**Features:**
- URL or text input
- Cost estimation before analysis
- Model selection (choose from 20+ models across providers)
- Claim extraction and individual verification
- Comprehensive results with confidence scores
- Detailed explanations for each verdict

### Knowledge Base
- Organize resources into collections
- Index web content and documents
- Searchable knowledge repository
- Cost estimation for indexing operations

### Philosophy Framework
Built on "Something Deeperism" philosophy with the 7 Universal Values:
- **Awareness** - Being present and attentive
- **Honesty** - Truthfulness with self and others
- **Accuracy** - Precision in thought and expression
- **Competence** - Skillful action and understanding
- **Compassion** - Care for the suffering of others
- **Loving-kindness** - Active goodwill toward all
- **Joyful-sharing** - Generous spirit in community

### Multi-LLM Support
Supports multiple AI providers with transparent pricing:

| Provider | Models | Use Case |
|----------|--------|----------|
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Haiku, Claude 3 Opus | Best for nuanced reasoning |
| **OpenAI** | GPT-4o, GPT-4o Mini, GPT-4 Turbo | Versatile, fast |
| **Google** | Gemini 2.0 Flash, Gemini 1.5 Pro | Cost-effective, large context |
| **Nebius** | Llama 3.3 70B, DeepSeek V3, Mixtral | Budget-friendly |
| **Local** | Ollama (Mistral, Llama, Phi-3) | Free, private |

### Budget Management
- Monthly spending limits
- Cost estimation before operations
- Usage tracking and history

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
ANTHROPIC_API_KEY=your_key_here      # Recommended
OPENAI_API_KEY=your_key_here         # Optional
GOOGLE_API_KEY=your_key_here         # Optional
NEBIUS_API_KEY=your_key_here         # Optional (budget-friendly)

# Database (optional - defaults to SQLite if not set)
DATABASE_URL=postgresql://postgres:password@localhost:5432/wisdom_agent

# Fact-checking providers (optional - enhances fact-checking)
CLAIMBUSTER_API_KEY=your_key_here
# Google Fact Check API uses GOOGLE_API_KEY
```

### Database Options
- **PostgreSQL** (recommended): Better performance, required for production
- **SQLite** (default): No setup required, great for development and testing

## 📁 Project Structure

```
wisdom-agent/
├── backend/
│   ├── main.py           # FastAPI application entry
│   ├── routers/          # API endpoints
│   │   ├── review_router.py    # Fact checker
│   │   ├── knowledge.py        # Knowledge base
│   │   └── ...
│   ├── services/         # Business logic
│   │   ├── review_service.py
│   │   ├── knowledge_service.py
│   │   └── ...
│   ├── models/           # Pydantic models
│   ├── database/         # DB models and connections
│   └── providers/        # External API integrations
├── frontend/
│   └── src/
│       ├── app/          # Next.js pages
│       │   ├── fact-checker/   # F/L/W Checker
│       │   ├── knowledge/      # Knowledge Base
│       │   └── ...
│       ├── components/   # React components
│       └── lib/          # Utilities and API client
├── data/
│   └── philosophy/       # Philosophy text files
│       └── base/         # Core philosophy documents
└── config/
    └── llm_providers.json
```

## 🔍 Troubleshooting

### Backend won't start
- Check that all required API keys are set in `.env`
- Ensure PostgreSQL is running if using `DATABASE_URL`
- Check Python dependencies: `pip install -r requirements.txt`

### "Knowledge Base tables" warnings
- These are usually harmless if the tables already exist
- If KB isn't working, check the database connection

### Fact Checker stuck on "Analyzing"
- External fact-check APIs may be unavailable
- The system will fall back to LLM verification (slower)
- Check backend terminal for error messages

### Frontend not updating
- Stop and restart: `npm run dev`
- Clear browser cache or use incognito mode

## 🎯 Roadmap

### Completed
- [x] Multi-LLM support with 5 providers
- [x] Fact/Logic/Wisdom Checker with cost estimation
- [x] Model selection per operation
- [x] Budget tracking and limits
- [x] Knowledge Base backend

### In Progress
- [ ] Knowledge Base frontend completion
- [ ] Fact checker reliability improvements

### Planned
- [ ] **Thesis Wiki** - Hierarchical thesis system for studying complex topics
  - Overview + drill-down navigation
  - Media integration (videos, articles)
  - Shareable resources for civic engagement
- [ ] Global model selector (use preferred model everywhere)
- [ ] Wisdom AI self-improvement mode
- [ ] Public API for third-party integration
- [ ] Democracy tools for election monitoring

## 🤝 Contributing

This is an open-source project welcoming contributions. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. **Read existing code before modifying** - understand what's there
4. Make small, tested changes
5. Ensure no existing features are broken
6. Submit a pull request

### Development Principles
- **View before modify** - Always check existing code first
- **Minimal changes** - Fix the bug, don't rewrite the file
- **Test after each change** - Verify nothing broke
- **Preserve functionality** - Working code > clean code

## 📄 License

[License type to be determined]

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Backend framework
- [Next.js](https://nextjs.org/) - Frontend framework
- [Anthropic Claude](https://www.anthropic.com/) - Primary AI provider
- The wisdom traditions that inspire this work

---

*"Something Deeperism" is a philosophical approach that seeks the deeper truth beneath surface appearances, guided by universal values that transcend cultural boundaries.*

## 📞 Support

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Documentation**: Check `/docs` endpoint when backend is running
- **API Docs**: Visit `http://localhost:8000/docs` for Swagger UI
