# Wisdom Agent Frontend

A Next.js frontend for the Wisdom Agent platform - an AI companion for growing in wisdom through Something Deeperism philosophy.

## Features

- **Chat Interface** - Engage in wisdom-focused conversations with AI
- **Project Management** - Organize your learning into projects with goals
- **Philosophy Browser** - Explore Something Deeperism principles and the 7 Universal Values
- **Reflections** - Track your growth through session reflections and value scores
- **Settings** - Configure LLM providers and view system status

## Design Philosophy

The interface is designed with a contemplative, refined aesthetic that reflects the philosophical nature of the platform:

- **Color Palette**: Deep wisdom blues, warm gold accents, and neutral stone tones
- **Typography**: Crimson Pro serif for headings (philosophical feel), Inter for body text
- **Spacing**: Generous whitespace to encourage reflection
- **Animation**: Subtle, thoughtful transitions

## Tech Stack

- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with custom design system
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Backend server running on port 8000

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment example
cp .env.example .env.local

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── (dashboard)/        # Dashboard layout group
│   │   │   ├── chat/           # Chat interface
│   │   │   ├── projects/       # Project management
│   │   │   ├── philosophy/     # Philosophy browser
│   │   │   ├── reflections/    # Session reflections
│   │   │   └── settings/       # Settings page
│   │   ├── globals.css         # Global styles
│   │   ├── layout.tsx          # Root layout
│   │   └── page.tsx            # Landing/redirect
│   ├── components/             # React components
│   │   ├── ChatInterface.tsx   # Main chat component
│   │   ├── ChatInput.tsx       # Message input
│   │   ├── ChatMessage.tsx     # Message bubble
│   │   ├── ProjectCard.tsx     # Project display card
│   │   ├── ReflectionCard.tsx  # Reflection display
│   │   ├── Sidebar.tsx         # Navigation sidebar
│   │   └── ValueScore.tsx      # 7 Values score display
│   ├── lib/                    # Utilities
│   │   ├── api.ts              # Backend API client
│   │   └── utils.ts            # Helper functions
│   ├── hooks/                  # Custom React hooks
│   └── types/                  # TypeScript types
├── public/                     # Static assets
├── tailwind.config.ts          # Tailwind configuration
├── next.config.js              # Next.js configuration
└── package.json
```

## Available Scripts

```bash
# Development
npm run dev          # Start dev server with hot reload

# Production
npm run build        # Build for production
npm run start        # Start production server

# Code Quality
npm run lint         # Run ESLint
```

## API Integration

The frontend communicates with the FastAPI backend through the API client in `src/lib/api.ts`. The `next.config.js` includes a rewrite rule to proxy `/api/*` requests to the backend.

### Key API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `/health` | Backend health check |
| `/philosophy` | Load philosophy files |
| `/chat/complete` | Send chat messages |
| `/chat/providers` | List LLM providers |
| `/projects/` | CRUD for projects |
| `/sessions/` | Session management |
| `/sessions/{id}/reflection` | Get session reflections |

## The 7 Universal Values

The platform evaluates conversations based on these values:

1. **Awareness** - Present-moment attention and mindfulness
2. **Honesty** - Truthfulness with self and others
3. **Accuracy** - Precision in thought and expression
4. **Competence** - Skill and capability development
5. **Compassion** - Understanding and caring for others
6. **Loving-kindness** - Unconditional positive regard
7. **Joyful Sharing** - Delight in giving and connecting

## Styling Guide

### Colors

```css
/* Primary - Wisdom Blue */
wisdom-600: #2f5789

/* Accent - Gold */
gold-500: #e6a42f

/* Success - Sage Green */
sage-500: #5a7a61

/* Neutral - Stone */
stone-900: #1c1917
```

### Components

The design system includes these reusable classes:

- `.card` - Card container with border and shadow
- `.btn-primary` - Primary action button
- `.btn-secondary` - Secondary action button
- `.btn-ghost` - Ghost/text button
- `.input` - Form input field
- `.message-user` / `.message-assistant` - Chat bubbles

## Contributing

1. Follow the existing code style and patterns
2. Use TypeScript for all new files
3. Add appropriate types for new components
4. Keep components focused and reusable
5. Write meaningful commit messages

## License

MIT License - See LICENSE file for details
