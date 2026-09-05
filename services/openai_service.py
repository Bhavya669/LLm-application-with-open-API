"""
Gemini service — responsible for all Google Gemini API interactions.
Replaces the previous OpenAI integration.
Phase 3: single synchronous call implemented.
Phase 6: async bulk calls implemented.
"""
import asyncio
import logging
from google import genai
from google.genai import errors as genai_errors
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# Single reusable Gemini client — not re-created per request
_gemini_client = None


def get_gemini_client() -> genai.Client:
    """Return the reusable Gemini client instance."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def call_openai(prompt: str) -> str:
    """
    Send a single prompt to Gemini and return the response text.
    Function name kept as call_openai to avoid changing the route layer.

    Args:
        prompt: The fully constructed prompt string to send.

    Returns:
        The AI-generated response text.

    Raises:
        RuntimeError: If the Gemini API call fails.
    """
    logger.info(f"Sending prompt to Gemini using model: {GEMINI_MODEL}")
    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )
        response_text = response.text
        logger.info("Gemini response received successfully.")
        return response_text
    except genai_errors.APIError as e:
        logger.error(f"Gemini API error: {e}")
        raise RuntimeError("Gemini API request failed.") from e
    except Exception as e:
        logger.error(f"Unexpected error during Gemini call: {e}")
        raise RuntimeError("Unexpected error during Gemini call.") from e


async def call_openai_async(prompt: str) -> str:
    """
    Run the synchronous call_openai in a thread so it can be awaited.
    Used by the batch endpoint to allow concurrent execution via asyncio.gather().
    """
    # asyncio.to_thread runs the blocking call in a thread pool,
    # allowing multiple Gemini calls to execute concurrently.
    return await asyncio.to_thread(call_openai, prompt)


async def call_openai_bulk(prompts: list[str]) -> list[str]:
    """
    Process multiple prompts concurrently using asyncio.gather().
    Result order is preserved — index 0 in input maps to index 0 in output.
    """
    logger.info(f"Starting concurrent Gemini calls for {len(prompts)} prompts.")
    tasks = [call_openai_async(prompt) for prompt in prompts]
    # gather() dispatches all tasks concurrently and returns results in input order
    results = await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("All concurrent Gemini calls completed.")
    return results
