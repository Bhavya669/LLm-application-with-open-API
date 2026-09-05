"""
AI routes blueprint — /ask and /ask-batch endpoints.
Phase 3: /ask fully implemented.
Phase 4: history saving added to /ask.
Phase 6: /ask-batch with concurrent Gemini calls implemented.
"""
import asyncio
import logging
from flask import Blueprint, request, jsonify
from services.prompt_service import get_prompt
from services.openai_service import call_openai, call_openai_bulk
from services.history_service import save_history

logger = logging.getLogger(__name__)

ai_bp = Blueprint("ai", __name__)

# The prompt document _id to use — defined once, not hard-coded per request
PROMPT_ID = "Education Prompt"


@ai_bp.route("/ask", methods=["POST"])
def ask():
    """
    POST /ask
    Body: { "userInput": "..." }
    Returns: { "response": "..." }
    """
    # Step 1 — Parse JSON body
    data = request.get_json(silent=True)
    if not data:
        logger.warning("POST /ask — invalid or missing JSON body.")
        return jsonify({"error": "Request body must be valid JSON."}), 400

    # Step 2 — Validate userInput
    user_input = data.get("userInput")
    if not user_input:
        logger.warning("POST /ask — missing userInput field.")
        return jsonify({"error": "userInput is required."}), 400
    if not isinstance(user_input, str) or not user_input.strip():
        logger.warning("POST /ask — userInput is empty or not a string.")
        return jsonify({"error": "userInput must be a non-empty string."}), 400

    user_input = user_input.strip()
    logger.info(f"POST /ask — received request.")

    # Step 3 — Fetch prompt template from MongoDB
    try:
        template = get_prompt(PROMPT_ID)
    except ValueError as e:
        logger.error(f"POST /ask — prompt error: {e}")
        return jsonify({"error": "Prompt configuration not found. Contact administrator."}), 404
    except RuntimeError as e:
        logger.error(f"POST /ask — database error: {e}")
        return jsonify({"error": "Database error. Please try again later."}), 500

    # Step 4 — Replace {{userInput}} placeholder with actual input
    final_prompt = template.replace("{{userInput}}", user_input)
    logger.info("POST /ask — prompt template substituted successfully.")

    # Step 5 — Call Gemini API
    try:
        ai_response = call_openai(final_prompt)
    except RuntimeError as e:
        logger.error(f"POST /ask — Gemini error: {e}")
        return jsonify({"error": "AI service error. Please try again later."}), 500

    # Step 6 — Save request and response to history
    try:
        save_history(user_input, ai_response)
    except RuntimeError as e:
        logger.error(f"POST /ask — history save failed: {e}")
        # AI response was successful — still return it, but log the failure clearly
        return jsonify({"response": ai_response}), 200

    # Step 7 — Return JSON response
    logger.info("POST /ask — returning AI response to client.")
    return jsonify({"response": ai_response}), 200


@ai_bp.route("/ask-batch", methods=["POST"])
def ask_batch():
    """
    POST /ask-batch
    Body: { "userInput": ["question 1", "question 2", ...] }
    Returns: { "responses": ["response 1", "response 2", ...] }

    Processes all inputs concurrently via asyncio.gather() + asyncio.to_thread().
    Response order matches input order exactly.
    Each input/response pair is saved to MongoDB history independently.
    """
    # Step 1 — Parse JSON body
    data = request.get_json(silent=True)
    if not data:
        logger.warning("POST /ask-batch — invalid or missing JSON body.")
        return jsonify({"error": "Request body must be valid JSON."}), 400

    # Step 2 — Validate userInput is a non-empty list of non-empty strings
    user_inputs = data.get("userInput")
    if user_inputs is None:
        logger.warning("POST /ask-batch — missing userInput field.")
        return jsonify({"error": "userInput is required."}), 400
    if not isinstance(user_inputs, list):
        logger.warning("POST /ask-batch — userInput is not a list.")
        return jsonify({"error": "userInput must be a list of strings."}), 400
    if len(user_inputs) == 0:
        logger.warning("POST /ask-batch — userInput list is empty.")
        return jsonify({"error": "userInput list must not be empty."}), 400
    for i, item in enumerate(user_inputs):
        if not isinstance(item, str) or not item.strip():
            logger.warning(f"POST /ask-batch — invalid item at index {i}.")
            return jsonify({"error": f"Each item in userInput must be a non-empty string. Invalid item at index {i}."}), 400

    # Strip whitespace from all inputs
    user_inputs = [item.strip() for item in user_inputs]
    logger.info(f"POST /ask-batch — received request with {len(user_inputs)} inputs.")

    # Step 3 — Fetch prompt template from MongoDB once for the entire batch
    try:
        template = get_prompt(PROMPT_ID)
    except ValueError as e:
        logger.error(f"POST /ask-batch — prompt error: {e}")
        return jsonify({"error": "Prompt configuration not found. Contact administrator."}), 404
    except RuntimeError as e:
        logger.error(f"POST /ask-batch — database error: {e}")
        return jsonify({"error": "Database error. Please try again later."}), 500

    # Step 4 — Build individual final prompts by substituting each input
    final_prompts = [template.replace("{{userInput}}", ui) for ui in user_inputs]
    logger.info("POST /ask-batch — all prompt templates substituted.")

    # Step 5 — Call Gemini concurrently for all prompts, preserving order
    try:
        results = asyncio.run(call_openai_bulk(final_prompts))
    except Exception as e:
        logger.error(f"POST /ask-batch — unexpected error during concurrent AI calls: {e}")
        return jsonify({"error": "AI service error. Please try again later."}), 500

    # Step 6 — Build response list and save each result to history
    responses = []
    for i, (ui, result) in enumerate(zip(user_inputs, results)):
        # asyncio.gather with return_exceptions=True returns exceptions instead of raising
        if isinstance(result, Exception):
            logger.error(f"POST /ask-batch — Gemini failed for input index {i}: {result}")
            responses.append({"error": "AI service error for this input."})
        else:
            responses.append(result)
            # Save each successful result to history independently
            try:
                save_history(ui, result)
            except RuntimeError as e:
                logger.error(f"POST /ask-batch — history save failed for index {i}: {e}")
                # Continue — don't block the response for a history write failure

    logger.info(f"POST /ask-batch — returning {len(responses)} responses to client.")
    return jsonify({"responses": responses}), 200
