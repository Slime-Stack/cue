# Cue

AI-powered Augmentative and Alternative Communication (AAC) platform built with Google ADK, Gemini 3, and MongoDB.

Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) (MongoDB partner track).

Scaffolded with [`agent-starter-pack`](https://github.com/GoogleCloudPlatform/agent-starter-pack) v0.41.3.

## About

Cue is an adaptive AAC system that uses AI agents to dynamically personalize communication for users across ages, ability levels, and contexts. Unlike traditional AAC tools with static grids, Cue adapts in real time — predicting what the user wants to say, generating context-aware communication boards, and adjusting interface complexity based on the user's current abilities.

## How It Works

Cue uses a multi-agent architecture where each agent has a specific role:

- **Prediction Agent** — learns communication patterns from MongoDB history, surfaces likely next words based on context (time, location, conversation partner)
- **Scene Agent** — generates context-specific communication boards on the fly (restaurant, doctor, school, home)
- **Expression Agent** — converts selected words into grammatically complete speech via Google Cloud TTS, or formats for texting with emoji suggestions

Agents access user data through the **MongoDB MCP server**, enabling aggregation pipelines that analyze communication patterns and a feedback loop that improves predictions over time.

## Tech Stack

| Layer | Technology |
|---|---|
| Agents | Google ADK, Vertex AI Agent Engine, Gemini 3 |
| Partner Integration | MongoDB Atlas via MCP server |
| Backend | FastAPI on Cloud Run |
| Frontend | React + TypeScript + Vite |
| TTS | Google Cloud Text-to-Speech |

## Project Structure

```
cue/
├── app/                    # ADK agent definitions
│   ├── agent.py            # Agent hierarchy
│   ├── agent_engine_app.py # Agent Engine deployment wrapper
│   ├── config.py           # Model tier config
│   ├── prompts/            # Agent instructions
│   └── tools/              # Agent tools (MCP wrappers)
├── backend/                # FastAPI service
│   ├── main.py
│   ├── api/                # REST endpoints
│   ├── services/           # Agent engine client, TTS, MongoDB
│   └── models/             # Pydantic schemas
├── frontend/               # React SPA
│   └── src/
├── tests/                  # Unit, integration, eval tests
├── docs/
│   └── technical-design.md # Full technical design
└── pyproject.toml          # Python deps (uv)
```

## Quick Start

```bash
make install && make playground
```

## Commands

| Command | Purpose |
|---|---|
| `make install` | Install dependencies |
| `make playground` | Launch local ADK dev environment |
| `make test` | Run unit and integration tests |
| `make eval` | Run agent evaluation |
| `make lint` | Code quality checks |
| `make deploy` | Deploy to Agent Engine |

## Status

Early development. See [docs/technical-design.md](docs/technical-design.md) for the full architecture and design.

## License

MIT
