# Argument Builder (AB) Design Document

**Project:** Wisdom Agent  
**Document Version:** 1.0  
**Date:** February 11, 2025  
**Status:** Design Complete, Ready for Implementation

---

## Table of Contents

1. [Overview](#overview)
2. [Core Design Principle](#core-design-principle)
3. [User Experience](#user-experience)
4. [Data Model](#data-model)
5. [API Endpoints](#api-endpoints)
6. [Frontend Components](#frontend-components)
7. [Integration with Existing Systems](#integration-with-existing-systems)
8. [Implementation Phases](#implementation-phases)
9. [Open Questions](#open-questions)
10. [Appendix: Example Content](#appendix-example-content)

---

## Overview

### What Is the Argument Builder?

The Argument Builder (AB) is a tool for creating structured, navigable investigations. Users compose readable prose at the top level, with embedded links that take readers deeper into definitions, claims, evidence, and counterarguments.

**The AB is NOT:**
- A block-diagram tool
- A mind-mapping interface
- A replacement for the Knowledge Base (KB)

**The AB IS:**
- A way to write investigations that are both accessible (quick overview) and thorough (drill down for details)
- A system where every claim links to evidence, and every piece of evidence links to its source
- A modular structure where blocks of text remain connected to their origins

### Primary Use Case

The initial AB will build an investigation answering:

> "It seems that the USA's democracy is collapsing. But what exactly is going on? Why is it a problem? What should we do?"

This serves as both the prototype and the first real content.

### Relationship to Knowledge Base

```
┌─────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE (KB)                          │
│  - Stores articles, documents, URLs                             │
│  - Parsing extracts structure (thesis, claims, evidence)        │
│  - Provides raw material for AB                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ARGUMENT BUILDER (AB)                        │
│  - User composes investigations using KB material               │
│  - Links snippets back to exact source locations                │
│  - Structures arguments with claims, evidence, rebuttals        │
└─────────────────────────────────────────────────────────────────┘
```

The KB is the library. The AB is where you write using that library.

---

## Core Design Principle

**Links create structure, not boxes.**

The investigation is readable prose at the surface. Structure emerges from embedded links. A reader can stop at any layer:

| Layer | What It Is | Depth |
|-------|------------|-------|
| **Overview** | One paragraph with colored links | Surface |
| **Definition Page** | Precise meaning of a term | 1 click |
| **Claim Page** | Full discussion with evidence | 1 click |
| **Evidence Item** | Credibility + link to source | 2 clicks |
| **Source Credibility Page** | About the publication/author | 2-3 clicks |
| **KB Resource** | The actual article | 3+ clicks |

---

## User Experience

### Overview Page

The investigation opens with a readable paragraph. Terms and claims are color-coded links:

```
The USA's liberal representative government is seriously 
damaged in these ways. These damages have these causes. 
Harming liberal representative government is harmful to the 
country and its inhabitants because liberal representative 
democracy is a spiritual good. Likely paths towards restoring 
democratic health include these approaches.
```

**Color Coding:**
- 🔵 **Blue** = Definition (click to see precise meaning)
- 🟠 **Orange** = Claim (click to see full discussion)

### Click Behavior: Slide-Out Panel (Recommended)

When a user clicks a link:
1. A panel slides in from the right
2. The overview remains visible (slightly dimmed) on the left
3. User can read details without losing context
4. Panel can be closed to return to overview

**Alternative:** New page with breadcrumb navigation ("Overview → Claim X")

### Definition Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  DEFINITION: Liberal                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  In this context: Basic human rights guaranteed to all         │
│  citizens, regardless of status. Not the partisan political    │
│  term, but the classical sense: freedom of speech, due         │
│  process, equal protection under law, etc.                     │
│                                                                 │
│  See also: Representative Government, Universal Values         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Claim Page Structure

Every claim page has the same sections:

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to Overview                                             │
│                                                                 │
│  CLAIM: The Executive Branch Is Defying Judicial Orders        │
│  Status: Ongoing | Last updated: Feb 11, 2025                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CLAIM                                                          │
│  [The assertion, stated clearly]                                │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EXPOSITION                                                     │
│  [Description, background, argumentation, logical links to     │
│   other claims - this is prose with embedded links]            │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EVIDENCE                                                       │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 📰 Source Title                                        │    │
│  │    Credibility: ★★★★☆ | Type: Think tank analysis     │    │
│  │    "Key quote or summary"                              │    │
│  │    [View credibility] [View source]                    │    │
│  └────────────────────────────────────────────────────────┘    │
│  [More evidence items...]                                       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  COUNTERARGUMENTS & REBUTTALS                                   │
│                                                                 │
│  ⚡ "Counter-argument text..."                                  │
│     💬 Response: "Rebuttal text..."                             │
│        └── [Evidence for rebuttal]                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Source Credibility Page Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  SOURCE CREDIBILITY ASSESSMENT                                  │
│  [Publication Name]                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PUBLICATION INFO                                               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Name: [Publication]                                   │      │
│  │ Type: [News / Think tank / Academic / Government]    │      │
│  │ Founded: [Year]                                       │      │
│  │ Affiliation: [If any]                                 │      │
│  │ Funding: [Sources]                                    │      │
│  │ Track Record: [Notable citations, corrections, etc.]  │      │
│  │                                                       │      │
│  │ 🤖 AI Assessment: [Auto-generated evaluation]        │      │
│  │    [Remove AI assessment] [Regenerate]               │      │
│  │                                                       │      │
│  │ 📝 Your Notes: [User's own evaluation]               │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
│  THIS SPECIFIC PIECE                                            │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ Title: [Article title]                                │      │
│  │ Author(s): [Names and roles]                          │      │
│  │ Published: [Date]                                     │      │
│  │ Style: [Report / Opinion / News / Analysis]          │      │
│  │ Intent: [Inform / Persuade / Document / Advocate]    │      │
│  │ Primary Sources Cited: [Yes/No, what kind]           │      │
│  │                                                       │      │
│  │ 🤖 AI Assessment: [Auto-generated]                   │      │
│  │    [Remove AI assessment] [Regenerate]               │      │
│  │                                                       │      │
│  │ 📝 Your Notes: [User input]                          │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Writing/Editing Experience

Writing an investigation should feel like writing a Word doc:
- Rich text editor for the overview
- "Insert Link" action that lets you link to:
  - An existing Definition
  - An existing Claim
  - Create a new Definition
  - Create a new Claim
- Color coding appears automatically based on link type

---

## Data Model

### Core Tables

```sql
-- An investigation is the top-level container
CREATE TABLE investigations (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,  -- URL-friendly, auto-generated but editable
    overview_html TEXT NOT NULL,         -- The overview prose with embedded links
    status VARCHAR(50) DEFAULT 'draft',  -- draft, published, archived
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),             -- For future multi-user
    version INT DEFAULT 1                -- For temporal versioning
);

-- Definitions explain terms used in the investigation
CREATE TABLE definitions (
    id SERIAL PRIMARY KEY,
    investigation_id INT REFERENCES investigations(id) ON DELETE CASCADE,
    term VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,          -- Auto-generated but editable
    definition_html TEXT NOT NULL,       -- Can include links to other definitions
    see_also JSON,                       -- Array of related definition slugs
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(investigation_id, slug)
);

-- Claims are the building blocks of the argument
CREATE TABLE claims (
    id SERIAL PRIMARY KEY,
    investigation_id INT REFERENCES investigations(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(255) NOT NULL,          -- Auto-generated but editable
    claim_text TEXT NOT NULL,            -- The assertion itself
    exposition_html TEXT,                -- Background, description, links to other claims
    status VARCHAR(50) DEFAULT 'ongoing', -- ongoing, resolved, historical, superseded
    temporal_note TEXT,                  -- "As of Feb 2025..."
    position INT,                        -- For ordering in claim lists
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(investigation_id, slug)
);

-- Evidence supports claims
CREATE TABLE evidence (
    id SERIAL PRIMARY KEY,
    claim_id INT REFERENCES claims(id) ON DELETE CASCADE,
    kb_resource_id INT,                  -- Link to KB resource (nullable for manual entry)
    source_title VARCHAR(500),
    source_url TEXT,
    source_type VARCHAR(100),            -- primary_source, news, analysis, think_tank, academic, government
    key_quote TEXT,                      -- The specific relevant excerpt
    key_point TEXT,                      -- Summary of why this evidence matters
    position INT,                        -- For ordering
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Link to exact location in source (for "threaded" connection)
    source_anchor_type VARCHAR(50),      -- character_range, parsed_claim, section
    source_anchor_data JSON              -- {"start": 1523, "end": 1589} or {"claim_id": 17}
);

-- Credibility assessments for sources (can be shared across evidence)
CREATE TABLE source_credibility (
    id SERIAL PRIMARY KEY,
    
    -- Publication-level info
    publication_name VARCHAR(255) NOT NULL,
    publication_type VARCHAR(100),       -- news, think_tank, academic, government, advocacy
    founded_year INT,
    affiliation TEXT,
    funding_sources TEXT,
    track_record TEXT,
    
    -- AI assessment (optional, deletable)
    ai_assessment_publication TEXT,
    ai_assessment_generated_at TIMESTAMP,
    ai_model_used VARCHAR(100),
    
    -- User notes
    user_notes TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(publication_name)
);

-- Per-piece credibility (links evidence to source credibility + piece-specific info)
CREATE TABLE evidence_credibility (
    id SERIAL PRIMARY KEY,
    evidence_id INT REFERENCES evidence(id) ON DELETE CASCADE,
    source_credibility_id INT REFERENCES source_credibility(id),
    
    -- Piece-specific info
    author_names TEXT,
    author_roles TEXT,
    published_date DATE,
    style VARCHAR(100),                  -- report, opinion, news, analysis, editorial
    intent VARCHAR(100),                 -- inform, persuade, document, advocate
    primary_sources_cited BOOLEAN,
    primary_sources_description TEXT,
    
    -- AI assessment for this specific piece
    ai_assessment_piece TEXT,
    ai_assessment_generated_at TIMESTAMP,
    
    -- User notes for this specific piece
    user_notes TEXT,
    
    -- Overall credibility rating (1-5 stars, user can override)
    credibility_rating INT CHECK (credibility_rating >= 1 AND credibility_rating <= 5),
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Counterarguments and rebuttals
CREATE TABLE counterarguments (
    id SERIAL PRIMARY KEY,
    claim_id INT REFERENCES claims(id) ON DELETE CASCADE,
    counter_text TEXT NOT NULL,          -- The objection
    rebuttal_text TEXT,                  -- The response (optional if unaddressed)
    position INT,                        -- For ordering
    created_at TIMESTAMP DEFAULT NOW()
);

-- Evidence supporting rebuttals
CREATE TABLE rebuttal_evidence (
    id SERIAL PRIMARY KEY,
    counterargument_id INT REFERENCES counterarguments(id) ON DELETE CASCADE,
    evidence_id INT REFERENCES evidence(id),  -- Reuse existing evidence
    custom_note TEXT                     -- Or add a custom note
);

-- Change log for temporal versioning
CREATE TABLE investigation_changelog (
    id SERIAL PRIMARY KEY,
    investigation_id INT REFERENCES investigations(id) ON DELETE CASCADE,
    changed_at TIMESTAMP DEFAULT NOW(),
    change_type VARCHAR(50),             -- claim_added, claim_updated, evidence_added, etc.
    change_summary TEXT,                 -- Human-readable description
    changed_by VARCHAR(255),
    previous_state JSON                  -- Optional: store previous version of changed item
);
```

### Link Format in HTML

When storing `overview_html`, `exposition_html`, or `definition_html`, links use this format:

```html
<!-- Link to a definition -->
<a href="#def:liberal" class="ab-link ab-definition">liberal</a>

<!-- Link to a claim -->
<a href="#claim:judicial-defiance" class="ab-link ab-claim">these ways</a>
```

The frontend renders these with appropriate colors and click behavior.

---

## API Endpoints

### Investigation CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ab/investigations` | List all investigations |
| POST | `/api/ab/investigations` | Create new investigation |
| GET | `/api/ab/investigations/{slug}` | Get investigation by slug |
| PUT | `/api/ab/investigations/{slug}` | Update investigation |
| DELETE | `/api/ab/investigations/{slug}` | Delete investigation |

### Definitions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ab/investigations/{slug}/definitions` | List definitions |
| POST | `/api/ab/investigations/{slug}/definitions` | Create definition |
| GET | `/api/ab/investigations/{slug}/definitions/{def_slug}` | Get definition |
| PUT | `/api/ab/investigations/{slug}/definitions/{def_slug}` | Update definition |
| DELETE | `/api/ab/investigations/{slug}/definitions/{def_slug}` | Delete definition |

### Claims

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ab/investigations/{slug}/claims` | List claims |
| POST | `/api/ab/investigations/{slug}/claims` | Create claim |
| GET | `/api/ab/investigations/{slug}/claims/{claim_slug}` | Get claim with evidence |
| PUT | `/api/ab/investigations/{slug}/claims/{claim_slug}` | Update claim |
| DELETE | `/api/ab/investigations/{slug}/claims/{claim_slug}` | Delete claim |

### Evidence

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ab/claims/{claim_id}/evidence` | List evidence for claim |
| POST | `/api/ab/claims/{claim_id}/evidence` | Add evidence to claim |
| PUT | `/api/ab/evidence/{id}` | Update evidence |
| DELETE | `/api/ab/evidence/{id}` | Remove evidence |

### Credibility

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ab/credibility/publication/{name}` | Get publication credibility |
| POST | `/api/ab/credibility/publication` | Create/update publication credibility |
| POST | `/api/ab/evidence/{id}/credibility` | Set evidence-specific credibility |
| POST | `/api/ab/evidence/{id}/credibility/ai-assess` | Generate AI assessment |
| DELETE | `/api/ab/evidence/{id}/credibility/ai-assess` | Remove AI assessment |

### Counterarguments

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ab/claims/{claim_id}/counterarguments` | List counterarguments |
| POST | `/api/ab/claims/{claim_id}/counterarguments` | Add counterargument |
| PUT | `/api/ab/counterarguments/{id}` | Update (add rebuttal, etc.) |
| DELETE | `/api/ab/counterarguments/{id}` | Delete counterargument |

### Integration with KB

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ab/evidence/from-kb` | Create evidence from KB resource |
| GET | `/api/ab/kb-search` | Search KB for relevant resources |
| POST | `/api/ab/evidence/from-parsed-claim` | Create evidence from parsed claim |

---

## Frontend Components

### New Pages

```
frontend/src/app/(dashboard)/
├── arguments/                          # Investigation list & editor
│   ├── page.tsx                        # List all investigations
│   ├── new/
│   │   └── page.tsx                    # Create new investigation
│   └── [slug]/
│       ├── page.tsx                    # View/edit investigation overview
│       ├── definitions/
│       │   └── [def_slug]/
│       │       └── page.tsx            # View/edit definition
│       └── claims/
│           └── [claim_slug]/
│               └── page.tsx            # View/edit claim
```

### New Components

```
frontend/src/components/arguments/
├── InvestigationOverview.tsx           # The overview with colored links
├── OverviewEditor.tsx                  # Rich text editor with link insertion
├── SlideOutPanel.tsx                   # Right-side panel for definitions/claims
├── DefinitionView.tsx                  # Definition display
├── DefinitionEditor.tsx                # Definition editing
├── ClaimView.tsx                       # Full claim display with all sections
├── ClaimEditor.tsx                     # Claim editing (all sections)
├── EvidenceCard.tsx                    # Single evidence item display
├── EvidenceEditor.tsx                  # Add/edit evidence
├── CredibilityAssessment.tsx           # Publication + piece credibility
├── CounterargumentSection.tsx          # Counter + rebuttal display
├── LinkInsertModal.tsx                 # Modal for inserting definition/claim links
├── KBResourcePicker.tsx                # Search/select KB resources for evidence
└── ChangeLog.tsx                       # Display investigation changelog
```

### New API Client

```
frontend/src/lib/arguments-api.ts       # API client for all AB endpoints
```

---

## Integration with Existing Systems

### Knowledge Base Integration

The AB uses KB in these ways:

1. **Search KB resources** when adding evidence
2. **Link evidence to specific KB resource** (stores `kb_resource_id`)
3. **Use parsed claims** from KB parsing as evidence
4. **Deep link to exact location** in source (character range or parsed claim ID)

### Using Parsed Content

When a KB resource has been parsed, the AB can:
- Show parsed outline when selecting evidence
- Let user pick specific claims from the parse
- Auto-populate evidence fields from parsed content
- Maintain link to `extracted_claims.id` from parsing

### Existing Services Used

| Service | AB Usage |
|---------|----------|
| `llm_router.py` | AI credibility assessments |
| `knowledge_service.py` | KB resource search and retrieval |
| `parsing_service.py` | Access parsed content for evidence selection |

---

## Implementation Phases

### ⚠️ CRITICAL: Implementation Rules

**From project memory:**
> CRITICAL: Surgical changes ONLY. Never rewrite files. Verify ALL existing features preserved after edits. #1 bug cause = overwriting features.

Each phase must:
1. Make minimal, targeted changes
2. Test before proceeding
3. Verify no existing features broken
4. Commit after each phase

---

### Phase 1: Data Model + Basic CRUD

**Goal:** Database tables exist, can create/read/update/delete investigations

**Tasks:**
1. Create `backend/database/ab_models.py` with SQLAlchemy models
2. Add tables to database initialization (migration or create_all)
3. Create `backend/routers/arguments_builder.py` with basic CRUD
4. Create `backend/services/ab_service.py` for business logic
5. Test all CRUD endpoints via `/docs`

**Stop Point:** Can create an investigation with overview, add definitions and claims, retrieve them via API.

**Verification:**
```bash
# Test: Create investigation
curl -X POST http://localhost:8000/api/ab/investigations \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Investigation", "overview_html": "<p>Test</p>"}'

# Test: Get investigation
curl http://localhost:8000/api/ab/investigations/test-investigation
```

---

### Phase 2: Frontend - Investigation List & Overview Display

**Goal:** Can view list of investigations, click one to see overview with rendered links

**Tasks:**
1. Create `frontend/src/app/(dashboard)/arguments/page.tsx` - list view
2. Create `frontend/src/app/(dashboard)/arguments/[slug]/page.tsx` - overview view
3. Create `frontend/src/components/arguments/InvestigationOverview.tsx`
4. Create `frontend/src/lib/arguments-api.ts`
5. Implement link rendering (color coding, click behavior)

**Stop Point:** Can navigate to `/arguments`, see list, click one, see overview with colored links (even if clicking doesn't work yet)

**Verification:** Manual browser testing

---

### Phase 3: Slide-Out Panel for Definitions & Claims

**Goal:** Clicking a link opens the slide-out panel showing definition or claim

**Tasks:**
1. Create `SlideOutPanel.tsx` component
2. Create `DefinitionView.tsx` and `ClaimView.tsx` (read-only first)
3. Wire up link clicks to panel open
4. Implement panel close behavior

**Stop Point:** Click definition link → see definition in panel. Click claim link → see claim (without evidence yet).

---

### Phase 4: Claim Page - Evidence Section

**Goal:** Claims display their evidence with credibility info

**Tasks:**
1. Create `EvidenceCard.tsx` component
2. Add evidence fetching to claim view
3. Display credibility rating and type
4. Link "View source" to KB resource if available

**Stop Point:** Claim page shows all associated evidence with basic credibility info.

---

### Phase 5: Adding/Editing Content

**Goal:** Can create and edit investigations, definitions, claims, evidence

**Tasks:**
1. Create `OverviewEditor.tsx` with rich text editing
2. Create `LinkInsertModal.tsx` for inserting definition/claim links
3. Create `DefinitionEditor.tsx`
4. Create `ClaimEditor.tsx`
5. Create `EvidenceEditor.tsx`
6. Wire up all "Edit" and "Add" buttons

**Stop Point:** Can create a complete investigation from scratch via UI.

---

### Phase 6: KB Integration

**Goal:** Can search KB and add resources as evidence

**Tasks:**
1. Create `KBResourcePicker.tsx` component
2. Add KB search API endpoint to AB
3. Integrate with evidence editor
4. Support linking to parsed claims if available

**Stop Point:** Can search KB, select resource, auto-populate evidence fields.

---

### Phase 7: Credibility Assessment

**Goal:** Full credibility workflow with AI assessment option

**Tasks:**
1. Create `CredibilityAssessment.tsx` component
2. Create API endpoint for AI assessment generation
3. Add user notes field
4. Implement "Remove AI assessment" and "Regenerate" buttons

**Stop Point:** Can view/edit full credibility assessment for any evidence source.

---

### Phase 8: Counterarguments & Rebuttals

**Goal:** Claims can have counterarguments with rebuttals

**Tasks:**
1. Create `CounterargumentSection.tsx`
2. Add CRUD for counterarguments
3. Support linking evidence to rebuttals

**Stop Point:** Can add counterarguments to claims, add rebuttals, cite evidence.

---

### Phase 9: Temporal Versioning

**Goal:** Track changes over time

**Tasks:**
1. Implement changelog recording
2. Create `ChangeLog.tsx` component
3. Add status field UI (ongoing/resolved/historical)
4. Add "Last updated" display

**Stop Point:** Changes are logged, can view changelog, can mark claims as historical.

---

### Phase 10: Polish & Integration

**Goal:** Production-ready feature

**Tasks:**
1. Add to main navigation
2. Responsive design for mobile
3. Error handling and loading states
4. Help text / onboarding
5. Update README documentation

---

## Open Questions

These decisions can be made during implementation:

| Question | Options | Notes |
|----------|---------|-------|
| **Credibility framework** | CRAAP test / Custom / Hybrid | Research media literacy best practices |
| **Slug generation** | Auto from title / User-defined | Currently: auto + editable |
| **Investigation snapshots** | Monthly / On-demand / Both | For "what did this look like before?" |
| **Collaborative editing** | Real-time / Turn-based / Single-user first | Start single-user, design for future |

---

## Appendix: Example Content

### Example Overview (Democracy Investigation)

```html
<p>The USA's <a href="#def:liberal" class="ab-link ab-definition">liberal</a> 
<a href="#def:representative-government" class="ab-link ab-definition">representative government</a> 
is seriously damaged in <a href="#claim:damages-overview" class="ab-link ab-claim">these ways</a>. 
These damages have <a href="#claim:causes-overview" class="ab-link ab-claim">these causes</a>. 
Harming liberal representative government is harmful to the country and its inhabitants because 
<a href="#claim:why-democracy-matters" class="ab-link ab-claim">liberal representative democracy 
is a spiritual good</a>. Likely paths towards restoring democratic health include 
<a href="#claim:restoration-paths" class="ab-link ab-claim">these approaches</a>.</p>
```

### Example Definition

```json
{
  "term": "Liberal",
  "slug": "liberal",
  "definition_html": "<p>In this context: Basic human rights guaranteed to all citizens, regardless of status. Not the partisan political term, but the classical sense: freedom of speech, due process, equal protection under law, etc.</p>",
  "see_also": ["representative-government", "universal-values"]
}
```

### Example Claim

```json
{
  "title": "The Executive Branch Is Defying Judicial Orders",
  "slug": "judicial-defiance",
  "claim_text": "The current administration has refused to comply with multiple federal court orders, representing a breakdown in the constitutional separation of powers.",
  "exposition_html": "<p>The U.S. system depends on the executive branch accepting judicial authority, even when it disagrees with rulings. Historically, presidents have sometimes <a href=\"#claim:historical-pushback\" class=\"ab-link ab-claim\">pushed back rhetorically</a> but ultimately complied. The current situation differs in scale and explicit defiance.</p><p>This damage connects to <a href=\"#claim:norm-erosion\" class=\"ab-link ab-claim\">erosion of democratic norms</a>.</p>",
  "status": "ongoing",
  "temporal_note": "As of February 2025, multiple cases pending"
}
```

### Example Evidence

```json
{
  "kb_resource_id": 47,
  "source_title": "Democracy Under Strain: February 2025 Report",
  "source_url": "https://www.brennancenter.org/...",
  "source_type": "think_tank",
  "key_quote": "Documents 12 instances of non-compliance with federal court orders since January 2025.",
  "key_point": "Systematic pattern of defiance, not isolated incidents",
  "source_anchor_type": "section",
  "source_anchor_data": {"section": "Executive Accountability", "paragraph": 3}
}
```

---

## File Locations Summary

### Backend (New Files)

```
backend/
├── database/
│   └── ab_models.py              # NEW: SQLAlchemy models
├── services/
│   └── ab_service.py             # NEW: Business logic
├── routers/
│   └── arguments_builder.py      # NEW: API endpoints
└── models/
    └── ab_schemas.py             # NEW: Pydantic schemas
```

### Frontend (New Files)

```
frontend/src/
├── app/(dashboard)/arguments/    # NEW: All AB pages
├── components/arguments/         # NEW: All AB components
└── lib/arguments-api.ts          # NEW: API client
```

---

*End of Design Document*
