# Wisdom Agent - Week 3 Day 4 Updates
# Instructions for Adding Gemini & Session Browsing

## Files to Copy

Copy these files to your project:

1. `backend/services/llm_router.py` → `wisdom-agent/backend/services/llm_router.py`
2. `frontend/src/components/SessionList.tsx` → `wisdom-agent/frontend/src/components/SessionList.tsx`
3. `frontend/src/components/Sidebar.tsx` → `wisdom-agent/frontend/src/components/Sidebar.tsx`
4. `frontend/src/app/sessions/page.tsx` → `wisdom-agent/frontend/src/app/sessions/page.tsx`

**Important:** You'll need to create the `sessions` folder inside `frontend/src/app/` before copying the page.tsx file.

---

## Step 1: Update config.py

Open `wisdom-agent/backend/config.py` and find the section where API keys are defined.
It will look something like this:

```python
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY")
```

**Add this line right after the other API keys:**

```python
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
```

---

## Step 2: Update .env file

Open your `wisdom-agent/.env` file and add your Google API key:

```
GOOGLE_API_KEY=your_google_api_key_here
```

To get a Google API key:
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key and paste it in your .env file

---

## Step 3: Install the Google library

Run this command in your terminal:

```bash
pip install google-generativeai --break-system-packages
```

---

## Step 4: Delete old config file (optional but recommended)

If you have issues, delete the cached LLM config to get fresh defaults:

```bash
rm wisdom-agent/config/llm_providers.json
```

---

## Step 5: Restart servers

```bash
# Terminal 1 - Backend
cd wisdom-agent/backend
python -m uvicorn main:app --reload

# Terminal 2 - Frontend  
cd wisdom-agent/frontend
npm run dev
```

---

## How to Use Session Browsing

The SessionList component can be used in your pages. For example, to add it to a page:

```tsx
import SessionList from '@/components/SessionList';

// In your component:
<SessionList projectId={1} />
```

This will show all sessions for project ID 1, with the ability to:
- See all past sessions
- View conversation transcripts
- See summaries and reflections
- View 7 Universal Values scores

---

## Verification

When you restart the backend, you should see:

```
✓ Anthropic client initialized
✓ Google Gemini client initialized    ← NEW!
```

If you don't have a Google API key set, you'll see:
```
⚠ Google Generative AI library not installed
```
or no message at all (which is fine - Gemini is optional).
