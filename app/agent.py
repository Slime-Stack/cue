# ruff: noqa
"""
Cue — AI-powered AAC Platform

Agent hierarchy:
  root_agent (Flash) → routes to specialists
    ├── prediction_agent (Flash) — word/phrase prediction from MongoDB history
    ├── scene_agent (Flash) — dynamic board generation
    └── expression_agent (Lite) — grammar completion, TTS, texting

All agents share access to MongoDB via MCP server for reading/writing
user profiles, communication history, and boards.
"""

import os

import google.auth
from google.adk.agents import Agent, ParallelAgent
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

from .prompts import (
    EXPRESSION_INSTRUCTION,
    PREDICTION_INSTRUCTION,
    ROOT_INSTRUCTION,
    SCENE_INSTRUCTION,
)
from .tools import complete_grammar, format_for_texting, synthesize_speech

# Configure Google Cloud auth
_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

# MongoDB MCP connection — agents access the database through this
MONGODB_URI = os.environ.get("MONGODB_URI", "")

mongodb_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="npx",
            args=["-y", "mongodb-mcp-server@latest"],
            env={
                "MDB_MCP_CONNECTION_STRING": MONGODB_URI,
                **os.environ,
            },
        )
    ),
)

# Model config shared across Flash agents
FLASH_MODEL = Gemini(
    model="gemini-3-flash-preview",
    retry_options=types.HttpRetryOptions(attempts=3),
)

LITE_MODEL = Gemini(
    model="gemini-3-flash-lite-preview",
    retry_options=types.HttpRetryOptions(attempts=3),
)

# Global instruction injected into all agents via root
GLOBAL_INSTRUCTION = """PROJECT CONTEXT:
You are part of Cue, an AI-powered AAC (Augmentative and Alternative Communication) platform.
The user is a non-speaking person who communicates by selecting symbols/words on a board.
All user data is stored in MongoDB and accessed via MCP tools.

MongoDB collections:
- users: profiles with vocabulary, ability_level, voice_config, grid_size
- communication_history: timestamped records of what the user said, in what context
- boards: generated communication boards with core and fringe vocabulary zones

CURRENT USER CONTEXT:
- User ID: {user_id?}
- Name: {user_name?}
- Age: {user_age?}
- Ability level: {ability_level?}
- Current scene: {current_scene?}
- Recent selections: {recent_selections?}
"""


# =============================================================================
# SPECIALIST AGENTS
# =============================================================================

prediction_agent = Agent(
    name="prediction_agent",
    model=FLASH_MODEL,
    description="Predicts the most likely next words/phrases based on the user's communication history and current context. Use when you need word predictions for the AAC board.",
    instruction=PREDICTION_INSTRUCTION,
    tools=[mongodb_mcp],
)

scene_agent = Agent(
    name="scene_agent",
    model=FLASH_MODEL,
    description="Generates context-specific communication boards with core and fringe vocabulary zones. Use when the user changes scenes (restaurant, home, doctor, school) or needs a new board.",
    instruction=SCENE_INSTRUCTION,
    tools=[mongodb_mcp],
)

expression_agent = Agent(
    name="expression_agent",
    model=LITE_MODEL,
    description="Takes selected words and produces output: grammar completion, TTS speech, or formatted text messages with emoji. Use when the user has selected words and wants to express them.",
    instruction=EXPRESSION_INSTRUCTION,
    tools=[mongodb_mcp, synthesize_speech, complete_grammar, format_for_texting],
)


# =============================================================================
# COMPOSITE AGENTS
# =============================================================================

# Board Generator — runs prediction + scene in parallel when context changes
# Separate instances required because ADK agents can only have one parent
prediction_agent_for_board = Agent(
    name="prediction_agent_for_board",
    model=FLASH_MODEL,
    description="Generates word predictions for a new board context.",
    instruction=PREDICTION_INSTRUCTION,
    tools=[mongodb_mcp],
    output_key="board_predictions",
)

scene_agent_for_board = Agent(
    name="scene_agent_for_board",
    model=FLASH_MODEL,
    description="Generates the board layout for a new context.",
    instruction=SCENE_INSTRUCTION,
    tools=[mongodb_mcp],
    output_key="board_layout",
)

board_generator = ParallelAgent(
    name="board_generator",
    description="Generates a complete communication board by running scene generation and word prediction simultaneously. Use when a new scene is detected and both a board layout and predictions are needed at once.",
    sub_agents=[scene_agent_for_board, prediction_agent_for_board],
)


# =============================================================================
# ROOT AGENT
# =============================================================================

root_agent = Agent(
    name="root_agent",
    model=FLASH_MODEL,
    description="Cue AAC assistant — routes requests to prediction, scene, or expression agents.",
    global_instruction=GLOBAL_INSTRUCTION,
    instruction=ROOT_INSTRUCTION,
    tools=[mongodb_mcp],
    sub_agents=[prediction_agent, scene_agent, expression_agent, board_generator],
)


# =============================================================================
# ADK APP
# =============================================================================

app = App(
    root_agent=root_agent,
    name="cue",
)
