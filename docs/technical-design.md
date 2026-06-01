# Cue — Technical Design Document

**Partner Track:** MongoDB
**Hackathon:** Google Cloud Rapid Agent Hackathon
**Deadline:** June 11, 2026 @ 2:00pm PDT

## Table of Contents
1. [Partner Track Decision](#1-partner-track-decision)
2. [Architecture Overview](#2-architecture-overview)
3. [Agent Specifications](#3-agent-specifications)
4. [MongoDB Data Model](#4-mongodb-data-model)
5. [MongoDB MCP Integration](#5-mongodb-mcp-integration)
6. [API Surface](#6-api-surface)
7. [Frontend Design](#7-frontend-design)
8. [Deployment](#8-deployment)
9. [Hackathon Judging Strategy](#9-hackathon-judging-strategy)
10. [Competitive Landscape](#10-competitive-landscape)

---

## 1. Partner Track Decision

**Chosen: MongoDB**

MongoDB is the natural partner for Cue because the MCP integration powers the core product — agents read/write user data, communication history, and boards directly through the MCP server. Every agent call touches MongoDB MCP tools.

| Factor | Assessment |
|---|---|
| Technical fit | Excellent — user profiles, vocab sets, boards, history are all documents |
| MCP tool count | ~43 tools (find, aggregate, insert, update, indexes, Atlas management) |
| Integration depth | Every agent uses MCP for core functionality, not just supplementary queries |
| Vector Search | Built-in Atlas Vector Search for semantic vocabulary matching |
| Atlas Search | Full-text search across communication history |
| Free tier | Atlas M0 (512MB, no time limit) |
| Familiarity | Prior MongoDB experience |

**Why not other partners:**

| Partner | Why Not |
|---|---|
| Arize | Observability MCP tools (traces, prompts, experiments) don't power core AAC features. MCP usage would feel supplementary, not central. |
| Elastic | Strong search, but time-limited trial. Higher setup complexity. Less database familiarity. |
| Fivetran | Data pipelines — irrelevant to AAC. |
| GitLab | DevSecOps — irrelevant to AAC. |
| Dynatrace | Enterprise observability — no advantage for AAC. |

**MCP integration story for judges:** "Every time a user taps a word, our agents query MongoDB via MCP to find communication patterns, generate personalized boards, and store the interaction — building a richer profile with every use. The more you use Cue, the better it knows you."

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    React SPA (Frontend)                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │
│  │Board View│ │Prediction│ │Expression│ │User Profile│ │
│  │  Grid    │ │  Bar     │ │  Output  │ │  Settings  │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │
└──────────────────────┬──────────────────────────────────┘
                       │ REST / SSE
┌──────────────────────▼──────────────────────────────────┐
│                 FastAPI (Cloud Run)                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Agent Engine Client                    │   │
│  │  Local: ADK Runner + InMemorySessionService       │   │
│  │  Prod:  Vertex AI Agent Engine proxy              │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────▼───────────────────────────┐   │
│  │              ADK Agent Hierarchy                   │   │
│  │                                                    │   │
│  │  root_agent (Gemini 3 Flash)                      │   │
│  │    ├── prediction_agent (Flash)                    │   │
│  │    ├── scene_agent (Flash)                        │   │
│  │    └── expression_agent (Lite)                    │   │
│  │                                                    │   │
│  │  Standalone (invoked by backend):                 │   │
│  │    └── board_generator (ParallelAgent)            │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│              MongoDB MCP Server                          │
│              (npx mongodb-mcp-server)                    │
└──────┬──────────────────────────────┬───────────────────┘
       │                              │
┌──────▼──────┐                ┌──────▼──────┐
│  MongoDB    │                │  Google     │
│  Atlas      │                │  Cloud TTS  │
│  (M0 Free)  │                │             │
└─────────────┘                └─────────────┘
```

### Key Design Decisions

1. **ADK over raw Gemini API** — agent routing, state management, tool calling, and Agent Engine deployment out of the box. Proven in SlimeStudio with 18 agents.

2. **FastAPI proxy pattern** — backend proxies agent calls via `AgentEngineClient` (local ADK Runner in dev, Vertex AI Agent Engine in prod). Same pattern as SlimeStudio.

3. **3-tier model strategy** — Flash for reasoning agents (prediction, scene), Lite for extraction agents (expression). Keeps costs down and latency low.

4. **MongoDB MCP as the data backbone** — agents don't use PyMongo directly. They access MongoDB through the MCP server, making the partner integration central and visible. Every agent tool call that touches data goes through MCP.

5. **Human-in-the-loop always** — agents suggest; user selects. Nothing is spoken without user confirmation. Critical for AAC safety.

---

## 3. Agent Specifications

### 3.1 Root Agent

```python
# Role: Entry point. Routes user intent to the right specialist.
# Model: gemini-3-flash
# Tools: (MongoDB MCP tools available to all agents)
# Sub-agents: prediction_agent, scene_agent, expression_agent

GLOBAL_INSTRUCTION = """USER CONTEXT:
- Name: {user_name?}, Age: {user_age?}
- Ability level: {ability_level?} (1-5, where 1=early intervention, 5=advanced)
- Current board: {current_board?}
- Location context: {location?}
- Time: {current_time?}
- Recent selections: {recent_selections?}
- Communication partner: {partner_type?} (parent, teacher, peer, stranger)
"""
```

The root agent inspects the incoming request and delegates:
- "What should the user likely say next?" → prediction_agent
- "Generate a board for this context" → scene_agent
- "Speak this / format this for texting" → expression_agent

### 3.2 Prediction Agent

```
Name: prediction_agent
Model: gemini-3-flash
Tier: Flash (analytical, pattern-matching)
Temperature: 1.0 (Gemini 3 recommendation)
Thinking: medium

MongoDB MCP Tools Used:
  - find(communication_history) — retrieve past communications by context
  - aggregate(communication_history) — compute word frequencies, pattern analysis
  - find(vocabulary_sets) — load user's known vocabulary
  - find(users) — get user profile and ability level
  - insert-many(predictions) — log prediction events for learning

Custom ADK Tools:
  - save_prediction(user_id, predictions, context)

Purpose:
  Given user profile + current context (time, location, partner, recent selections),
  predict the most likely next words/phrases. Uses communication history aggregations
  from MongoDB MCP to find patterns.
```

**Prediction strategy:**
1. `find` user profile from `users` collection via MCP
2. `aggregate` communication_history — group by context, compute word frequencies:
   ```
   aggregate("communication_history", [
     { $match: { user_id: X, "context.location": "restaurant" } },
     { $unwind: "$selections" },
     { $group: { _id: "$selections", count: { $sum: 1 } } },
     { $sort: { count: -1 } },
     { $limit: 20 }
   ])
   ```
3. `find` vocabulary_sets to constrain predictions to known words
4. Combine frequency data + context + vocabulary level to rank predictions
5. `insert-many` the prediction event into a `predictions` collection for future learning

### 3.3 Scene Agent

```
Name: scene_agent
Model: gemini-3-flash
Tier: Flash (creative generation)
Temperature: 1.0
Thinking: medium

MongoDB MCP Tools Used:
  - find(vocabulary_sets) — user's known words
  - find(users) — ability level, grid size preferences
  - find(boards) — check for existing boards for this scene
  - aggregate(communication_history) — most-used words in this scene type
  - insert-many(boards) — save generated board

Purpose:
  Generate a context-appropriate communication board. Given a scene
  (restaurant, doctor, school, playground), produces a grid of
  relevant symbols/words organized by communication function
  (requests, comments, questions, social).
```

**Board generation strategy:**
1. `find` existing boards for this scene type — reuse if recent
2. `find` user profile for ability_level and grid_size preferences
3. `aggregate` communication_history for this scene type — what words does the user actually use here?
4. Generate board with categories: core words, context-specific, social, quick phrases
5. Adjust grid density based on ability_level (fewer, larger buttons for level 1-2; more for 4-5)
6. `insert-many` the new board into `boards` collection

### 3.4 Expression Agent

```
Name: expression_agent
Model: gemini-3-flash-lite
Tier: Lite (structured output, fast)
Temperature: 1.0
Thinking: low

MongoDB MCP Tools Used:
  - find(users) — voice_config for TTS settings
  - insert-many(communication_history) — log the completed expression

Custom ADK Tools:
  - synthesize_speech(text, voice_config) — calls Google Cloud TTS
  - complete_grammar(word_sequence) — expands telegraphic input
  - format_for_texting(word_sequence, style) — emoji, casual, formal

Purpose:
  Takes selected words/symbols and produces output:
  - TTS: grammatically complete sentence → Google Cloud TTS
  - Text: formatted for messaging (with emoji/GIF suggestions)
  - Grammar: expands telegraphic input ("want water") → "I want water, please"
```

### 3.5 Board Generator (Composite)

```python
# ParallelAgent — runs prediction + scene generation simultaneously
# when a new context is detected

board_generator = ParallelAgent(
    name="board_generator",
    description="Generates a complete board: context-aware layout + predicted words",
    sub_agents=[
        scene_agent_for_board,      # generates the board structure
        prediction_agent_for_board, # generates predicted words to highlight
    ],
)
```

### Agent Model Configuration

```python
# config.py — 3-tier model assignment (mirrors SlimeStudio pattern)

MODEL_REGISTRY = {
    "stable": {
        "lite": "gemini-3-flash-lite",
        "fast": "gemini-3-flash",
        "reasoning": "gemini-3-pro",
    },
}

_AGENT_MODELS = {
    "root": "fast",
    "prediction_agent": "fast",
    "scene_agent": "fast",
    "expression_agent": "lite",
}
```

---

## 4. MongoDB Data Model

### Collections

#### `users`
```json
{
  "_id": "ObjectId",
  "name": "Alex",
  "age": 4,
  "ability_level": 2,
  "diagnosis": "autism spectrum disorder",
  "voice_config": {
    "language": "en-US",
    "voice_name": "en-US-Journey-O",
    "speaking_rate": 0.9,
    "pitch": 2.0
  },
  "vocabulary_level": "core_200",
  "grid_size": { "rows": 3, "cols": 4 },
  "motor_config": {
    "min_button_size_px": 80,
    "dwell_time_ms": null,
    "switch_scanning": false
  },
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### `communication_history`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "timestamp": "datetime",
  "context": {
    "location": "restaurant",
    "time_of_day": "lunch",
    "partner_type": "parent",
    "board_id": "ObjectId"
  },
  "selections": ["I", "want", "pizza"],
  "expressed_output": "I want pizza, please.",
  "output_type": "speech",
  "prediction_used": true,
  "prediction_rank": 2
}
```

#### `boards`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "name": "Restaurant",
  "scene_type": "restaurant",
  "grid": {
    "rows": 4,
    "cols": 5,
    "cells": [
      {
        "position": [0, 0],
        "word": "I",
        "category": "core",
        "symbol_url": "/symbols/i.png",
        "color": "#FFD700"
      }
    ]
  },
  "generated_by": "scene_agent",
  "created_at": "datetime",
  "last_used": "datetime",
  "usage_count": 15
}
```

#### `vocabulary_sets`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "name": "core_200",
  "words": [
    { "word": "I", "category": "pronoun", "frequency": 0.95 },
    { "word": "want", "category": "verb", "frequency": 0.88 },
    { "word": "more", "category": "adjective", "frequency": 0.82 }
  ],
  "custom_words": [
    { "word": "dinosaur", "category": "noun", "added_by": "parent" }
  ]
}
```

#### `predictions`
```json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "timestamp": "datetime",
  "context": {
    "location": "restaurant",
    "time_of_day": "lunch",
    "recent_selections": ["I", "want"]
  },
  "predicted_words": [
    { "word": "pizza", "confidence": 0.85, "rank": 1 },
    { "word": "water", "confidence": 0.72, "rank": 2 },
    { "word": "more", "confidence": 0.65, "rank": 3 }
  ],
  "selected_word": "pizza",
  "was_prediction_used": true,
  "selected_rank": 1
}
```

### Indexes
```
communication_history: { user_id: 1, timestamp: -1 }
communication_history: { user_id: 1, "context.location": 1 }
boards: { user_id: 1, scene_type: 1 }
vocabulary_sets: { user_id: 1 }
predictions: { user_id: 1, timestamp: -1 }
predictions: { user_id: 1, "context.location": 1, was_prediction_used: 1 }
```

---

## 5. MongoDB MCP Integration

### MCP Server Configuration

```json
{
  "mcpServers": {
    "mongodb": {
      "command": "npx",
      "args": ["-y", "mongodb-mcp-server@latest"],
      "env": {
        "MDB_MCP_CONNECTION_STRING": "${MONGODB_URI}"
      }
    }
  }
}
```

### How Each Agent Uses MongoDB MCP

#### Prediction Agent — heaviest MCP user
| MCP Tool | Purpose | Example |
|---|---|---|
| `find` | Get user profile | `find("users", { _id: user_id })` |
| `find` | Get vocabulary set | `find("vocabulary_sets", { user_id: X })` |
| `aggregate` | Word frequency by context | Group communication_history by word, count, sort |
| `aggregate` | Prediction accuracy | Compute acceptance rate from predictions collection |
| `insert-many` | Log prediction event | Save predicted words + outcome for learning |

#### Scene Agent — board generation
| MCP Tool | Purpose | Example |
|---|---|---|
| `find` | Check existing boards | `find("boards", { user_id: X, scene_type: "restaurant" })` |
| `find` | Get user preferences | Grid size, ability level from users |
| `aggregate` | Most-used words per scene | Top words from communication_history for this scene_type |
| `insert-many` | Save generated board | Persist new board config |
| `update-many` | Update board usage | Increment usage_count, update last_used |

#### Expression Agent — logging
| MCP Tool | Purpose | Example |
|---|---|---|
| `find` | Get voice config | Voice settings from users collection |
| `insert-many` | Log communication | Save completed expression to communication_history |

#### Root Agent — context loading
| MCP Tool | Purpose | Example |
|---|---|---|
| `find` | Load user profile | On session start, fetch full user context |
| `find` | Get recent history | Last N communications for context |
| `list-collections` | System health | Verify collections exist |

### MCP Integration Depth for Demo

The demo should make the MCP integration visible:

1. **Show the aggregation pipeline** — "Watch the Prediction Agent query MongoDB for Alex's communication patterns at restaurants..."
2. **Show data accumulating** — "After Alex taps 'pizza', that selection is written back to MongoDB via MCP, making the next prediction even better."
3. **Show cross-collection queries** — agents read from users, vocabulary_sets, communication_history, and boards in a single interaction.

### Atlas Features to Leverage

**Atlas Search** (if time permits): Full-text search across vocabulary_sets for caregiver vocabulary discovery ("find all words related to 'food'").

**Atlas Vector Search** (stretch goal): Embed communication sequences and find semantically similar past interactions for better prediction.

**Performance Advisor** (via MCP): `atlas-get-performance-advisor` tool to show index recommendations — demonstrates operational awareness.

---

## 6. API Surface

### FastAPI Endpoints

```
# Health
GET  /                          -> { status: "ok" }
GET  /health                    -> { status, agent_mode, db_connected }

# User Management
POST /users                     -> Create user profile
GET  /users/{user_id}           -> Get user profile
PUT  /users/{user_id}           -> Update user profile

# Agent Endpoints (proxied to Agent Engine)
POST /agent                     -> Root agent (general chat/commands)
POST /agent/stream              -> SSE streaming agent responses
POST /predict                   -> Prediction agent (returns ranked word list)
POST /generate-board            -> Scene agent (returns board config)
POST /express                   -> Expression agent (returns TTS audio URL or text)

# Board Management
GET  /boards/{user_id}          -> List user's boards
GET  /boards/{user_id}/{board_id} -> Get specific board
POST /boards/{user_id}/generate -> Generate new board for context

# Communication History
GET  /history/{user_id}         -> Get communication history
POST /history/{user_id}         -> Log a communication event

# TTS
POST /tts                       -> Generate speech audio (Google Cloud TTS)
```

### Request/Response Examples

```python
# POST /predict
class PredictRequest(BaseModel):
    user_id: str
    context: dict  # location, time, partner_type, recent_selections
    board_id: str | None = None
    limit: int = 12

class PredictResponse(BaseModel):
    predictions: list[dict]  # [{ word, confidence, category }]
    context_used: str
```

```python
# POST /generate-board
class GenerateBoardRequest(BaseModel):
    user_id: str
    scene_type: str  # "restaurant", "doctor", "school", "home", "playground"
    custom_context: str | None = None  # free-text scene description

class GenerateBoardResponse(BaseModel):
    board: dict  # full board config with grid, cells, words
    board_id: str
```

```python
# POST /express
class ExpressRequest(BaseModel):
    user_id: str
    selections: list[str]  # ["I", "want", "pizza"]
    output_type: str  # "speech", "text", "both"
    style: str | None = None  # "casual", "formal", "emoji" (for text output)

class ExpressResponse(BaseModel):
    expressed_text: str  # "I want pizza, please."
    audio_url: str | None = None  # GCS URL to TTS audio
    text_formatted: str | None = None  # "I want pizza! 🍕" (if text output)
```

---

## 7. Frontend Design

### Technology
- **React** with TypeScript
- **Vite** for build tooling
- Deployed as static assets on Cloud Run (or Firebase Hosting)
- Responsive design: works on tablet (primary AAC device form factor)

### Key Components

```
src/
├── components/
│   ├── BoardGrid.tsx          # Main AAC grid — renders board cells
│   ├── BoardCell.tsx          # Individual tappable word/symbol button
│   ├── PredictionBar.tsx      # Top bar showing predicted next words
│   ├── MessageBar.tsx         # Bottom bar showing constructed message
│   ├── ExpressionControls.tsx # Speak / Text / Clear buttons
│   ├── SceneSelector.tsx      # Context picker (home, restaurant, etc.)
│   └── UserSwitcher.tsx       # Switch between user profiles
├── pages/
│   ├── CommunicatorPage.tsx   # Main AAC interface
│   ├── SetupPage.tsx          # User profile creation/editing
│   └── DashboardPage.tsx      # Caregiver view: history, prediction stats
├── hooks/
│   ├── useAgent.ts            # Agent API calls (predict, generate, express)
│   ├── useBoard.ts            # Board state management
│   └── useSpeech.ts           # TTS playback
└── utils/
    └── api.ts                 # Fetch wrapper for backend
```

### UX Principles (critical for AAC)
1. **Large touch targets** — minimum 60px, scaled by ability_level
2. **Consistent layout** — core words (I, want, not, go) always in same position
3. **Color coding** — nouns=orange, verbs=green, adjectives=blue, social=pink (Fitzgerald Key)
4. **Minimal latency** — predictions must appear <500ms
5. **Progressive disclosure** — start simple, grow with user

### Demo Flow (for video)
```
0:00-0:20  Hook: "4-year-old Alex can't speak. Today, we're giving him a voice."
0:20-0:40  Problem: Show static AAC grid. "This is what exists. Static. Expensive.
           Requires hours of SLP configuration."
0:40-1:30  Cue in action: Home scene → restaurant transition → prediction → speech output
           (show MongoDB MCP queries happening in real time)
1:30-2:00  Texting demo: Alex texts his friend with emoji suggestions
2:00-2:30  Data story: Show MongoDB — communication history growing, prediction accuracy
           improving, boards adapting. "The more Alex uses Cue, the smarter it gets."
2:30-2:50  Tech stack: Architecture diagram, agent hierarchy, MCP integration depth
2:50-3:00  Impact: "1 in 200 children need AAC. Cue makes it adaptive, affordable,
           and intelligent."
```

---

## 8. Deployment

### Infrastructure

```
Google Cloud Project: "cue-aac" (or existing "slimeify" project)

Services:
├── Cloud Run: FastAPI backend (port 8080)
├── Agent Engine: ADK agents (deployed via agent-starter-pack or manual)
├── MongoDB Atlas: M0 free tier (external, connected via URI)
├── Google Cloud TTS: Pay-as-you-go (free tier: 1M chars/month)
└── Secret Manager: API keys and connection strings
```

### Deployment Flow

```bash
# 1. Agent Engine deployment (ADK app)
cd app/
agent-starter-pack enhance  # adds CI/CD, Terraform
gcloud builds submit        # deploys to Agent Engine

# 2. Backend deployment (FastAPI)
cd backend/
gcloud run deploy cue-api \
  --source . \
  --region us-central1 \
  --set-env-vars AGENT_ENGINE_ID=...,MONGODB_URI=...

# 3. Frontend deployment
cd frontend/
npm run build
# Serve from Cloud Run or Firebase Hosting
```

### Environment Variables
```
AGENT_ENGINE_ID=          # Vertex AI Agent Engine resource ID
MONGODB_URI=              # MongoDB Atlas connection string
GOOGLE_API_KEY=           # Gemini API key (dev) or use Vertex AI auth (prod)
GOOGLE_CLOUD_PROJECT=     # GCP project ID
GOOGLE_CLOUD_LOCATION=    # Agent Engine region
```

### Cost Estimate (Hackathon Period)

| Service | Free Tier | Expected Cost |
|---|---|---|
| Gemini 3 Flash | $100 hackathon credits | $0 |
| MongoDB Atlas M0 | 512MB free forever | $0 |
| Cloud Run | 2M requests/month free | $0 |
| Cloud TTS | 1M chars/month free | $0 |
| Agent Engine | Included in credits | $0 |
| **Total** | | **$0** (within free tiers) |

---

## 9. Hackathon Judging Strategy

### Judging Criteria (Equal Weight)

#### 1. Technological Implementation
> "Quality of Google Cloud and Partner service interaction"

**What to demonstrate:**
- ADK agent hierarchy with root → specialists
- ParallelAgent for concurrent board+prediction generation
- Deep MongoDB MCP integration: agents run aggregation pipelines, cross-collection queries, and write-back loops
- Google Cloud TTS integration
- Agent Engine deployment (not just local dev)
- State management via ADK sessions
- Show MCP tool calls in action (aggregation pipelines computing word frequencies)

#### 2. Design
> "User experience and thoughtful design"

**What to demonstrate:**
- Accessibility-first UI (large targets, color coding, consistent layout)
- Progressive complexity (ability levels 1-5)
- Tablet-optimized layout
- <500ms prediction latency
- Smooth transitions between scenes/boards

#### 3. Potential Impact
> "Scope of impact on target communities"

**What to demonstrate:**
- AAC market: 2M+ Americans need AAC; 75% of current tools are prohibitively expensive
- Early intervention: dynamic boards reduce SLP configuration time by 80%+
- Degenerative conditions: system adapts as abilities change (ALS/Parkinson's)
- Social inclusion: texting/emoji support treats users as whole people
- Frame it: "This isn't a chatbot — this gives a voice to people who can't speak"

#### 4. Quality of the Idea
> "Creativity and uniqueness"

**What to demonstrate:**
- No existing AAC tool uses multi-agent architecture
- Self-improving predictions via MongoDB data feedback loop (predictions collection tracks accuracy, agents query it to calibrate)
- Dynamic board generation vs. static grids (paradigm shift in AAC)
- Context-aware communication (boards change when you walk into a restaurant)

---

## 10. Competitive Landscape

### vs. Existing AAC Tools

| App | Approach | Cue's Advantage |
|---|---|---|
| Proloquo2Go | Static symbol grids, $250, manual SLP config | Dynamic boards, AI-generated, free |
| Spoken AAC | LLM text prediction | No dynamic boards, no context adaptation |
| Mosaic Voice | AI card selection (beta) | No multi-agent architecture, no learning |
| TD Snap | Eye gaze + switch, clinical | No AI personalization, expensive |

### vs. Hackathon Competitors

**Ember** (2nd place, ElevenLabs track, AI Partner Catalyst hackathon):
- GitHub: https://github.com/Superiour-fuel/ember
- Interprets unclear speech (dysarthria/aphasia) using Gemini + ElevenLabs voice cloning
- **Different user population:** Ember is for people who CAN speak but aren't understood. Cue is for people who CAN'T speak and need symbol-based boards.
- **Different approach:** Ember = speech interpretation. Cue = communication board generation + prediction.
- Ember had no learning/adaptation loop. Cue's MongoDB integration enables progressive improvement.

**Key differentiator for judges:** Cue's MongoDB MCP integration isn't cosmetic — it's the memory and learning engine. Every interaction feeds back into the system via MCP, making predictions more accurate over time. The agents don't just use a database; they learn from it.

---

## Appendix: Project Structure

```
cue/
├── app/                          # ADK agent definitions
│   ├── __init__.py
│   ├── agent.py                  # Agent hierarchy (root, prediction, scene, expression)
│   ├── agent_engine_app.py       # Agent Engine deployment wrapper
│   ├── config.py                 # 3-tier model config
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── root.py               # Root agent instructions
│   │   ├── prediction.py         # Prediction agent instructions
│   │   ├── scene.py              # Scene agent instructions
│   │   └── expression.py         # Expression agent instructions
│   └── tools/
│       ├── __init__.py
│       ├── context_tools.py      # get_user_profile, get_current_context
│       ├── prediction_tools.py   # get_communication_history, save_prediction
│       ├── board_tools.py        # get_board_templates, save_board
│       └── expression_tools.py   # synthesize_speech, complete_grammar
├── backend/                      # FastAPI service
│   ├── main.py                   # FastAPI app, CORS, routers
│   ├── api/
│   │   ├── users.py
│   │   ├── boards.py
│   │   ├── predictions.py
│   │   └── history.py
│   ├── services/
│   │   ├── agent_engine_client.py  # Local/prod agent proxy
│   │   ├── tts_service.py
│   │   └── mongodb_service.py
│   └── models/
│       └── schemas.py
├── frontend/                     # React SPA
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
├── docs/
│   └── technical-design.md       # This document
├── Makefile                      # Dev commands
├── pyproject.toml                # Python deps (uv)
├── README.md
└── LICENSE                       # MIT
```
