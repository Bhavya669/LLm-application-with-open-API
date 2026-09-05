"""
Prompt service — responsible for fetching prompt templates from MongoDB.
"""
import logging
from pymongo.errors import PyMongoError
from database.mongodb import get_prompts_collection

logger = logging.getLogger(__name__)


def get_prompt(prompt_id: str) -> str:
    """
    Fetch a prompt template from the prompts collection by its _id.

    Args:
        prompt_id: The _id of the prompt document e.g. "Education Prompt"

    Returns:
        The template string e.g. "You are an expert... {{userInput}}"

    Raises:
        ValueError: If the prompt is not found or the template field is missing/empty.
        RuntimeError: If a MongoDB error occurs.
    """
    try:
        collection = get_prompts_collection()
        document = collection.find_one({"_id": prompt_id})
    except PyMongoError as e:
        logger.error(f"MongoDB error while fetching prompt '{prompt_id}': {e}")
        raise RuntimeError(f"Database error while fetching prompt.") from e

    if document is None:
        logger.warning(f"Prompt not found in MongoDB: '{prompt_id}'")
        raise ValueError(f"Prompt '{prompt_id}' not found in the prompts collection.")

    template = document.get("template")

    if not template or not template.strip():
        logger.warning(f"Prompt '{prompt_id}' exists but has a missing or empty template field.")
        raise ValueError(f"Prompt '{prompt_id}' has a missing or empty template field.")

    logger.info(f"Successfully retrieved prompt: '{prompt_id}'")
    return template
