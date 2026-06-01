"""
Seed MongoDB with test data for Cue AAC demo.

Usage:
    uv run python scripts/seed_db.py

Requires MONGODB_URI env var or .env file.
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI")
if not MONGODB_URI:
    raise SystemExit("MONGODB_URI not set. Copy .env.example to .env and fill in your Atlas connection string.")

client = MongoClient(MONGODB_URI)
db = client["cue"]

# Drop existing collections for clean seed
for collection_name in ["users", "communication_history", "boards"]:
    db[collection_name].drop()

now = datetime.now(timezone.utc)

# =============================================================================
# USER: Alex (4yo, autism, ability level 2)
# =============================================================================

alex = db["users"].insert_one({
    "name": "Alex",
    "age": 4,
    "ability_level": 2,
    "diagnosis": "autism spectrum disorder",
    "voice_config": {
        "language": "en-US",
        "voice_name": "en-US-Journey-O",
        "speaking_rate": 0.9,
        "pitch": 2.0,
    },
    "grid_size": {"rows": 3, "cols": 4},
    "motor_config": {
        "min_button_size_px": 80,
        "dwell_time_ms": None,
        "switch_scanning": False,
    },
    "vocabulary": {
        "level": "core_200",
        "words": [
            {"word": "I", "category": "pronoun"},
            {"word": "you", "category": "pronoun"},
            {"word": "it", "category": "pronoun"},
            {"word": "that", "category": "pronoun"},
            {"word": "want", "category": "verb"},
            {"word": "go", "category": "verb"},
            {"word": "like", "category": "verb"},
            {"word": "eat", "category": "verb"},
            {"word": "play", "category": "verb"},
            {"word": "help", "category": "verb"},
            {"word": "see", "category": "verb"},
            {"word": "not", "category": "negation"},
            {"word": "stop", "category": "negation"},
            {"word": "more", "category": "adjective"},
            {"word": "big", "category": "adjective"},
            {"word": "all done", "category": "adjective"},
            {"word": "good", "category": "adjective"},
            {"word": "hot", "category": "adjective"},
            {"word": "hi", "category": "social"},
            {"word": "bye", "category": "social"},
            {"word": "please", "category": "social"},
            {"word": "thank you", "category": "social"},
            {"word": "pizza", "category": "noun"},
            {"word": "water", "category": "noun"},
            {"word": "juice", "category": "noun"},
            {"word": "french fries", "category": "noun"},
            {"word": "burger", "category": "noun"},
            {"word": "TV", "category": "noun"},
            {"word": "snack", "category": "noun"},
            {"word": "outside", "category": "noun"},
            {"word": "toy", "category": "noun"},
            {"word": "blanket", "category": "noun"},
            {"word": "bathroom", "category": "noun"},
            {"word": "mom", "category": "noun"},
            {"word": "dad", "category": "noun"},
        ],
        "custom_words": [
            {"word": "dinosaur", "category": "noun", "added_by": "parent"},
            {"word": "Peppa Pig", "category": "noun", "added_by": "parent"},
            {"word": "goldfish crackers", "category": "noun", "added_by": "parent"},
        ],
    },
    "created_at": now,
    "updated_at": now,
})

alex_id = alex.inserted_id
print(f"Created user Alex: {alex_id}")

# =============================================================================
# USER: Maria (45yo, ALS, ability level 4)
# =============================================================================

maria = db["users"].insert_one({
    "name": "Maria",
    "age": 45,
    "ability_level": 4,
    "diagnosis": "amyotrophic lateral sclerosis",
    "voice_config": {
        "language": "en-US",
        "voice_name": "en-US-Journey-F",
        "speaking_rate": 1.0,
        "pitch": 0.0,
    },
    "grid_size": {"rows": 5, "cols": 7},
    "motor_config": {
        "min_button_size_px": 50,
        "dwell_time_ms": 800,
        "switch_scanning": False,
    },
    "vocabulary": {
        "level": "full",
        "words": [
            {"word": "I", "category": "pronoun"},
            {"word": "you", "category": "pronoun"},
            {"word": "he", "category": "pronoun"},
            {"word": "she", "category": "pronoun"},
            {"word": "we", "category": "pronoun"},
            {"word": "they", "category": "pronoun"},
            {"word": "it", "category": "pronoun"},
            {"word": "that", "category": "pronoun"},
            {"word": "this", "category": "pronoun"},
            {"word": "want", "category": "verb"},
            {"word": "need", "category": "verb"},
            {"word": "go", "category": "verb"},
            {"word": "like", "category": "verb"},
            {"word": "think", "category": "verb"},
            {"word": "feel", "category": "verb"},
            {"word": "help", "category": "verb"},
            {"word": "know", "category": "verb"},
            {"word": "tell", "category": "verb"},
            {"word": "see", "category": "verb"},
            {"word": "call", "category": "verb"},
            {"word": "not", "category": "negation"},
            {"word": "don't", "category": "negation"},
            {"word": "stop", "category": "negation"},
            {"word": "more", "category": "adjective"},
            {"word": "good", "category": "adjective"},
            {"word": "tired", "category": "adjective"},
            {"word": "cold", "category": "adjective"},
            {"word": "hot", "category": "adjective"},
            {"word": "hungry", "category": "adjective"},
            {"word": "happy", "category": "adjective"},
            {"word": "sad", "category": "adjective"},
            {"word": "hi", "category": "social"},
            {"word": "bye", "category": "social"},
            {"word": "please", "category": "social"},
            {"word": "thank you", "category": "social"},
            {"word": "sorry", "category": "social"},
            {"word": "love you", "category": "social"},
        ],
        "custom_words": [
            {"word": "physical therapy", "category": "noun", "added_by": "caregiver"},
            {"word": "breathing exercise", "category": "noun", "added_by": "caregiver"},
        ],
    },
    "created_at": now,
    "updated_at": now,
})

maria_id = maria.inserted_id
print(f"Created user Maria: {maria_id}")

# =============================================================================
# COMMUNICATION HISTORY: Alex (builds patterns for prediction agent)
# =============================================================================

history_entries = [
    # Restaurant pattern — Alex frequently says "I want pizza" at restaurants
    {"user_id": alex_id, "timestamp": now - timedelta(days=5, hours=2), "context": {"location": "restaurant", "time_of_day": "lunch", "partner_type": "parent"}, "selections": ["I", "want", "pizza"], "expressed_output": "I want pizza, please.", "output_type": "speech", "prediction_used": True, "prediction_rank": 1},
    {"user_id": alex_id, "timestamp": now - timedelta(days=5, hours=1), "context": {"location": "restaurant", "time_of_day": "lunch", "partner_type": "parent"}, "selections": ["more", "juice"], "expressed_output": "More juice, please.", "output_type": "speech", "prediction_used": True, "prediction_rank": 2},
    {"user_id": alex_id, "timestamp": now - timedelta(days=3, hours=6), "context": {"location": "restaurant", "time_of_day": "dinner", "partner_type": "parent"}, "selections": ["I", "want", "french fries"], "expressed_output": "I want french fries.", "output_type": "speech", "prediction_used": False, "prediction_rank": None},
    {"user_id": alex_id, "timestamp": now - timedelta(days=3, hours=5), "context": {"location": "restaurant", "time_of_day": "dinner", "partner_type": "parent"}, "selections": ["want", "water"], "expressed_output": "I want water.", "output_type": "speech", "prediction_used": True, "prediction_rank": 1},
    {"user_id": alex_id, "timestamp": now - timedelta(days=1, hours=3), "context": {"location": "restaurant", "time_of_day": "lunch", "partner_type": "parent"}, "selections": ["I", "want", "pizza"], "expressed_output": "I want pizza, please.", "output_type": "speech", "prediction_used": True, "prediction_rank": 1},
    {"user_id": alex_id, "timestamp": now - timedelta(days=1, hours=2), "context": {"location": "restaurant", "time_of_day": "lunch", "partner_type": "parent"}, "selections": ["all done"], "expressed_output": "All done!", "output_type": "speech", "prediction_used": False, "prediction_rank": None},

    # Home pattern — TV and snacks
    {"user_id": alex_id, "timestamp": now - timedelta(days=4, hours=8), "context": {"location": "home", "time_of_day": "morning", "partner_type": "parent"}, "selections": ["want", "TV"], "expressed_output": "I want TV.", "output_type": "speech", "prediction_used": True, "prediction_rank": 1},
    {"user_id": alex_id, "timestamp": now - timedelta(days=4, hours=7), "context": {"location": "home", "time_of_day": "morning", "partner_type": "parent"}, "selections": ["want", "snack"], "expressed_output": "I want a snack.", "output_type": "speech", "prediction_used": True, "prediction_rank": 2},
    {"user_id": alex_id, "timestamp": now - timedelta(days=2, hours=9), "context": {"location": "home", "time_of_day": "afternoon", "partner_type": "parent"}, "selections": ["go", "outside"], "expressed_output": "I want to go outside.", "output_type": "speech", "prediction_used": False, "prediction_rank": None},
    {"user_id": alex_id, "timestamp": now - timedelta(days=2, hours=8), "context": {"location": "home", "time_of_day": "afternoon", "partner_type": "parent"}, "selections": ["play", "dinosaur"], "expressed_output": "Play dinosaur!", "output_type": "speech", "prediction_used": False, "prediction_rank": None},
    {"user_id": alex_id, "timestamp": now - timedelta(hours=10), "context": {"location": "home", "time_of_day": "morning", "partner_type": "parent"}, "selections": ["want", "Peppa Pig"], "expressed_output": "I want Peppa Pig.", "output_type": "speech", "prediction_used": True, "prediction_rank": 3},

    # Social / texting
    {"user_id": alex_id, "timestamp": now - timedelta(days=2, hours=4), "context": {"location": "home", "time_of_day": "afternoon", "partner_type": "peer"}, "selections": ["hi"], "expressed_output": "Hi! 👋", "output_type": "text", "prediction_used": False, "prediction_rank": None},
    {"user_id": alex_id, "timestamp": now - timedelta(days=2, hours=3), "context": {"location": "home", "time_of_day": "afternoon", "partner_type": "peer"}, "selections": ["like", "play"], "expressed_output": "I like to play! 🎮", "output_type": "text", "prediction_used": True, "prediction_rank": 1},
]

db["communication_history"].insert_many(history_entries)
print(f"Inserted {len(history_entries)} communication history entries for Alex")

# =============================================================================
# INDEXES
# =============================================================================

db["communication_history"].create_index([("user_id", 1), ("timestamp", -1)])
db["communication_history"].create_index([("user_id", 1), ("context.location", 1)])
db["boards"].create_index([("user_id", 1), ("scene_type", 1)])

print("Created indexes")

# =============================================================================
# VERIFY
# =============================================================================

print(f"\nDatabase: cue")
print(f"Users: {db['users'].count_documents({})}")
print(f"Communication history: {db['communication_history'].count_documents({})}")
print(f"Boards: {db['boards'].count_documents({})}")

# Quick aggregation test — what Alex says most at restaurants
pipeline = [
    {"$match": {"user_id": alex_id, "context.location": "restaurant"}},
    {"$unwind": "$selections"},
    {"$group": {"_id": "$selections", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 5},
]
results = list(db["communication_history"].aggregate(pipeline))
print(f"\nAlex's top words at restaurants:")
for r in results:
    print(f"  {r['_id']}: {r['count']}x")

print("\nSeed complete! Set MONGODB_URI in .env and run: make playground")
