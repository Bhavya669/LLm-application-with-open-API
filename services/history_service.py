"""
History service — responsible for saving request/response records to MongoDB.
"""
import logging
from datetime import datetime, timezone
from pymongo.errors import PyMongoError
from database.mongodb import get_history_collection

logger = logging.getLogger(__name__)


def save_history(user_input: str, response: str) -> None:
    """
    Insert a request/response record into the history collection.

    Args:
        user_input: The original input string from the user.
        response:   The AI-generated response text.

    Raises:
        RuntimeError: If the MongoDB insert fails.
    """
    document = {
        "userInput": user_input,
        "response": response,
        "createdAt": datetime.now(timezone.utc)
    }
    try:
        collection = get_history_collection()
        collection.insert_one(document)
        logger.info("History record saved to MongoDB successfully.")
    except PyMongoError as e:
        logger.error(f"Failed to save history to MongoDB: {e}")
        raise RuntimeError("Database error while saving history.") from e
