import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from config import MONGODB_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

# Single reusable client — not re-created per request
_client = None
_db = None


def get_client() -> MongoClient:
    """Initialize and return the reusable MongoDB client."""
    global _client
    if _client is None:
        logger.info("Initializing MongoDB client...")
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    return _client


def get_db():
    """Return the ai_project database handle."""
    global _db
    if _db is None:
        _db = get_client()[DATABASE_NAME]
    return _db


def get_prompts_collection():
    """Return the prompts collection."""
    return get_db()["prompts"]


def get_history_collection():
    """Return the history collection."""
    return get_db()["history"]


def ping_db() -> bool:
    """
    Ping MongoDB to verify connectivity.
    Returns True if reachable, raises an exception otherwise.
    """
    try:
        get_client().admin.command("ping")
        logger.info("MongoDB ping successful.")
        return True
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise
    except ConfigurationError as e:
        logger.error(f"MongoDB configuration error: {e}")
        raise
